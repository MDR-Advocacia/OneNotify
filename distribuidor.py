# arquivo: distribuidor.py
import logging
import database
from itertools import cycle

# Configuração básica de log para este script
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] - %(message)s')

def distribuir_tarefas():
    """
    Busca notificações processadas e as distribui entre os usuários ativos
    no formato round-robin.
    """
    logging.info("--- Iniciando a Distribuição de Tarefas ---")

    # 1. Buscar tarefas prontas e sem dono
    notificacoes = database.obter_notificacoes_para_distribuir()
    if not notificacoes:
        logging.info("Nenhuma notificação nova processada para distribuir. Encerrando.")
        return

    # 2. Buscar usuários que podem receber tarefas
    usuarios = database.obter_usuarios_ativos_para_distribuicao()
    if not usuarios:
        logging.warning("Nenhuma notificação foi distribuída porque não há usuários ativos para receber tarefas.")
        return

    logging.info(f"Encontradas {len(notificacoes)} notificações para distribuir entre {len(usuarios)} usuários.")

    # 3. Criar um ciclo infinito de usuários para a distribuição
    ciclo_usuarios = cycle(usuarios)
    
    # 4. Atribuir cada notificação a um usuário
    for notificacao in notificacoes:
        usuario_atual = next(ciclo_usuarios)
        id_notificacao = notificacao['id']
        id_usuario = usuario_atual['id']
        
        database.atribuir_notificacao_a_usuario(id_notificacao, id_usuario)
        logging.info(f"  -> Notificação NPJ {notificacao['NPJ']} (ID: {id_notificacao}) atribuída para o usuário '{usuario_atual['nome']}' (ID: {id_usuario})")
    
    logging.info(f"--- Distribuição Concluída: {len(notificacoes)} tarefas foram atribuídas. ---")

if __name__ == "__main__":
    # Garante que o banco de dados esteja com a estrutura mais recente
    database.inicializar_banco()
    distribuir_tarefas()