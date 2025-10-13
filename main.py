import logging
import time
from datetime import datetime
import sys
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright, Error as PlaywrightError

import database
from config import LOG_FORMAT, LOG_LEVEL, TAMANHO_LOTE
from autologin import realizar_login_automatico
from modulo_notificacoes import executar_extracao_e_ciencia
from processamento_detalhado import processar_detalhes_de_lote
from session import SessionExpiredError, refresh_session_if_needed

# --- Configuração de Log ---
LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
timestamp_log = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_filename = LOG_DIR / f"log_{timestamp_log}.txt"

logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

def main():
    """Função principal que orquestra a execução da RPA."""
    stats_extracao = {"notificacoes_salvas": 0, "ciencias_registradas": 0}
    stats_processamento = {"sucesso": 0, "falha": 0, "andamentos": 0, "documentos": 0}
    start_time = time.time()
    
    # --- Flag para controlar o status da execução ---
    ocorreu_falha_critica = False
    
    logging.info("=" * 60)
    logging.info("INICIANDO NOVA EXECUÇÃO DA RPA")
    logging.info("=" * 60)
    
    browser = None
    browser_process_ref = None

    try:
        database.inicializar_banco()
        database.resetar_notificacoes_em_processamento_ou_erro()

        with sync_playwright() as playwright:
            try:
                # --- LÓGICA DE RETENTATIVA DE LOGIN ---
                login_success = False
                for attempt in range(3):
                    try:
                        logging.info(f"\nFASE 1: TENTATIVA DE LOGIN E CONFIGURAÇÃO DA SESSÃO ({attempt + 1}/3)")
                        browser, context, browser_process_ref, page = realizar_login_automatico(playwright)
                        session_start_time = time.time()
                        login_success = True
                        logging.info("Login realizado com sucesso!")
                        break 
                    except Exception as login_error:
                        logging.error(f"Falha na tentativa de login {attempt + 1}. Erro: {login_error}")
                        if attempt < 2:
                            logging.info("Aguardando 60 segundos antes de tentar novamente...")
                            time.sleep(60)
                
                if not login_success:
                    logging.critical("Não foi possível realizar o login após 3 tentativas. Abortando execução.")
                    raise ConnectionError("Falha persistente no login.")
                # --- FIM DA LÓGICA DE RETENTATIVA ---

                logging.info("\nFASE 2: EXTRAÇÃO DE NOVAS NOTIFICAÇÕES E REGISTRO DE CIÊNCIA")
                stats_extracao = executar_extracao_e_ciencia(page)
                
                logging.info("\nFASE 3: PROCESSAMENTO DETALHADO EM LOTES")
                
                pendentes_iniciais = database.contar_pendentes()
                logging.info(f"Total de tarefas pendentes para processar: {pendentes_iniciais}")

                while database.contar_pendentes() > 0:
                    try:
                        page, browser, context, browser_process_ref, session_start_time = refresh_session_if_needed(
                            playwright, page, browser, context, browser_process_ref, session_start_time
                        )
                        
                        logging.info("Buscando novo lote de tarefas...")
                        lote_para_processar = database.obter_tarefas_pendentes_por_lote(TAMANHO_LOTE)
                        if not lote_para_processar:
                            logging.warning("Não há mais lotes para processar nesta iteração (pode ser concorrência ou fim da fila).")
                            break
                        
                        logging.info(f"Iniciando processamento detalhado de {len(lote_para_processar)} tarefa(s).")
                        stats_lote = processar_detalhes_de_lote(context, lote_para_processar)

                        stats_processamento["sucesso"] += stats_lote["sucesso"]
                        stats_processamento["falha"] += stats_lote["falha"]
                        stats_processamento["andamentos"] += stats_lote["andamentos"]
                        stats_processamento["documentos"] += stats_lote["documentos"]
                        
                        pendentes_restantes = database.contar_pendentes()
                        logging.info(f"Lote finalizado. Restam {pendentes_restantes} tarefas pendentes.")

                    except SessionExpiredError:
                        logging.warning("Exceção de sessão capturada no loop principal. Forçando renovação imediata.")
                        session_start_time = 0 
                        continue
                
            finally:
                # Este bloco garante que o navegador e os processos sejam fechados
                logging.info("Finalizando a sessão do navegador e processos relacionados.")
                if browser and browser.is_connected():
                    try:
                        browser.close()
                        logging.info("Objeto browser do Playwright fechado com sucesso.")
                    except PlaywrightError as e:
                        logging.warning(f"Erro ao fechar o browser (pode já estar fechado): {e}")

                if browser_process_ref and browser_process_ref.get('process'):
                    proc = browser_process_ref['process']
                    if proc.poll() is None:
                        logging.info(f"Forçando o encerramento do processo do navegador (PID: {proc.pid})...")
                        if sys.platform == "win32":
                            subprocess.run(f"TASKKILL /F /PID {proc.pid} /T", shell=True, capture_output=True, check=False)
                        else:
                            proc.kill()
                        logging.info("Processo do navegador finalizado.")
    
    except (PlaywrightError, ConnectionError) as e:
        logging.critical(f"Ocorreu uma falha crítica na automação que impede a continuação: {e}", exc_info=True)
        ocorreu_falha_critica = True
    except Exception as e:
        logging.critical(f"Ocorreu uma falha geral e inesperada na automação.", exc_info=True)
        ocorreu_falha_critica = True
    finally:
        # Este bloco externo CUIDA APENAS DO RESUMO E LOGS FINAIS
        end_time = time.time()
        duracao_total = end_time - start_time
        
        resumo = {
            "timestamp": timestamp_log, "duracao_total": duracao_total,
            "notificacoes_salvas": stats_extracao["notificacoes_salvas"], "ciencias_registradas": stats_extracao["ciencias_registradas"],
            "andamentos": stats_processamento["andamentos"], "documentos": stats_processamento["documentos"],
            "npjs_sucesso": stats_processamento["sucesso"], "npjs_falha": stats_processamento["falha"]
        }
        database.salvar_log_execucao(resumo)
        
        logging.info("\n--- RESUMO DA EXECUÇÃO ---")
        for key, value in resumo.items():
            logging.info(f"{key.replace('_', ' ').capitalize()}: {value:.2f}" if isinstance(value, float) else f"{key.replace('_', ' ').capitalize()}: {value}")
        logging.info("=" * 60)
        
        # --- Lógica de saída para o .bat ---
        if ocorreu_falha_critica:
            logging.error("Execução finalizada com erro crítico. O supervisor irá reiniciar no modo de falha.")
            sys.exit(1)
        else:
            logging.info("Execução finalizada com sucesso.")
            sys.exit(0)

if __name__ == "__main__":
    main()

