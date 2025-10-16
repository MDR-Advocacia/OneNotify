# -*- coding: utf-8 -*-
import sqlite3
import os
import logging
from itertools import cycle

# --- Configuração ---
DATABASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'rpa_refatorado.db'))
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

def redistribuir_responsaveis():
    """
    Realiza a redistribuição de todas as notificações existentes no banco de dados
    com base nas novas regras de perfil de usuário (Geral vs. Polo Ativo).
    """
    conn = None
    try:
        logging.info(f"Conectando ao banco de dados em: {DATABASE_PATH}")
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Buscar todos os usuários e seus perfis
        logging.info("Buscando usuários e seus perfis...")
        cursor.execute("SELECT nome, perfil FROM usuarios ORDER BY nome")
        usuarios_raw = cursor.fetchall()
        
        if not usuarios_raw:
            logging.error("Nenhum usuário encontrado no banco de dados. Abortando a redistribuição.")
            return

        usuarios_gerais = [u['nome'] for u in usuarios_raw if u['perfil'] == 'Geral']
        usuarios_polo_ativo = [u['nome'] for u in usuarios_raw if u['perfil'] == 'Polo Ativo']
        
        if not usuarios_gerais:
            logging.error("Nenhum usuário com perfil 'Geral' encontrado. É necessário ter ao menos um para processar todas as notificações. Abortando.")
            return

        logging.info(f"Usuários com perfil 'Geral': {usuarios_gerais}")
        logging.info(f"Usuários com perfil 'Polo Ativo': {usuarios_polo_ativo}")

        # Pool de usuários para notificações de Polo Ativo (todos os usuários)
        pool_polo_ativo = usuarios_gerais + usuarios_polo_ativo
        
        # 2. Buscar todas as notificações já processadas (que possuem um responsável)
        logging.info("Buscando todas as notificações já processadas para redistribuir...")
        cursor.execute("SELECT id, polo FROM notificacoes WHERE responsavel IS NOT NULL AND responsavel != ''")
        notificacoes = cursor.fetchall()

        if not notificacoes:
            logging.info("Nenhuma notificação para redistribuir. Encerrando.")
            return

        logging.info(f"Total de {len(notificacoes)} notificações a serem redistribuídas.")

        # 3. Preparar iteradores cíclicos para as listas de usuários (round-robin)
        ciclo_geral = cycle(usuarios_gerais)
        ciclo_polo_ativo = cycle(pool_polo_ativo)
        
        updates_gerais = []
        updates_polo_ativo = []

        # 4. Separar notificações e preparar os updates
        for notificacao in notificacoes:
            if notificacao['polo'] == 'Ativo':
                novo_responsavel = next(ciclo_polo_ativo)
                updates_polo_ativo.append((novo_responsavel, notificacao['id']))
            else: # Passivo, Nulo ou qualquer outro valor
                novo_responsavel = next(ciclo_geral)
                updates_gerais.append((novo_responsavel, notificacao['id']))

        # 5. Executar as atualizações no banco de dados
        logging.info("Iniciando a atualização no banco de dados...")
        if updates_polo_ativo:
            logging.info(f"Redistribuindo {len(updates_polo_ativo)} notificações de 'Polo Ativo'...")
            cursor.executemany("UPDATE notificacoes SET responsavel = ? WHERE id = ?", updates_polo_ativo)
        
        if updates_gerais:
            logging.info(f"Redistribuindo {len(updates_gerais)} notificações de outros polos (Passivo, Nulo, etc)...")
            cursor.executemany("UPDATE notificacoes SET responsavel = ? WHERE id = ?", updates_gerais)

        conn.commit()
        logging.info(f"Redistribuição concluída com sucesso! {cursor.rowcount} registros atualizados no total.")

    except sqlite3.Error as e:
        logging.error(f"Ocorreu um erro de banco de dados: {e}", exc_info=True)
        if conn:
            conn.rollback()
    except Exception as e:
        logging.error(f"Ocorreu um erro inesperado: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()
            logging.info("Conexão com o banco de dados fechada.")

if __name__ == '__main__':
    redistribuir_responsaveis()
