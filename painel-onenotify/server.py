from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import sqlite3
import json
import sys
import os

# Adiciona o diretório pai ao path para encontrar os módulos do projeto principal
diretorio_pai = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(diretorio_pai)

# Importa as funções do database.py
from database import (
    atualizar_status_de_notificacoes_por_ids,
    corrigir_e_consolidar_datas_por_ids
)

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(diretorio_pai, 'rpa_refatorado.db')
DOCUMENTOS_PATH = os.path.join(diretorio_pai, 'documentos')


def query_db(query, args=(), one=False):
    """Função auxiliar para conectar e consultar o banco de dados."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(query, args)
            rv = cur.fetchall()
            return (rv[0] if rv else None) if one else rv
    except sqlite3.Error as e:
        print(f"Erro no banco de dados: {e}")
        return None

@app.route('/api/logs', methods=['GET'])
def get_logs():
    logs = query_db("SELECT * FROM logs_execucao ORDER BY id DESC")
    if logs is None:
        return jsonify({"error": "Não foi possível buscar os logs"}), 500
    return jsonify([dict(log) for log in logs])

@app.route('/api/notificacoes', methods=['GET'])
def get_notificacoes():
    notificacoes_data = query_db("SELECT * FROM notificacoes ORDER BY id DESC")
    if notificacoes_data is None:
        return jsonify({"error": "Não foi possível buscar as notificações"}), 500
        
    lista_notificacoes = []
    for n in notificacoes_data:
        notificacao_dict = dict(n)
        try:
            if notificacao_dict.get('andamentos'):
                notificacao_dict['andamentos'] = json.loads(notificacao_dict['andamentos'])
            if notificacao_dict.get('documentos'):
                notificacao_dict['documentos'] = json.loads(notificacao_dict['documentos'])
        except (json.JSONDecodeError, TypeError):
            pass
        lista_notificacoes.append(notificacao_dict)

    return jsonify(lista_notificacoes)

@app.route('/api/notificacoes/bulk-update-status', methods=['POST'])
def bulk_update_status():
    data = request.get_json()
    if not data or 'ids' not in data or 'status' not in data:
        return jsonify({'error': 'Dados inválidos fornecidos.'}), 400

    ids = data.get('ids')
    novo_status = data.get('status')

    if not isinstance(ids, list) or not ids:
        return jsonify({'message': 'Nenhum ID fornecido para atualização.', 'updated_rows': 0}), 200

    try:
        updated_rows = atualizar_status_de_notificacoes_por_ids(ids, novo_status)
        return jsonify({'updated_rows': updated_rows})
    except Exception as e:
        print(f"Erro ao executar atualização em massa: {e}")
        return jsonify({'error': f'Erro interno do servidor: {e}'}), 500

@app.route('/api/notificacoes/bulk-update-date', methods=['POST'])
def bulk_update_date():
    data = request.get_json()
    if not data or 'ids' not in data or 'nova_data' not in data:
        return jsonify({'error': 'Dados inválidos fornecidos.'}), 400

    ids = data.get('ids')
    nova_data = data.get('nova_data')

    if not isinstance(ids, list) or not ids:
        return jsonify({'message': 'Nenhum ID fornecido para atualização.'}), 200

    try:
        result = corrigir_e_consolidar_datas_por_ids(ids, nova_data)
        return jsonify(result)
    except Exception as e:
        print(f"Erro ao executar atualização de data em massa: {e}")
        return jsonify({'error': f'Erro interno do servidor: {e}'}), 500

@app.route('/download-documento', methods=['GET'])
def download_documento():
    caminho_relativo = request.args.get('path')
    if not caminho_relativo:
        return "Caminho do arquivo não fornecido.", 400

    # Medida de segurança: Garante que o caminho é seguro e dentro do diretório esperado
    caminho_seguro = os.path.normpath(os.path.join(DOCUMENTOS_PATH, caminho_relativo))
    if not caminho_seguro.startswith(DOCUMENTOS_PATH):
        return "Acesso negado.", 403

    try:
        if os.path.exists(caminho_seguro) and os.path.isfile(caminho_seguro):
            return send_file(caminho_seguro, as_attachment=True)
        else:
            return "Arquivo não encontrado.", 404
    except Exception as e:
        print(f"Erro ao tentar baixar o arquivo {caminho_seguro}: {e}")
        return "Erro ao processar o download.", 500

if __name__ == '__main__':
    from database import inicializar_banco
    inicializar_banco()
    app.run(debug=True, port=5000)

