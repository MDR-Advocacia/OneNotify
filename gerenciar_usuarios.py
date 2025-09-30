# arquivo: gerenciar_usuarios.py
import argparse
import hashlib
import getpass
import database
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

def criar_primeiro_admin():
    """Função para guiar a criação do primeiro usuário administrador."""
    logging.info("--- Criando o primeiro usuário Administrador ---")
    nome_completo = input("Nome completo do admin: ")
    login = input("Login do admin: ")
    
    while True:
        senha = getpass.getpass("Senha do admin: ")
        senha_confirma = getpass.getpass("Confirme a senha: ")
        if senha == senha_confirma:
            break
        logging.warning("As senhas não coincidem. Tente novamente.")
            
    hash_senha = hashlib.sha256(senha.encode()).hexdigest()
    
    user_id = database.criar_usuario(nome_completo, login, hash_senha, perfil='admin')
    if user_id:
        logging.info(f"\n[SUCESSO] Administrador '{nome_completo}' criado com ID {user_id}.")
    else:
        logging.error("\n[ERRO] Não foi possível criar o administrador. Verifique se o login já existe.")

def criar_novo_usuario():
    """Função para criar usuários comuns."""
    logging.info("\n--- Criando um novo usuário ---")
    nome_completo = input("Nome completo: ")
    login = input("Login: ")
    senha = getpass.getpass("Senha: ")
    hash_senha = hashlib.sha256(senha.encode()).hexdigest()

    user_id = database.criar_usuario(nome_completo, login, hash_senha, perfil='usuario')
    if user_id:
        logging.info(f"\n[SUCESSO] Usuário '{nome_completo}' criado com ID {user_id}.")
    else:
        logging.error("\n[ERRO] Não foi possível criar o usuário. Verifique se o login já existe.")

def listar_todos_usuarios():
    """Lista todos os usuários cadastrados."""
    logging.info("\n--- Lista de Usuários Cadastrados ---")
    usuarios = database.listar_usuarios()
    if not usuarios:
        logging.info("Nenhum usuário encontrado.")
        return
        
    print(f"{'ID':<5} | {'Nome Completo':<30} | {'Login':<15} | {'Perfil':<10} | {'Ativo'}")
    print("-" * 75)
    for user in usuarios:
        ativo_str = "Sim" if user[4] == 1 else "Não"
        print(f"{user[0]:<5} | {user[1]:<30} | {user[2]:<15} | {user[3]:<10} | {ativo_str}")

def main():
    parser = argparse.ArgumentParser(
        description="Gerenciador de usuários do OneNotify.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'acao', 
        choices=['init', 'criar', 'listar'], 
        help="A ação a ser executada:\n"
             "  init    - Cria o primeiro usuário administrador do sistema.\n"
             "  criar   - Cria um novo usuário com perfil padrão.\n"
             "  listar  - Exibe todos os usuários cadastrados."
    )
    
    args = parser.parse_args()

    # Garante que as tabelas existam antes de qualquer operação
    database.inicializar_banco() 

    if args.acao == 'init':
        # Verifica se já existe um admin
        if any(u[3] == 'admin' for u in (database.listar_usuarios() or [])):
            logging.warning("Um administrador já existe. Use a ação 'criar' para adicionar novos usuários.")
            return
        criar_primeiro_admin()
    elif args.acao == 'criar':
        criar_novo_usuario()
    elif args.acao == 'listar':
        listar_todos_usuarios()

if __name__ == "__main__":
    main()

