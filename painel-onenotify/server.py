from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
import sqlite3
import json
import sys
import os
import hashlib
import jwt
import datetime
from functools import wraps

# Adiciona o diretório pai ao path para encontrar os módulos do projeto principal
diretorio_pai = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(diretorio_pai)

# Importa as funções do seu database.py
import database

app = Flask(__name__, static_folder='build', static_url_path='/')
CORS(app)

# --- CONFIGURAÇÕES ---
DB_PATH = os.path.join(diretorio_pai, 'rpa_refatorado.db')
DOCUMENTOS_PATH = os.path.join(diretorio_pai, 'documentos')
app.config['SECRET_KEY'] = 'chave-secreta-muito-segura-para-onenotify'

# --- DECORATOR PARA PROTEGER ROTAS (CORRIGIDO) ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]

        if not token:
            return jsonify({'mensagem': 'Token de autenticação está faltando!'}), 401

        try:
            # Decodifica o token para obter os dados do usuário (payload)
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            
            # Busca o usuário no banco para garantir que ele ainda existe e está ativo
            with sqlite3.connect(database.DB_NOME) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(f"SELECT * FROM {database.TABELA_USUARIOS} WHERE id = ? AND ativo = 1", (data['id'],))
                current_user_row = cursor.fetchone()

            if not current_user_row:
                 return jsonify({'mensagem': 'Usuário do token não encontrado ou inativo.'}), 401
            
            # Converte a linha do banco para um dicionário
            current_user = dict(current_user_row)

        except jwt.ExpiredSignatureError:
            return jsonify({'mensagem': 'Token expirado!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'mensagem': 'Token inválido!'}), 401
        except Exception as e:
            return jsonify({'mensagem': 'Erro na autenticação do token!', 'error': str(e)}), 500
        
        # Passa o usuário encontrado para a rota protegida
        return f(current_user, *args, **kwargs)
    return decorated


# --- SUAS ROTAS ORIGINAIS (AGORA PROTEGIDAS) ---
@app.route('/api/notificacoes')
@token_required
def get_notificacoes(current_user):
    user_id = current_user['id']
    notificacoes = database.obter_notificacoes_por_usuario(user_id)
    return jsonify(notificacoes)

@app.route('/api/update-status', methods=['POST'])
@token_required
def update_status(current_user):
    data = request.get_json()
    ids = data.get('ids')
    novo_status = data.get('novo_status')
    try:
        updated_count = database.atualizar_status_de_notificacoes_por_ids(ids, novo_status)
        return jsonify({'updated': updated_count})
    except Exception as e:
        return jsonify({'error': f'Erro interno do servidor: {e}'}), 500

@app.route('/api/update-data', methods=['POST'])
@token_required
def update_data(current_user):
    data = request.get_json()
    ids = data.get('ids')
    nova_data = data.get('nova_data')
    try:
        result = database.corrigir_e_consolidar_datas_por_ids(ids, nova_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Erro interno do servidor: {e}'}), 500

@app.route('/download-documento', methods=['GET'])
@token_required
def download_documento(current_user):
    caminho_relativo = request.args.get('path')
    if not caminho_relativo:
        return "Caminho do arquivo não fornecido.", 400

    caminho_seguro = os.path.normpath(os.path.join(DOCUMENTOS_PATH, caminho_relativo))
    if not caminho_seguro.startswith(os.path.abspath(DOCUMENTOS_PATH)):
        return "Acesso negado.", 403

    try:
        if os.path.exists(caminho_seguro) and os.path.isfile(caminho_seguro):
            return send_file(caminho_seguro, as_attachment=True)
        else:
            return "Arquivo não encontrado.", 404
    except Exception as e:
        return str(e), 500

# --- ROTA DE LOGIN ---
@app.route('/api/login', methods=['POST'])
def login():
    auth_data = request.get_json()
    login_usuario = auth_data.get('login')
    senha_usuario = auth_data.get('senha')
    
    if not login_usuario or not senha_usuario:
        return jsonify({"mensagem": "Login e senha são obrigatórios."}), 400
    
    hash_senha = hashlib.sha256(senha_usuario.encode()).hexdigest()
    user = database.validar_usuario(login_usuario, hash_senha)

    if not user:
        return jsonify({"mensagem": "Credenciais inválidas ou usuário inativo."}), 401

    token = jwt.encode({
        'id': user['id'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    }, app.config['SECRET_KEY'], algorithm="HS256")

    return jsonify({
        "mensagem": "Login bem-sucedido!",
        "token": token,
        "usuario": user
    })

# --- ROTAS PARA SERVIR O FRONTEND ---
@app.route('/')
def serve():
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'build'), 'index.html')

@app.errorhandler(404)
def not_found(e):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'build'), 'index.html')

if __name__ == '__main__':
    database.inicializar_banco()
    app.run(debug=True, port=5001)

