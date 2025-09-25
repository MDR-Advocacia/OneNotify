# arquivo: main.py
import logging
import time
from datetime import datetime
import sys
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright, Error

# Importação dos módulos da RPA
import database
from config import LOG_FORMAT, LOG_LEVEL, TAMANHO_LOTE
from autologin import realizar_login_automatico
from modulo_notificacoes import executar_extracao_e_ciencia
from processamento_detalhado import processar_detalhes_de_lote

# --- CONFIGURAÇÃO DE LOGS ---
LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
timestamp_log = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_filename = LOG_DIR / f"log_{timestamp_log}.txt"

# Configura o logger para registrar tanto no arquivo quanto no console
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# --- FUNÇÃO PRINCIPAL ---
def main():
    """Função principal que orquestra a execução da RPA."""
    stats_extracao = {"notificacoes_salvas": 0, "ciencias_registradas": 0}
    stats_processamento = {"sucesso": 0, "falha": 0, "andamentos": 0, "documentos": 0}
    start_time = time.time()
    
    logging.info("=" * 60)
    logging.info("INICIANDO NOVA EXECUÇÃO DA RPA")
    logging.info("=" * 60)
    
    browser = None
    browser_process_ref = None

    try:
        # FASE 0: PREPARAÇÃO DO BANCO DE DADOS
        database.inicializar_banco()
        database.resetar_notificacoes_em_processamento_ou_erro() # NOME DA FUNÇÃO CORRIGIDO

        with sync_playwright() as playwright:
            # FASE 1: LOGIN E CONFIGURAÇÃO
            logging.info("\nFASE 1: LOGIN E CONFIGURAÇÃO DA SESSÃO")
            browser, context, browser_process_ref, page = realizar_login_automatico(playwright)
            
            # FASE 2: EXTRAÇÃO E CIÊNCIA
            logging.info("\nFASE 2: EXTRAÇÃO DE NOVAS NOTIFICAÇÕES E REGISTRO DE CIÊNCIA")
            stats_extracao = executar_extracao_e_ciencia(page)
            
            # FASE 3: PROCESSAMENTO DETALHADO
            logging.info("\nFASE 3: PROCESSAMENTO DETALHADO EM LOTES")
            total_pendentes = database.contar_pendentes()
            logging.info(f"Total de {total_pendentes} NPJs pendentes para detalhamento.")

            while database.contar_pendentes() > 0:
                lote_para_processar = database.obter_npjs_pendentes_por_lote(TAMANHO_LOTE)
                if not lote_para_processar:
                    logging.info("Não foi possível obter um lote para processamento no momento.")
                    break
                
                logging.info(f"Iniciando processamento detalhado de {len(lote_para_processar)} NPJ(s).")
                stats_lote = processar_detalhes_de_lote(context, lote_para_processar)

                stats_processamento["sucesso"] += stats_lote["sucesso"]
                stats_processamento["falha"] += stats_lote["falha"]
                stats_processamento["andamentos"] += stats_lote["andamentos"]
                stats_processamento["documentos"] += stats_lote["documentos"]
                
                pendentes_restantes = database.contar_pendentes()
                logging.info(f"Lote finalizado. Restam {pendentes_restantes} NPJs pendentes.")

    except Error as e:
        logging.critical(f"Ocorreu uma falha inesperada na automação.\n{e}")
    except Exception as e:
        logging.critical(f"Ocorreu um erro não relacionado ao Playwright.\n{e}", exc_info=True)
    finally:
        end_time = time.time()
        duracao_total = end_time - start_time
        
        logging.info("Finalizando a automação e fechando o navegador.")
        if browser and browser.is_connected():
            browser.close()
        
        if browser_process_ref and browser_process_ref.get('process'):
            proc = browser_process_ref['process']
            if proc.poll() is None:
                if sys.platform == "win32":
                    subprocess.run(f"TASKKILL /F /PID {proc.pid} /T", shell=True, capture_output=True)
                else:
                    proc.kill()
        
        # --- SALVAR RESUMO ---
        total_processado = stats_processamento["sucesso"] + stats_processamento["falha"]
        tempo_medio = (duracao_total / total_processado) if total_processado > 0 else 0
        
        resumo = {
            "timestamp": timestamp_log,
            "duracao_total": duracao_total,
            "tempo_medio_npj": tempo_medio,
            "notificacoes_salvas": stats_extracao["notificacoes_salvas"],
            "ciencias_registradas": stats_extracao["ciencias_registradas"],
            "andamentos": stats_processamento["andamentos"], # Chave corrigida
            "documentos": stats_processamento["documentos"], # Chave corrigida
            "npjs_sucesso": stats_processamento["sucesso"],
            "npjs_falha": stats_processamento["falha"]
        }
        database.salvar_log_execucao(resumo)
        
        logging.info("\n--- RESUMO DA EXECUÇÃO ---")
        for key, value in resumo.items():
            logging.info(f"{key.replace('_', ' ').capitalize()}: {value:.2f}" if isinstance(value, float) else f"{key.replace('_', ' ').capitalize()}: {value}")
        logging.info("=" * 60)

if __name__ == "__main__":
    main()

