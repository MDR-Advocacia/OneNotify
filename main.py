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
    ocorreu_falha_critica = False
    start_time = time.time()
    browser_process_ref = {'process': None} # Referência para o processo do navegador
    browser = None
    context = None

    logging.info("=" * 60)
    logging.info(f"INICIANDO EXECUÇÃO DO ONENOTIFY - {timestamp_log}")
    logging.info("=" * 60)

    try:
        with sync_playwright() as p:
            logging.info("Iniciando Playwright...")
            database.inicializar_banco()
            database.resetar_notificacoes_em_processamento_ou_erro()
            
            # Tenta reutilizar o estado de login, se não conseguir, faz login novo.
            context, page, browser, browser_process_ref = realizar_login_automatico(p)
            
            # --- FASE 1: Extração de Notificações e Registro de Ciência ---
            logging.info("\n--- FASE 1: EXTRAÇÃO E CIÊNCIA DE NOTIFICAÇÕES ---")
            # CORREÇÃO: Passando o 'context' que a função espera
            stats_extracao = executar_extracao_e_ciencia(context)
            
            # --- FASE 2: Processamento Detalhado das Notificações Pendentes ---
            logging.info("\n--- FASE 2: PROCESSAMENTO DETALHADO ---")
            
            while True:
                if database.contar_pendentes() == 0:
                    logging.info("Nenhuma notificação pendente encontrada para processamento. Encerrando a fase 2.")
                    break

                logging.info(f"Tentando processar um novo lote de até {TAMANHO_LOTE} notificações.")
                
                context, browser, browser_process_ref = refresh_session_if_needed(p, context, browser, browser_process_ref)

                lote_stats = processar_detalhes_de_lote(context, tamanho_lote=TAMANHO_LOTE)
                
                stats_processamento["sucesso"] += lote_stats["sucesso"]
                stats_processamento["falha"] += lote_stats["falha"]
                stats_processamento["andamentos"] += lote_stats["andamentos"]
                stats_processamento["documentos"] += lote_stats["documentos"]
                
                logging.info(f"Lote finalizado. Sucessos: {lote_stats['sucesso']}, Falhas: {lote_stats['falha']}. Pausando por 10 segundos...")
                time.sleep(10)

            if page and not page.is_closed():
                page.close()
            if context:
                context.close()
            logging.info("Contexto do Playwright fechado com sucesso.")

    except SessionExpiredError as e:
        logging.error(f"Erro de sessão irrecuperável: {e}. A automação será encerrada.")
        ocorreu_falha_critica = True
    except PlaywrightError as e:
        logging.error(f"Ocorreu um erro específico do Playwright: {e}", exc_info=True)
        ocorreu_falha_critica = True
    except Exception as e:
        logging.critical(f"Ocorreu uma falha geral e inesperada na automação.", exc_info=True)
        ocorreu_falha_critica = True
    finally:
        end_time = time.time()
        duracao_total = end_time - start_time
        
        logging.info("Finalizando a automação e fechando o navegador.")
        
        if context and hasattr(context, 'is_closed') and not context.is_closed():
            context.close()
        if browser and browser.is_connected():
            browser.close()
        
        if browser_process_ref and browser_process_ref.get('process'):
            proc = browser_process_ref['process']
            if proc.poll() is None:
                if sys.platform == "win32":
                    subprocess.run(f"TASKKILL /F /PID {proc.pid} /T", shell=True, capture_output=True, check=False)
                else:
                    proc.kill()
        
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
        
        if ocorreu_falha_critica:
            logging.error("A automação terminou com uma falha crítica.")
        else:
            logging.info("Automação concluída com sucesso.")

if __name__ == '__main__':
    main()

