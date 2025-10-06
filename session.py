import time
import logging
import subprocess
import sys
from playwright.sync_api import Page, Browser, BrowserContext, Playwright
from autologin import realizar_login_automatico

# Definição de uma exceção customizada para ser mais explícita
class SessionExpiredError(Exception):
    """Exceção para quando a sessão do portal expira."""
    pass

# Define o tempo máximo de vida de uma sessão antes de forçar uma renovação
SESSION_TIMEOUT_SECONDS = 30 * 60  # 30 minutos

def refresh_session_if_needed(
    playwright: Playwright,
    page: Page,
    browser: Browser,
    context: BrowserContext,
    browser_process_ref: dict,
    session_start_time: float
) -> tuple[Page, Browser, BrowserContext, dict, float]:
    """
    Verifica se a sessão expirou com base no tempo. Se sim, fecha o navegador
    atual, inicia uma nova instância e realiza o login novamente de forma robusta.
    """
    elapsed_time = time.time() - session_start_time
    if elapsed_time < SESSION_TIMEOUT_SECONDS:
        # Se o tempo não foi atingido, retorna os objetos atuais sem alteração
        return page, browser, context, browser_process_ref, session_start_time

    logging.warning("="*60)
    logging.warning(f"TEMPO DE SESSÃO ATINGIDO ({elapsed_time:.0f}s). INICIANDO RENOVAÇÃO FORÇADA.")
    logging.warning("="*60)

    # --- LÓGICA DE REINÍCIO ROBUSTA ---
    logging.info("Fechando a instância atual do navegador e seus processos...")
    
    # 1. Desconecta o Playwright do navegador
    if browser and browser.is_connected():
        try:
            browser.close()
        except Exception as e:
            logging.warning(f"Erro não crítico ao fechar o browser (pode já estar fechado): {e}")

    # 2. Finaliza o processo do chrome.exe para garantir que não fiquem instâncias órfãs
    proc = browser_process_ref.get('process')
    if proc and proc.poll() is None:
        try:
            if sys.platform == "win32":
                subprocess.run(f"TASKKILL /F /PID {proc.pid} /T", shell=True, capture_output=True, check=False)
            else:
                proc.kill()
            logging.info(f"Processo do navegador (PID: {proc.pid}) finalizado com sucesso.")
        except Exception as e:
            logging.warning(f"Não foi possível finalizar o processo do navegador: {e}")

    # 3. Pausa estratégica para garantir que o sistema operacional libere a porta de depuração
    logging.info("Aguardando 5 segundos para garantir a liberação de recursos do sistema...")
    time.sleep(5)

    # 4. Inicia uma nova sessão completa
    logging.info("Iniciando uma nova sessão com login automático...")
    try:
        new_browser, new_context, new_browser_process_ref, new_page = realizar_login_automatico(playwright)
        new_session_start_time = time.time()
        logging.info("="*60)
        logging.info("RENOVAÇÃO DE SESSÃO CONCLUÍDA COM SUCESSO.")
        logging.info("="*60)
        return new_page, new_browser, new_context, new_browser_process_ref, new_session_start_time
    except Exception as e:
        logging.critical(f"Falha CRÍTICA durante a tentativa de renovar a sessão: {e}", exc_info=True)
        # Se a renovação falhar, a exceção é encapsulada e relançada para que o loop principal
        # possa capturá-la e encerrar a execução, permitindo que o .bat reinicie o processo.
        raise SessionExpiredError(f"Não foi possível renovar a sessão após expirar. Erro original: {e}") from e

