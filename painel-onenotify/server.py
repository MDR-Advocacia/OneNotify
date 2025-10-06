# arquivo: server.py
import os
import sqlite3
import json
import click
from flask import Flask, jsonify, request, g, send_from_directory
from flask.cli import with_appcontext
from flask_cors import CORS

# --- Configuração do App ---
app = Flask(__name__, static_folder='build', static_url_path='/')
CORS(app, origins="http://localhost:3000", supports_credentials=True)

# --- Configuração do Banco de Dados ---
DATABASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'rpa_refatorado.db'))

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- Comandos CLI ---
def init_db():
    db = get_db()
    cursor = db.cursor()
    # Verifica e adiciona colunas à tabela de notificações se não existirem
    cursor.execute("PRAGMA table_info(notificacoes)")
    cols = [col['name'] for col in cursor.fetchall()]
    if 'responsavel' not in cols:
        db.execute('ALTER TABLE notificacoes ADD COLUMN responsavel TEXT')
    if 'data_processamento' not in cols:
        db.execute('ALTER TABLE notificacoes ADD COLUMN data_processamento TEXT')
    if 'detalhes_erro' not in cols:
        db.execute('ALTER TABLE notificacoes ADD COLUMN detalhes_erro TEXT')
    
    # Cria a tabela de usuários se não existir
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

# --- Rotas da API ---

@app.route('/api/stats')
def get_stats():
    db = get_db()
    stats = {}
    statuses = {'pendente': 'Pendente', 'processado': 'Processado', 'arquivado': 'Arquivado'}
    for key, status_val in statuses.items():
        count = db.execute(
            "SELECT COUNT(DISTINCT NPJ || data_notificacao) FROM notificacoes WHERE status = ?", (status_val,)
        ).fetchone()[0]
        stats[key] = count
    
    # Soma os dois tipos de erro
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

    query = f"""
        SELECT
            NPJ, data_notificacao, MAX(adverso_principal) as adverso_principal,
            MAX(numero_processo) as numero_processo, GROUP_CONCAT(id, ';') as ids,
            GROUP_CONCAT(tipo_notificacao, '; ') as tipos_notificacao, MAX(responsavel) as responsavel,
            MAX(data_processamento) as data_processamento, MAX(detalhes_erro) as detalhes_erro,
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
    ids_list = data.get('ids') # Agora recebe uma lista
    novo_status = data.get('novo_status')

    if not ids_list or not novo_status: return jsonify({'error': 'IDs e novo_status são obrigatórios'}), 400
    
    # *** CORREÇÃO APLICADA AQUI ***
    # A variável já é uma lista, não precisa de split. Apenas garantimos que são inteiros.
    ids = [int(i) for i in ids_list]
    
    db = get_db()
    placeholders = ', '.join(['?'] * len(ids))
    db.execute(f"UPDATE notificacoes SET status = ? WHERE id IN ({placeholders})", [novo_status] + ids)
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

