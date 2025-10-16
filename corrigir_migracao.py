import sqlite3
import os
import logging
import re
from tqdm import tqdm

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuração do Banco de Dados ---
DATABASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'rpa_refatorado.db'))

def corrigir_dados_migrados_invertidos():
    """
    Identifica notificações da origem 'migracao' onde os campos NPJ e data_notificacao
    estão invertidos. Tenta corrigir o registro; se encontrar um duplicado, apaga o registro invertido.
    """
    conn = None
    corrigidos = 0
    apagados = 0
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        logging.info("Conectado ao banco de dados para correção de dados de migração.")

        # Regex para identificar formato de NPJ e data
        regex_npj = re.compile(r"^\d{4}/\d{1,7}-\d{3}$")
        regex_data = re.compile(r"^\d{2}/\d{2}/\d{4}$")

        logging.info("Buscando por notificações de migração com possíveis dados invertidos...")
        
        cursor.execute("SELECT id, NPJ, data_notificacao FROM notificacoes WHERE origem = 'migracao'")
        notificacoes_migradas = cursor.fetchall()

        if not notificacoes_migradas:
            logging.info("Nenhuma notificação com origem 'migracao' encontrada para verificar.")
            return

        logging.info(f"Verificando {len(notificacoes_migradas)} registros de migração...")

        for notificacao_id, npj, data_notificacao in tqdm(notificacoes_migradas, desc="Corrigindo migração"):
            # Verifica se o campo NPJ parece uma data E o campo data_notificacao parece um NPJ
            if npj and data_notificacao and regex_data.match(npj) and regex_npj.match(data_notificacao):
                
                novo_npj = data_notificacao
                nova_data = npj

                try:
                    # Tenta corrigir o registro
                    cursor.execute(
                        "UPDATE notificacoes SET NPJ = ?, data_notificacao = ?, status = 'Pendente' WHERE id = ?",
                        (novo_npj, nova_data, notificacao_id)
                    )
                    corrigidos += 1
                except sqlite3.IntegrityError:
                    # Se der erro de duplicidade, é porque o registro correto já existe. Então, apaga o errado.
                    logging.warning(f"\n  - Duplicata encontrada ao tentar corrigir ID {notificacao_id}. NPJ='{novo_npj}', Data='{nova_data}'.")
                    logging.info(f"    - Apagando o registro invertido (ID: {notificacao_id})...")
                    cursor.execute("DELETE FROM notificacoes WHERE id = ?", (notificacao_id,))
                    apagados += 1

        if corrigidos > 0 or apagados > 0:
            conn.commit()
            logging.info(f"\nSUCESSO: {corrigidos} notificações foram corrigidas e {apagados} duplicatas foram removidas.")
        else:
            logging.info("\nNenhuma notificação com dados invertidos foi encontrada.")

    except sqlite3.Error as e:
        logging.error(f"Ocorreu um erro no banco de dados durante a correção: {e}", exc_info=True)
        if conn:
            conn.rollback()
    except Exception as e:
        logging.critical(f"Ocorreu um erro inesperado: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()
            logging.info("Conexão com o banco de dados fechada.")

if __name__ == '__main__':
    corrigir_dados_migrados_invertidos()

