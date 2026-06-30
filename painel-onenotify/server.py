import os
import sqlite3
import json
import click
import sys
import mimetypes
from flask import Flask, jsonify, request, g, send_from_directory
from flask.cli import with_appcontext
from flask_cors import CORS
import logging
import time
from datetime import datetime
from urllib.parse import quote
import pandas as pd
from werkzeug.middleware.proxy_fix import ProxyFix

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import db_adapter
from document_payload import build_documents_json, safe_json_loads

# --- Configuração do App ---
app = Flask(__name__, static_folder='build', static_url_path='/')
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
# AJUSTE: Tornando o CORS mais permissivo para garantir a comunicação.
# Isso permite requisições de qualquer origem, ideal para resolver este problema.
CORS(app)

# --- Configuração do Banco de Dados ---
DATABASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'rpa_refatorado.db'))
LEGALONE_DATABASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database.db'))
TAREFAS_CRIADAS_PATH = os.getenv(
    "TAREFAS_CRIADAS_PATH",
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tarefas_criadas'))
)
DOCUMENTOS_PATH = os.getenv(
    "DOCUMENTOS_PATH",
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'documentos'))
)
FLOW_API_KEY = os.getenv("ONENOTIFY_FLOW_API_KEY")
PUBLIC_BASE_URL = os.getenv("ONENOTIFY_PUBLIC_BASE_URL", "").rstrip("/")


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = db_adapter.connect_main()
    return db

def get_legalone_db():
    try:
        return db_adapter.connect_legalone()
    except Exception as e:
        app.logger.warning(f"Não foi possível conectar ao banco de dados Legal One em '{LEGALONE_DATABASE}': {e}")
        return None

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- Comandos CLI ---
def init_db():
    if db_adapter.is_postgres():
        click.echo('PostgreSQL configurado via DATABASE_URL; schema gerenciado pelo migrador.')
        return

    db = get_db()
    cursor = db.cursor()
    
    # Migrações da tabela 'notificacoes'
    cursor.execute("PRAGMA table_info(notificacoes)")
    cols_notificacoes = [col['name'] for col in cursor.fetchall()]
    if 'responsavel' not in cols_notificacoes:
        db.execute('ALTER TABLE notificacoes ADD COLUMN responsavel TEXT')
    if 'data_processamento' not in cols_notificacoes:
        db.execute('ALTER TABLE notificacoes ADD COLUMN data_processamento TEXT')
    if 'detalhes_erro' not in cols_notificacoes:
        db.execute('ALTER TABLE notificacoes ADD COLUMN detalhes_erro TEXT')
    if 'gerou_tarefa' not in cols_notificacoes:
        db.execute('ALTER TABLE notificacoes ADD COLUMN gerou_tarefa INTEGER DEFAULT 0')
    if 'origem' not in cols_notificacoes:
        db.execute('ALTER TABLE notificacoes ADD COLUMN origem TEXT DEFAULT "onenotify"')
    colunas_flow = {
        "rpa_status": "TEXT DEFAULT 'PENDENTE'",
        "bb_ciencia_status": "TEXT DEFAULT 'PENDENTE'",
        "human_status": "TEXT DEFAULT 'NOVO'",
        "flow_status": "TEXT DEFAULT 'NAO_ENVIADO'",
        "flow_external_id": "TEXT",
        "flow_synced_at": "TEXT",
        "flow_last_error": "TEXT",
        "documentos_json": "TEXT",
    }
    for coluna, tipo in colunas_flow.items():
        if coluna not in cols_notificacoes:
            db.execute(f"ALTER TABLE notificacoes ADD COLUMN {coluna} {tipo}")

    # Criação e migração da tabela 'usuarios'
    db.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE
        )
    ''')
    
    cursor.execute("PRAGMA table_info(usuarios)")
    cols_usuarios = [col['name'] for col in cursor.fetchall()]
    if 'perfil' not in cols_usuarios:
        click.echo("Aplicando migração: Adicionando coluna 'perfil' à tabela 'usuarios'...")
        db.execute("ALTER TABLE usuarios ADD COLUMN perfil TEXT DEFAULT 'Geral'")

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
        # Ajustado para incluir o perfil padrão na inserção via CLI
        db.execute("INSERT INTO usuarios (nome, perfil) VALUES (?, 'Geral')", (nome,))
        db.commit()
        click.echo(f"Usuário '{nome}' adicionado com sucesso com perfil 'Geral'.")
    except Exception:
        click.echo(f"Erro: Usuário '{nome}' já existe.")

app.cli.add_command(add_user_command)

# --- Funções Auxiliares ---
def table_has_column(db, table_name, column_name):
    return db_adapter.table_has_column(db, table_name, column_name)

def _require_flow_api_key():
    if not FLOW_API_KEY:
        app.logger.warning("ONENOTIFY_FLOW_API_KEY não configurada; endpoint /api/flow aceitando request local.")
        return None
    provided = request.headers.get("X-Onenotify-Api-Key")
    if provided != FLOW_API_KEY:
        return jsonify({"error": "API key inválida ou ausente no header X-Onenotify-Api-Key."}), 401
    return None

def _agg_distinct(column_name):
    if db_adapter.is_postgres():
        return f"STRING_AGG(DISTINCT {column_name}::text, '; ' ORDER BY {column_name}::text)"
    return f"GROUP_CONCAT(DISTINCT {column_name})"

def _parse_limit_offset():
    limit = min(max(int(request.args.get("limit", 50)), 1), 500)
    offset = max(int(request.args.get("offset", 0)), 0)
    return limit, offset

def _split_agg(value):
    if not value:
        return []
    separator = ";" if ";" in value else ","
    return [part.strip() for part in str(value).split(separator) if part.strip()]

def _empty_documents_payload(reason="not_generated"):
    return {
        "schema_version": "onenotify.documents.v1",
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "extraction_status": reason,
        "items": [],
    }

def _public_base_url() -> str:
    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL
    return request.url_root.rstrip("/")

def _document_api_path(document: dict) -> str | None:
    relative_path = document.get("relative_path")
    if relative_path:
        resolved = _resolve_document_path(os.path.join(DOCUMENTOS_PATH, relative_path))
        return resolved.replace("\\", "/") if resolved else None

    original_path = document.get("original_path")
    if original_path:
        resolved = _resolve_document_path(str(original_path))
        return resolved.replace("\\", "/") if resolved else None

    return None

def _decorate_document_links(documentos_json):
    if not isinstance(documentos_json, dict):
        return documentos_json

    base_url = _public_base_url()
    for item in documentos_json.get("items", []):
        if not isinstance(item, dict):
            continue

        api_path = _document_api_path(item)
        if not api_path:
            continue

        encoded_path = quote(api_path, safe="/")
        item["view_url"] = f"{base_url}/api/flow/documentos/view?path={encoded_path}"
        item["download_url"] = f"{base_url}/api/download?path={encoded_path}"
        item["access_mode"] = (
            "metadata_and_link"
            if item.get("extraction", {}).get("ocr_required")
            else "text_json"
        )

    return documentos_json

def _document_text(item: dict) -> str:
    extraction = item.get("extraction", {}) if isinstance(item, dict) else {}
    pages = extraction.get("pages", []) if isinstance(extraction, dict) else []
    texts = []
    for page in pages:
        if isinstance(page, dict) and page.get("text"):
            texts.append(str(page["text"]))
    return "\n\n".join(texts).strip()

def _build_conteudo_payload(andamentos, documentos_json, documentos_originais):
    fontes_texto = []
    andamentos_lista = andamentos if isinstance(andamentos, list) else []

    for index, andamento in enumerate(andamentos_lista, start=1):
        if not isinstance(andamento, dict):
            continue
        texto = (andamento.get("detalhes") or andamento.get("descricao") or "").strip()
        if texto:
            fontes_texto.append({
                "tipo": "andamento",
                "ordem": index,
                "data": andamento.get("data"),
                "titulo": andamento.get("descricao"),
                "texto": texto,
            })

    documentos_items = []
    if isinstance(documentos_json, dict):
        documentos_items = [item for item in documentos_json.get("items", []) if isinstance(item, dict)]

    documentos_com_texto = 0
    documentos_exigem_ocr = 0
    documentos_links = []

    for index, item in enumerate(documentos_items, start=1):
        extraction = item.get("extraction", {}) if isinstance(item.get("extraction"), dict) else {}
        ocr_required = bool(extraction.get("ocr_required"))
        if ocr_required:
            documentos_exigem_ocr += 1

        texto_documento = _document_text(item)
        if texto_documento:
            documentos_com_texto += 1
            fontes_texto.append({
                "tipo": "documento",
                "ordem": index,
                "nome": item.get("nome"),
                "classification": extraction.get("classification"),
                "ocr_required": ocr_required,
                "view_url": item.get("view_url"),
                "download_url": item.get("download_url"),
                "texto": texto_documento,
            })

        documentos_links.append({
            "nome": item.get("nome"),
            "relative_path": item.get("relative_path"),
            "access_mode": item.get("access_mode"),
            "classification": extraction.get("classification"),
            "ocr_required": ocr_required,
            "view_url": item.get("view_url"),
            "download_url": item.get("download_url"),
        })

    if documentos_items:
        total_documentos = len(documentos_items)
    elif isinstance(documentos_originais, list):
        total_documentos = len(documentos_originais)
    else:
        total_documentos = 0

    return {
        "tem_texto": bool(fontes_texto),
        "tem_texto_andamentos": any(fonte["tipo"] == "andamento" for fonte in fontes_texto),
        "tem_documentos": total_documentos > 0,
        "tem_documentos_com_texto": documentos_com_texto > 0,
        "tem_documentos_ocr_required": documentos_exigem_ocr > 0,
        "total_andamentos": len(andamentos_lista),
        "total_documentos": total_documentos,
        "total_documentos_com_texto": documentos_com_texto,
        "total_documentos_ocr_required": documentos_exigem_ocr,
        "fontes_texto": fontes_texto,
        "documentos_links": documentos_links,
    }

def _documents_payload_needs_refresh(documentos_json, documentos_originais) -> bool:
    if not documentos_originais:
        return False
    if not isinstance(documentos_json, dict):
        return True

    items = [item for item in documentos_json.get("items", []) if isinstance(item, dict)]
    if not items:
        return True

    for item in items:
        extraction = item.get("extraction", {}) if isinstance(item.get("extraction"), dict) else {}
        if item.get("exists") is False or extraction.get("status") == "missing_file":
            return True
        if not item.get("mime_type") and item.get("original_path"):
            return True

    return False

def _flow_group_to_payload(row, include_documents=False):
    row_dict = dict(row)
    andamentos = safe_json_loads(row_dict.get("andamentos"), fallback=[])
    documentos_json = safe_json_loads(row_dict.get("documentos_json"), fallback=None)
    documentos_originais = safe_json_loads(row_dict.get("documentos"), fallback=[])
    if include_documents and _documents_payload_needs_refresh(documentos_json, documentos_originais):
        documentos_json = build_documents_json(documentos_originais, base_dir=DOCUMENTOS_PATH)
    elif include_documents and not documentos_json:
        documentos_json = _empty_documents_payload()

    if not include_documents:
        documentos_json = None
    elif documentos_json:
        documentos_json = _decorate_document_links(documentos_json)

    npj = row_dict.get("npj") or row_dict.get("NPJ")
    data_notificacao = row_dict.get("data_notificacao")
    numero_processo = row_dict.get("numero_processo")
    polo = row_dict.get("polo")
    adverso_principal = row_dict.get("adverso_principal")
    ids = _split_agg(row_dict.get("ids"))

    return {
        "schema_version": "onenotify.flow-intake.v1",
        "external_group_id": f"{npj}|{data_notificacao}",
        "ids": [int(i) for i in ids if str(i).isdigit()],
        "npj": npj,
        "numero_processo_cnj": numero_processo,
        "data_notificacao": data_notificacao,
        "numero_processo": numero_processo,
        "polo": polo,
        "adverso_principal": adverso_principal,
        "processo": {
            "npj": npj,
            "numero_cnj": numero_processo,
            "polo": polo,
            "adverso_principal": adverso_principal,
        },
        "tipos_notificacao": _split_agg(row_dict.get("tipos_notificacao")),
        "status_legacy": _split_agg(row_dict.get("status_legacy")),
        "rpa_status": _split_agg(row_dict.get("rpa_status")),
        "bb_ciencia_status": _split_agg(row_dict.get("bb_ciencia_status")),
        "human_status": _split_agg(row_dict.get("human_status")),
        "flow_status": _split_agg(row_dict.get("flow_status")),
        "responsavel": row_dict.get("responsavel"),
        "data_processamento": row_dict.get("data_processamento"),
        "detalhes_erro": row_dict.get("detalhes_erro"),
        "andamentos": andamentos if isinstance(andamentos, list) else [],
        "documentos": documentos_json,
        "conteudo": _build_conteudo_payload(andamentos, documentos_json, documentos_originais),
        "source": "ONENOTIFY_BB",
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }

def _resolve_document_path(caminho: str) -> str | None:
    diretorio_base = os.path.abspath(DOCUMENTOS_PATH)
    raw_path = str(caminho or "").strip()
    if not raw_path:
        return None

    normalized = raw_path.replace("\\", "/")
    candidates = []

    windows_prefix = "C:/OneNotify/documentos/"
    if normalized.lower().startswith(windows_prefix.lower()):
        relative = normalized[len(windows_prefix):]
        candidates.append(os.path.join(diretorio_base, *relative.split("/")))

    documentos_prefix = "documentos/"
    if normalized.lower().startswith(documentos_prefix):
        relative = normalized[len(documentos_prefix):]
        candidates.append(os.path.join(diretorio_base, *relative.split("/")))

    base_normalized = diretorio_base.replace("\\", "/").rstrip("/") + "/"
    if normalized.startswith(base_normalized):
        candidates.append(normalized)

    candidates.append(raw_path)

    for candidate in candidates:
        caminho_seguro = os.path.abspath(candidate)
        try:
            if os.path.commonpath([diretorio_base, caminho_seguro]) == diretorio_base:
                return caminho_seguro
        except ValueError:
            continue

    return None

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
        
        inseridos = 0
        for index, row in df.iterrows():
            npj = str(row['npj'])
            data_notificacao = str(row['data'])
            
            if db_adapter.is_postgres():
                cursor.execute("""
                    INSERT INTO notificacoes (NPJ, data_notificacao, status, origem, tipo_notificacao)
                    SELECT ?, ?, 'Pendente', 'migracao', 'Migração de Dados'
                    WHERE NOT EXISTS (
                        SELECT 1 FROM notificacoes
                        WHERE NPJ = ? AND data_notificacao = ? AND origem = 'migracao'
                    )
                """, (npj, data_notificacao, npj, data_notificacao))
            else:
                cursor.execute("""
                    INSERT OR IGNORE INTO notificacoes (NPJ, data_notificacao, status, origem, tipo_notificacao)
                    VALUES (?, ?, 'Pendente', 'migracao', 'Migração de Dados')
                """, (npj, data_notificacao))
            if cursor.rowcount > 0:
                inseridos += 1

        db.commit()
        return jsonify({'message': f'{inseridos} de {len(df)} notificações foram adicionadas à fila de migração.'}), 201

    except Exception as e:
        app.logger.error(f"Erro ao processar planilha: {e}")
        return jsonify({'error': 'Falha ao processar o arquivo da planilha'}), 500

@app.route('/api/migracao/conciliar', methods=['POST'])
def conciliar_planilha():
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
        
        atualizados = 0
        data_processamento = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

        for index, row in df.iterrows():
            npj = str(row['npj'])
            data_notificacao = str(row['data'])
            
            # CORREÇÃO: Remove a restrição de status para conciliar qualquer notificação correspondente
            cursor.execute("""
                UPDATE notificacoes 
                SET status = 'Tratada', 
                    responsavel = 'Conciliado', 
                    data_processamento = ?
                WHERE NPJ = ? AND data_notificacao = ?
            """, (data_processamento, npj, data_notificacao))
            
            if cursor.rowcount > 0:
                atualizados += 1

        db.commit()
        return jsonify({'message': f'{atualizados} notificações correspondentes foram marcadas como "Tratada".'}), 200

    except Exception as e:
        app.logger.error(f"Erro ao conciliar planilha: {e}")
        return jsonify({'error': 'Falha ao processar o arquivo da planilha para conciliação'}), 500


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
    except Exception as e:
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
    except Exception as e:
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
            f"SELECT {db_adapter.distinct_npj_date_count_expr()} FROM notificacoes WHERE status = ?", (status_val,)
        ).fetchone()[0]
        stats[key] = count
    
    erro_count = db.execute(
        f"SELECT {db_adapter.distinct_npj_date_count_expr()} FROM notificacoes WHERE status LIKE 'Erro%'"
    ).fetchone()[0]
    stats['erro'] = erro_count
    
    return jsonify(stats)

@app.route('/api/notificacoes')
def get_notificacoes():
    status_filter = request.args.get('status', 'Pendente')
    responsavel_filter = request.args.get('responsavel')
    polo_filter = request.args.get('polo')
    data_filter = request.args.get('data') # Recebe a data no formato YYYY-MM-DD
    search_filter = (request.args.get('search') or '').strip()
    paginated = 'limit' in request.args or 'offset' in request.args
    limit = min(max(int(request.args.get('limit', 25)), 1), 100)
    offset = max(int(request.args.get('offset', 0)), 0)
    sort_key = request.args.get('sort', 'data_notificacao')
    sort_direction = request.args.get('direction', 'descending')
    direction_sql = 'ASC' if sort_direction == 'ascending' else 'DESC'
    db = get_db()
    
    params = []
    
    if status_filter == 'Erro':
        query_status = "WHERE status LIKE 'Erro%'"
    else:
        query_status = "WHERE status = ?"
        params.append(status_filter)

    gerou_tarefa_select = "MAX(gerou_tarefa) as gerou_tarefa," if table_has_column(db, "notificacoes", "gerou_tarefa") else ""
    query = db_adapter.grouped_notificacoes_select(gerou_tarefa_select).format(query_status=query_status)
    
    if responsavel_filter and responsavel_filter != 'Todos':
        query += " AND responsavel = ?"
        params.append(responsavel_filter)
    elif responsavel_filter == 'Sem Responsável':
        query += " AND (responsavel IS NULL OR responsavel = '')"

    if polo_filter and polo_filter != 'Todos':
        query += " AND polo = ?"
        params.append(polo_filter)
    
    if data_filter:
        try:
            # Converte YYYY-MM-DD para DD/MM/YYYY
            formatted_date = datetime.strptime(data_filter, '%Y-%m-%d').strftime('%d/%m/%Y')
            query += " AND data_notificacao = ?"
            params.append(formatted_date)
        except ValueError:
            # Ignora o filtro se a data for inválida
            app.logger.warning(f"Formato de data inválido recebido no filtro: {data_filter}")

    if search_filter:
        like_term = f"%{search_filter}%"
        if db_adapter.is_postgres():
            query += " AND (NPJ ILIKE ? OR numero_processo ILIKE ?)"
        else:
            query += " AND (LOWER(NPJ) LIKE LOWER(?) OR LOWER(numero_processo) LIKE LOWER(?))"
        params.extend([like_term, like_term])

    grouped_query = query + " GROUP BY NPJ, data_notificacao"

    if sort_key == 'NPJ':
        sort_expr = '"NPJ"' if db_adapter.is_postgres() else 'NPJ'
    elif sort_key == 'responsavel':
        sort_expr = 'responsavel'
    elif sort_key == 'numero_processo':
        sort_expr = 'numero_processo'
    else:
        sort_expr = (
            "to_date(data_notificacao, 'DD/MM/YYYY')"
            if db_adapter.is_postgres()
            else "substr(data_notificacao, 7, 4) || substr(data_notificacao, 4, 2) || substr(data_notificacao, 1, 2)"
        )

    order_query = (
        f' ORDER BY {sort_expr} {direction_sql}, data_notificacao DESC, "NPJ"'
        if db_adapter.is_postgres()
        else f" ORDER BY {sort_expr} {direction_sql}, data_notificacao DESC, NPJ"
    )

    if paginated:
        total = db.execute(
            f"SELECT COUNT(*) FROM ({grouped_query}) AS grouped_notificacoes",
            params,
        ).fetchone()[0]
        notificacoes_raw = db.execute(
            grouped_query + order_query + " LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
        return jsonify({
            "items": [dict(row) for row in notificacoes_raw],
            "total": total,
            "limit": limit,
            "offset": offset,
        })

    notificacoes_raw = db.execute(grouped_query + order_query, params).fetchall()
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

    caminho_seguro = _resolve_document_path(caminho)
    if caminho_seguro is None: return "Acesso negado.", 403
    if os.path.exists(caminho_seguro): return send_from_directory(os.path.dirname(caminho_seguro), os.path.basename(caminho_seguro), as_attachment=True)
    return "Arquivo não encontrado.", 404

@app.route('/api/documentos/view')
@app.route('/api/flow/documentos/view')
def view_document_file():
    caminho = request.args.get('path')
    if not caminho: return "Caminho do arquivo não fornecido.", 400

    caminho_seguro = _resolve_document_path(caminho)
    if caminho_seguro is None: return "Acesso negado.", 403
    if not os.path.exists(caminho_seguro): return "Arquivo não encontrado.", 404
    extensao = os.path.splitext(caminho_seguro)[1].lower()
    if extensao not in {'.pdf', '.txt', '.text'}:
        return "Visualização inline disponível apenas para PDF e TXT.", 400

    response = send_from_directory(
        os.path.dirname(caminho_seguro),
        os.path.basename(caminho_seguro),
        as_attachment=False,
        mimetype=mimetypes.guess_type(caminho_seguro)[0] or 'application/octet-stream',
    )
    response.headers['Content-Disposition'] = f'inline; filename="{os.path.basename(caminho_seguro)}"'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'private, max-age=300'
    return response

@app.route('/api/acoes/status', methods=['POST'])
def update_status():
    data = request.json
    ids_list = data.get('ids')
    novo_status = data.get('novo_status')
    gerou_tarefa = data.get('gerou_tarefa') 

    if not ids_list or not novo_status: return jsonify({'error': 'IDs e novo_status são obrigatórios'}), 400
    
    try:
        ids = [int(i) for i in ids_list]
    except (TypeError, ValueError):
        return jsonify({'error': 'IDs inválidos'}), 400
    
    db = get_db()
    placeholders = db_adapter.placeholders(len(ids))
    human_status_by_legacy = {
        "Tratada": "TRATADO",
        "Arquivado": "ARQUIVADO",
        "Pendente": "NOVO",
    }
    human_status = human_status_by_legacy.get(novo_status, "EM_TRATAMENTO")

    if novo_status == 'Tratada' and gerou_tarefa is not None:
        params = [novo_status, gerou_tarefa, human_status] + ids
        cursor = db.execute(
            f"UPDATE notificacoes SET status = ?, gerou_tarefa = ?, human_status = ? WHERE id IN ({placeholders})",
            params,
        )
    else:
        params = [novo_status, human_status] + ids
        cursor = db.execute(
            f"UPDATE notificacoes SET status = ?, human_status = ? WHERE id IN ({placeholders})",
            params,
        )
        
    db.commit()
    updated = cursor.rowcount if cursor.rowcount is not None and cursor.rowcount >= 0 else 0
    if updated == 0:
        return jsonify({'error': 'Nenhuma notificação foi atualizada. Recarregue a lista e tente novamente.'}), 404
    return jsonify({'message': f'{updated} notificações atualizadas para {novo_status}', 'updated': updated})

@app.route('/api/usuarios', methods=['GET'])
def get_usuarios():
    db = get_db()
    users_raw = db.execute("SELECT id, nome, perfil FROM usuarios ORDER BY nome").fetchall()
    return jsonify([dict(row) for row in users_raw])

@app.route('/api/usuarios', methods=['POST'])
def add_usuario():
    data = request.json
    nome = data.get('nome')
    perfil = data.get('perfil', 'Geral')
    if not nome: return jsonify({'error': 'Nome é obrigatório'}), 400
    if perfil not in ['Geral', 'Polo Ativo']:
        return jsonify({'error': 'Perfil inválido'}), 400
    try:
        db = get_db()
        db.execute("INSERT INTO usuarios (nome, perfil) VALUES (?, ?)", (nome, perfil))
        db.commit()
        return jsonify({'message': f'Usuário {nome} criado com sucesso'}), 201
    except Exception:
        return jsonify({'error': f'Usuário {nome} já existe'}), 409

@app.route('/api/usuarios/<int:user_id>/perfil', methods=['PUT'])
def update_perfil(user_id):
    data = request.json
    perfil = data.get('perfil')
    if not perfil or perfil not in ['Geral', 'Polo Ativo']:
        return jsonify({'error': 'Perfil inválido'}), 400
    
    try:
        db = get_db()
        cursor = db.execute("UPDATE usuarios SET perfil = ? WHERE id = ?", (perfil, user_id))
        if cursor.rowcount == 0:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        db.commit()
        return jsonify({'message': 'Perfil do usuário atualizado com sucesso'})
    except Exception as e:
        app.logger.error(f"Erro ao atualizar perfil do usuário: {e}")
        return jsonify({'error': 'Falha ao atualizar o perfil no banco de dados'}), 500

@app.route('/api/usuarios/<int:user_id>', methods=['DELETE'])
def delete_usuario(user_id):
    db = get_db()
    db.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
    db.commit()
    return jsonify({'message': 'Usuário removido com sucesso'})

@app.route('/api/flow/health')
def flow_health():
    auth_response = _require_flow_api_key()
    if auth_response:
        return auth_response
    return jsonify({
        "status": "ok",
        "service": "onenotify-flow-api",
        "schema_version": "onenotify.flow-intake.v1",
    })

@app.route('/api/flow/notificacoes')
def flow_list_notificacoes():
    auth_response = _require_flow_api_key()
    if auth_response:
        return auth_response

    limit, offset = _parse_limit_offset()
    include_documents = request.args.get("include_documents", "false").lower() == "true"
    db = get_db()
    where = ["1 = 1"]
    params = []

    flow_status = request.args.get("flow_status")
    if flow_status:
        where.append("flow_status = ?")
        params.append(flow_status)

    rpa_status = request.args.get("rpa_status")
    if rpa_status:
        where.append("rpa_status = ?")
        params.append(rpa_status)

    human_status = request.args.get("human_status")
    if human_status:
        where.append("human_status = ?")
        params.append(human_status)

    npj = request.args.get("npj")
    if npj:
        where.append("NPJ = ?")
        params.append(npj)

    data_notificacao = request.args.get("data_notificacao")
    if data_notificacao:
        where.append("data_notificacao = ?")
        params.append(data_notificacao)

    where_sql = " AND ".join(where)
    total = db.execute(
        f"SELECT COUNT(*) FROM (SELECT 1 FROM notificacoes WHERE {where_sql} GROUP BY NPJ, data_notificacao) grouped",
        params,
    ).fetchone()[0]

    query = f"""
        SELECT
            NPJ as npj,
            data_notificacao,
            MAX(adverso_principal) as adverso_principal,
            MAX(numero_processo) as numero_processo,
            MAX(polo) as polo,
            {_agg_distinct('id')} as ids,
            {_agg_distinct('tipo_notificacao')} as tipos_notificacao,
            {_agg_distinct('status')} as status_legacy,
            {_agg_distinct('rpa_status')} as rpa_status,
            {_agg_distinct('bb_ciencia_status')} as bb_ciencia_status,
            {_agg_distinct('human_status')} as human_status,
            {_agg_distinct('flow_status')} as flow_status,
            MAX(responsavel) as responsavel,
            MAX(data_processamento) as data_processamento,
            MAX(detalhes_erro) as detalhes_erro,
            MAX(andamentos) as andamentos,
            MAX(documentos) as documentos,
            MAX(documentos_json) as documentos_json
        FROM notificacoes
        WHERE {where_sql}
        GROUP BY NPJ, data_notificacao
        ORDER BY MAX(data_criacao) DESC, NPJ
        LIMIT ? OFFSET ?
    """
    rows = db.execute(query, params + [limit, offset]).fetchall()
    return jsonify({
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_flow_group_to_payload(row, include_documents=include_documents) for row in rows],
    })

@app.route('/api/flow/notificacoes/<path:external_group_id>')
def flow_get_notificacao(external_group_id):
    auth_response = _require_flow_api_key()
    if auth_response:
        return auth_response
    if "|" not in external_group_id:
        return jsonify({"error": "external_group_id deve usar o formato NPJ|DD/MM/AAAA"}), 400
    npj, data_notificacao = external_group_id.split("|", 1)
    db = get_db()
    query = f"""
        SELECT
            NPJ as npj,
            data_notificacao,
            MAX(adverso_principal) as adverso_principal,
            MAX(numero_processo) as numero_processo,
            MAX(polo) as polo,
            {_agg_distinct('id')} as ids,
            {_agg_distinct('tipo_notificacao')} as tipos_notificacao,
            {_agg_distinct('status')} as status_legacy,
            {_agg_distinct('rpa_status')} as rpa_status,
            {_agg_distinct('bb_ciencia_status')} as bb_ciencia_status,
            {_agg_distinct('human_status')} as human_status,
            {_agg_distinct('flow_status')} as flow_status,
            MAX(responsavel) as responsavel,
            MAX(data_processamento) as data_processamento,
            MAX(detalhes_erro) as detalhes_erro,
            MAX(andamentos) as andamentos,
            MAX(documentos) as documentos,
            MAX(documentos_json) as documentos_json
        FROM notificacoes
        WHERE NPJ = ? AND data_notificacao = ?
        GROUP BY NPJ, data_notificacao
    """
    row = db.execute(query, (npj, data_notificacao)).fetchone()
    if row is None:
        return jsonify({"error": "Grupo não encontrado"}), 404
    return jsonify(_flow_group_to_payload(row, include_documents=True))

@app.route('/api/flow/sync-status', methods=['POST'])
def flow_update_sync_status():
    auth_response = _require_flow_api_key()
    if auth_response:
        return auth_response

    payload = request.json or {}
    flow_status = payload.get("flow_status")
    allowed = {"NAO_ENVIADO", "ENVIADO", "ACEITO", "REJEITADO", "SINCRONIZADO", "ERRO"}
    if flow_status not in allowed:
        return jsonify({"error": f"flow_status inválido. Use um de: {sorted(allowed)}"}), 400

    ids = payload.get("ids") or []
    npj = payload.get("npj")
    data_notificacao = payload.get("data_notificacao")
    if not ids and payload.get("external_group_id") and "|" in payload["external_group_id"]:
        npj, data_notificacao = payload["external_group_id"].split("|", 1)

    flow_external_id = payload.get("flow_external_id")
    flow_last_error = payload.get("flow_last_error")
    flow_synced_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    db = get_db()

    if ids:
        clean_ids = [int(i) for i in ids]
        placeholders = db_adapter.placeholders(len(clean_ids))
        params = [flow_status, flow_external_id, flow_synced_at, flow_last_error] + clean_ids
        cursor = db.execute(
            f"""
            UPDATE notificacoes
            SET flow_status = ?, flow_external_id = ?, flow_synced_at = ?, flow_last_error = ?
            WHERE id IN ({placeholders})
            """,
            params,
        )
    elif npj and data_notificacao:
        cursor = db.execute(
            """
            UPDATE notificacoes
            SET flow_status = ?, flow_external_id = ?, flow_synced_at = ?, flow_last_error = ?
            WHERE NPJ = ? AND data_notificacao = ?
            """,
            (flow_status, flow_external_id, flow_synced_at, flow_last_error, npj, data_notificacao),
        )
    else:
        return jsonify({"error": "Informe ids ou external_group_id/npj+data_notificacao."}), 400

    db.commit()
    return jsonify({
        "updated": cursor.rowcount or 0,
        "flow_status": flow_status,
        "flow_synced_at": flow_synced_at,
    })

# --- Servir React App ---
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

