import os
import sqlite3
import json
import click
from flask import Flask, jsonify, request, g, send_from_directory
from flask.cli import with_appcontext
from flask_cors import CORS
import logging
import time
from datetime import datetime
import pandas as pd

# --- Configuração do App ---
app = Flask(__name__, static_folder='build', static_url_path='/')
# AJUSTE: Tornando o CORS mais permissivo para garantir a comunicação.
# Isso permite requisições de qualquer origem, ideal para resolver este problema.
CORS(app)

# --- Configuração do Banco de Dados ---
DATABASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'rpa_refatorado.db'))
LEGALONE_DATABASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database.db'))
TAREFAS_CRIADAS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tarefas_criadas'))


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def get_legalone_db():
    try:
        db = sqlite3.connect(f'file:{LEGALONE_DATABASE}?mode=ro', uri=True)
        db.row_factory = sqlite3.Row
        return db
    except sqlite3.OperationalError as e:
        app.logger.warning(f"Não foi possível conectar ao banco de dados Legal One em '{LEGALONE_DATABASE}': {e}")
        return None

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- Comandos CLI ---
def init_db():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("PRAGMA table_info(notificacoes)")
    cols = [col['name'] for col in cursor.fetchall()]
    if 'responsavel' not in cols:
        db.execute('ALTER TABLE notificacoes ADD COLUMN responsavel TEXT')
    if 'data_processamento' not in cols:
        db.execute('ALTER TABLE notificacoes ADD COLUMN data_processamento TEXT')
    if 'detalhes_erro' not in cols:
        db.execute('ALTER TABLE notificacoes ADD COLUMN detalhes_erro TEXT')
    if 'gerou_tarefa' not in cols:
        db.execute('ALTER TABLE notificacoes ADD COLUMN gerou_tarefa INTEGER DEFAULT 0')
    if 'origem' not in cols:
        db.execute('ALTER TABLE notificacoes ADD COLUMN origem TEXT DEFAULT "onenotify"')

    db.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE
        )
    ''')
    db.commit()

@click.command('init-db')
@with_appcontext
def init_db_command():
    init_db()
    click.echo('Banco de dados verificado e atualizado.')

app.cli.add_command(init_db_command)

@click.command('add-user')
@click.argument('nome')
@with_appcontext
def add_user_command(nome):
    db = get_db()
    try:
        db.execute("INSERT INTO usuarios (nome) VALUES (?)", (nome,))
        db.commit()
        click.echo(f"Usuário '{nome}' adicionado com sucesso.")
    except sqlite3.IntegrityError:
        click.echo(f"Erro: Usuário '{nome}' já existe.")

app.cli.add_command(add_user_command)

# --- Funções Auxiliares ---
def table_has_column(db, table_name, column_name):
    cursor = db.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col['name'] for col in cursor.fetchall()]
    return column_name in columns

# --- Rotas da API ---

@app.route('/api/migracao', methods=['POST'])
def migrar_planilha():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nome de arquivo inválido'}), 400

    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.filename.endswith('.xlsx'):
            df = pd.read_excel(file)
        else:
            return jsonify({'error': 'Formato de arquivo não suportado. Use .csv ou .xlsx'}), 400

        if 'npj' not in df.columns or 'data' not in df.columns:
            return jsonify({'error': 'A planilha deve conter as colunas "npj" e "data"'}), 400

        db = get_db()
        cursor = db.cursor()
        
        for index, row in df.iterrows():
            npj = str(row['npj'])
            data_notificacao = str(row['data'])
            
            # CORREÇÃO APLICADA AQUI: De INSERT para INSERT OR IGNORE
            cursor.execute("""
                INSERT OR IGNORE INTO notificacoes (NPJ, data_notificacao, status, origem, tipo_notificacao)
                VALUES (?, ?, 'Pendente', 'migracao', 'Migração de Dados')
            """, (npj, data_notificacao))

        db.commit()
        return jsonify({'message': f'{len(df)} notificações foram adicionadas à fila de migração.'}), 201

    except Exception as e:
        app.logger.error(f"Erro ao processar planilha: {e}")
        return jsonify({'error': 'Falha ao processar o arquivo da planilha'}), 500


@app.route('/api/tarefas', methods=['POST'])
def criar_tarefa():
    tarefa_data = request.json
    if not tarefa_data or 'processos' not in tarefa_data or not tarefa_data['processos']:
        return jsonify({'error': 'Dados da tarefa inválidos'}), 400
    
    try:
        os.makedirs(TAREFAS_CRIADAS_PATH, exist_ok=True)
        
        now = datetime.now()
        interval_start_minute = 0 if now.minute < 30 else 30
        file_name = f"tarefas_{now.strftime('%Y-%m-%d_%H')}-{interval_start_minute:02d}.json"
        file_path = os.path.join(TAREFAS_CRIADAS_PATH, file_name)
        
        file_content = {"fonte": "Onenotify", "processos": []}
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = json.load(f)
                    if "processos" not in file_content or not isinstance(file_content["processos"], list):
                            file_content["processos"] = []
            except (json.JSONDecodeError, FileNotFoundError):
                pass

        file_content["processos"].append(tarefa_data["processos"][0])
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(file_content, f, ensure_ascii=False, indent=2)
            
        return jsonify({'message': 'Tarefa adicionada ao lote com sucesso', 'file_path': file_path}), 201
        
    except Exception as e:
        app.logger.error(f"Erro ao salvar arquivo de tarefa: {e}")
        return jsonify({'error': 'Falha ao salvar o arquivo da tarefa'}), 500


@app.route('/api/legalone/users')
def get_legalone_users():
    db = get_legalone_db()
    if db is None:
        return jsonify([])
    try:
        users_raw = db.execute("SELECT name, external_id FROM legal_one_users ORDER BY name").fetchall()
        users = [dict(row) for row in users_raw]
        return jsonify(users)
    except sqlite3.OperationalError as e:
        app.logger.warning(f"Erro ao buscar usuários do Legal One: {e}")
        return jsonify([])
    finally:
        if db:
            db.close()

@app.route('/api/legalone/tasks')
def get_legalone_tasks():
    db = get_legalone_db()
    if db is None:
        return jsonify([])
    try:
        tasks_raw = db.execute("SELECT name, external_id, parent_type_external_id FROM legal_one_task_subtypes ORDER BY name").fetchall()
        tasks = [dict(row) for row in tasks_raw]
        return jsonify(tasks)
    except sqlite3.OperationalError as e:
        app.logger.warning(f"Erro ao buscar tarefas do Legal One: {e}")
        return jsonify([])
    finally:
        if db:
            db.close()

@app.route('/api/stats')
def get_stats():
    db = get_db()
    stats = {}
    statuses = {'pendente': 'Pendente', 'processado': 'Processado', 'arquivado': 'Arquivado', 'tratada': 'Tratada', 'migrado': 'Migrado'}
    for key, status_val in statuses.items():
        count = db.execute(
            "SELECT COUNT(DISTINCT NPJ || data_notificacao) FROM notificacoes WHERE status = ?", (status_val,)
        ).fetchone()[0]
        stats[key] = count
    
    erro_count = db.execute(
        "SELECT COUNT(DISTINCT NPJ || data_notificacao) FROM notificacoes WHERE status LIKE 'Erro%'"
    ).fetchone()[0]
    stats['erro'] = erro_count
    
    return jsonify(stats)

@app.route('/api/notificacoes')
def get_notificacoes():
    status_filter = request.args.get('status', 'Pendente')
    responsavel_filter = request.args.get('responsavel')
    db = get_db()
    
    params = []
    
    if status_filter == 'Erro':
        query_status = "WHERE status LIKE 'Erro%'"
    else:
        query_status = "WHERE status = ?"
        params.append(status_filter)

    gerou_tarefa_select = "MAX(gerou_tarefa) as gerou_tarefa," if table_has_column(db, "notificacoes", "gerou_tarefa") else ""

    query = f"""
        SELECT
            NPJ, data_notificacao, MAX(adverso_principal) as adverso_principal,
            MAX(numero_processo) as numero_processo, GROUP_CONCAT(id, ';') as ids,
            GROUP_CONCAT(tipo_notificacao, '; ') as tipos_notificacao, MAX(responsavel) as responsavel,
            MAX(data_processamento) as data_processamento, MAX(detalhes_erro) as detalhes_erro,
            {gerou_tarefa_select}
            status
        FROM notificacoes {query_status}
    """
    
    if responsavel_filter and responsavel_filter != 'Todos':
        query += " AND responsavel = ?"
        params.append(responsavel_filter)
    elif responsavel_filter == 'Sem Responsável':
        query += " AND (responsavel IS NULL OR responsavel = '')"

    query += " GROUP BY NPJ, data_notificacao ORDER BY data_notificacao DESC, NPJ"

    notificacoes_raw = db.execute(query, params).fetchall()
    notificacoes = [dict(row) for row in notificacoes_raw]
    return jsonify(notificacoes)

@app.route('/api/detalhes')
def get_detalhes():
    npj = request.args.get('npj')
    data = request.args.get('data')

    if not npj or not data:
        return jsonify({"error": "NPJ e data são obrigatórios"}), 400

    db = get_db()
    detalhes = db.execute(
        "SELECT MAX(andamentos) as andamentos, MAX(documentos) as documentos FROM notificacoes WHERE NPJ = ? AND data_notificacao = ?",
        (npj, data)
    ).fetchone()
    
    if detalhes and (detalhes['andamentos'] or detalhes['documentos']):
        return jsonify({
            'andamentos': json.loads(detalhes['andamentos'] or '[]'),
            'documentos': json.loads(detalhes['documentos'] or '[]')
        })
    return jsonify({'andamentos': [], 'documentos': []})

@app.route('/api/download')
def download_file():
    caminho = request.args.get('path')
    if not caminho: return "Caminho do arquivo não fornecido.", 400
    
    diretorio_base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'documentos'))
    caminho_seguro = os.path.abspath(caminho)

    if not caminho_seguro.startswith(diretorio_base): return "Acesso negado.", 403
    if os.path.exists(caminho_seguro): return send_from_directory(os.path.dirname(caminho_seguro), os.path.basename(caminho_seguro), as_attachment=True)
    return "Arquivo não encontrado.", 404

@app.route('/api/acoes/status', methods=['POST'])
def update_status():
    data = request.json
    ids_list = data.get('ids')
    novo_status = data.get('novo_status')
    gerou_tarefa = data.get('gerou_tarefa') 

    if not ids_list or not novo_status: return jsonify({'error': 'IDs e novo_status são obrigatórios'}), 400
    
    ids = [int(i) for i in ids_list]
    
    db = get_db()
    placeholders = ', '.join(['?'] * len(ids))

    if novo_status == 'Tratada' and gerou_tarefa is not None:
        params = [novo_status, gerou_tarefa] + ids
        db.execute(f"UPDATE notificacoes SET status = ?, gerou_tarefa = ? WHERE id IN ({placeholders})", params)
    else:
        params = [novo_status] + ids
        db.execute(f"UPDATE notificacoes SET status = ? WHERE id IN ({placeholders})", params)
        
    db.commit()
    return jsonify({'message': f'{len(ids)} notificações atualizadas para {novo_status}'})

@app.route('/api/usuarios', methods=['GET'])
def get_usuarios():
    db = get_db()
    users_raw = db.execute("SELECT id, nome FROM usuarios ORDER BY nome").fetchall()
    return jsonify([dict(row) for row in users_raw])

@app.route('/api/usuarios', methods=['POST'])
def add_usuario():
    nome = request.json.get('nome')
    if not nome: return jsonify({'error': 'Nome é obrigatório'}), 400
    try:
        db = get_db()
        db.execute("INSERT INTO usuarios (nome) VALUES (?)", (nome,))
        db.commit()
        return jsonify({'message': f'Usuário {nome} criado com sucesso'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': f'Usuário {nome} já existe'}), 409

@app.route('/api/usuarios/<int:user_id>', methods=['DELETE'])
def delete_usuario(user_id):
    db = get_db()
    db.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
    db.commit()
    return jsonify({'message': 'Usuário removido com sucesso'})

# --- Servir React App ---
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

