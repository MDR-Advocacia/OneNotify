import sqlite3
import json
import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# --- CONFIGURAÇÃO ---
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

# Define o caminho base para o diretório de documentos de forma segura
# O servidor está em 'painel-onenotify', então subimos um nível para a raiz do projeto
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_NOME = os.path.join(BASE_DIR, "rpa_refatorado.db")
DOCUMENTOS_DIR = os.path.join(BASE_DIR, "documentos")

# --- FUNÇÕES AUXILIARES ---
def get_db_connection():
    conn = sqlite3.connect(DB_NOME)
    conn.row_factory = sqlite3.Row
    return conn

# --- ROTAS DA API ---

@app.route('/api/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    # ... (código existente inalterado) ...
    try:
        conn = get_db_connection()
        stats = conn.execute("SELECT status, COUNT(*) as count FROM notificacoes GROUP BY status").fetchall()
        conn.close()
        
        stats_dict = {s['status'].lower().replace(' ', '_'): s['count'] for s in stats}
        return jsonify(stats_dict)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/notificacoes', methods=['GET'])
def get_notificacoes():
    status = request.args.get('status', 'Pendente')
    # ... (código existente inalterado) ...
    try:
        conn = get_db_connection()
        query = """
            SELECT 
                NPJ, 
                data_notificacao,
                MAX(numero_processo) as numero_processo,
                GROUP_CONCAT(id, ',') as ids_string,
                GROUP_CONCAT(tipo_notificacao, '; ') as tipos_notificacao
            FROM notificacoes
            WHERE status = ?
            GROUP BY NPJ, data_notificacao
            ORDER BY data_notificacao DESC
        """
        notificacoes = conn.execute(query, (status,)).fetchall()
        conn.close()
        
        # Processa os IDs para serem uma lista de inteiros
        result = []
        for n in notificacoes:
            n_dict = dict(n)
            n_dict['ids'] = [int(id_str) for id_str in n_dict['ids_string'].split(',')]
            n_dict['status'] = status # Adiciona o status ao objeto
            del n_dict['ids_string']
            result.append(n_dict)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/notificacao-detalhes', methods=['GET'])
def get_notificacao_detalhes():
    npj = request.args.get('npj')
    data = request.args.get('data')
    # ... (código existente inalterado) ...
    if not npj or not data:
        return jsonify({"error": "NPJ e data são obrigatórios"}), 400
    try:
        conn = get_db_connection()
        # Busca a primeira notificação que corresponde para pegar os dados JSON
        notificacao = conn.execute(
            "SELECT andamentos, documentos FROM notificacoes WHERE NPJ = ? AND data_notificacao = ? LIMIT 1",
            (npj, data)
        ).fetchone()
        conn.close()

        if notificacao:
            andamentos = json.loads(notificacao['andamentos']) if notificacao['andamentos'] else []
            documentos = json.loads(notificacao['documentos']) if notificacao['documentos'] else []
            return jsonify({"andamentos": andamentos, "documentos": documentos})
        else:
            return jsonify({"andamentos": [], "documentos": []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- ROTA DE DOWNLOAD CORRIGIDA ---
@app.route('/api/download-documento', methods=['GET'])
def download_documento():
    caminho_completo = request.args.get('caminho')
    if not caminho_completo:
        return "Caminho do arquivo não fornecido.", 400

    # Medida de segurança: garante que o caminho solicitado está dentro do diretório de documentos
    caminho_sanitizado = os.path.abspath(caminho_completo)
    if not caminho_sanitizado.startswith(DOCUMENTOS_DIR):
        return "Acesso negado.", 403

    try:
        # Extrai o diretório e o nome do arquivo do caminho completo
        diretorio, nome_arquivo = os.path.split(caminho_sanitizado)
        # CORREÇÃO: Usando a variável 'diretorio' (em português) que foi definida acima.
        return send_from_directory(diretorio, nome_arquivo, as_attachment=True)
    except FileNotFoundError:
        return "Arquivo não encontrado.", 404
    except Exception as e:
        return str(e), 500

@app.route('/api/atualizar-status', methods=['POST'])
def atualizar_status():
    data = request.json
    # ... (código existente inalterado) ...
    ids = data.get('ids', [])
    novo_status = data.get('novo_status')

    if not ids or not novo_status:
        return jsonify({"message": "IDs e novo_status são obrigatórios"}), 400

    try:
        conn = get_db_connection()
        placeholders = ', '.join(['?'] * len(ids))
        query = f"UPDATE notificacoes SET status = ? WHERE id IN ({placeholders})"
        params = [novo_status] + ids
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        updated_count = cursor.rowcount
        conn.close()
        
        return jsonify({"message": f"{updated_count} notificações atualizadas para '{novo_status}' com sucesso!"})

    except Exception as e:
        return jsonify({"message": f"Erro ao atualizar status: {str(e)}"}), 500

@app.route('/api/corrigir-data', methods=['POST'])
def corrigir_data():
    data = request.json
    # ... (código existente inalterado) ...
    ids = data.get('ids', [])
    nova_data = data.get('nova_data')

    if not ids or not nova_data:
        return jsonify({"message": "IDs e nova_data são obrigatórios"}), 400
    
    # Simples validação de formato de data
    try:
        from datetime import datetime
        datetime.strptime(nova_data, '%d/%m/%Y')
    except ValueError:
        return jsonify({"message": "Formato de data inválido. Use DD/MM/AAAA."}), 400

    try:
        conn = get_db_connection()
        placeholders = ', '.join(['?'] * len(ids))
        query = f"UPDATE notificacoes SET data_notificacao = ? WHERE id IN ({placeholders})"
        params = [nova_data] + ids
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        updated_count = cursor.rowcount
        conn.close()

        return jsonify({"message": f"Data de {updated_count} notificações corrigida com sucesso!"})

    except Exception as e:
        return jsonify({"message": f"Erro ao corrigir data: {str(e)}"}), 500


if __name__ == '__main__':
    # Garante que o diretório de documentos exista
    os.makedirs(DOCUMENTOS_DIR, exist_ok=True)
    app.run(debug=True, port=5001)

