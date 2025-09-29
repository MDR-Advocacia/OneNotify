import sqlite3
import json
from flask import Flask, jsonify
from flask_cors import CORS # Importa o CORS

app = Flask(__name__)
CORS(app) # Habilita o CORS para toda a aplicação

DB_PATH = '../rpa_refatorado.db'

def get_db_connection():
    """Cria uma conexão com o banco de dados."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Busca os últimos 10 logs de execução."""
    try:
        conn = get_db_connection()
        logs = conn.execute('SELECT * FROM logs_execucao ORDER BY timestamp DESC LIMIT 10').fetchall()
        conn.close()
        return jsonify([dict(ix) for ix in logs])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/notificacoes', methods=['GET'])
def get_notificacoes():
    """Busca todas as notificações, ordenadas pela data de criação."""
    try:
        conn = get_db_connection()
        notificacoes = conn.execute('SELECT * FROM notificacoes ORDER BY data_criacao DESC').fetchall()
        conn.close()
        
        lista_notificacoes = []
        for row in notificacoes:
            row_dict = dict(row)
            try:
                if row_dict.get('andamentos'):
                    row_dict['andamentos'] = json.loads(row_dict['andamentos'])
                if row_dict.get('documentos'):
                    row_dict['documentos'] = json.loads(row_dict['documentos'])
            except (json.JSONDecodeError, TypeError):
                pass
            lista_notificacoes.append(row_dict)

        return jsonify(lista_notificacoes)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

