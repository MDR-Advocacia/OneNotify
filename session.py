# arquivo: session.py
import time
import logging
import sys
import subprocess
from playwright.sync_api import Page, Browser, BrowserContext, Playwright, Error

from autologin import realizar_login_automatico

class SessionExpiredError(Exception):
    """Exceção para sinalizar que a sessão expirou e precisa ser renovada."""
    pass

SESSION_DURATION = 25 * 60  # 25 minutos

def refresh_session_if_needed(
    playwright: Playwright,
    page: Page,
    browser: Browser,
    context: BrowserContext,
    browser_process_ref: dict,
    session_start_time: float
):
    """Verifica o tempo da sessão e, se necessário, realiza logout e um novo login."""
    if time.time() - session_start_time < SESSION_DURATION:
        return page, browser, context, browser_process_ref, session_start_time

    logging.info("=" * 60)
    logging.info("TEMPO DE SESSÃO PREVENTIVO ATINGIDO (25 MIN). RENOVANDO...")
    logging.info("=" * 60)

    try:
        logging.info("Navegando para a página inicial para logout controlado.")
        page.goto("https://juridico.bb.com.br/paj/juridico", wait_until='domcontentloaded', timeout=30000)
        
        logging.info("Abrindo menu do usuário para encontrar o botão 'Sair'.")
        # CORREÇÃO: Clica no elemento que contém o nome do usuário para abrir o dropdown.
        page.locator("li.nome--chave").click()
        
        # Espera o link 'Sair' ficar visível dentro do dropdown.
        sair_link = page.locator('ul.dropdown--.links--uteis a:has-text("Sair")')
        sair_link.wait_for(state="visible", timeout=10000)
        
        logging.info("Realizando logout.")
        sair_link.click()
        page.wait_for_timeout(5000)

    except Error as e:
        logging.warning(f"Não foi possível fazer logout controlado. Erro: {e}. Prosseguindo para o reinício forçado.")
    finally:
        logging.info("Fechando a instância atual do navegador.")
        if browser and browser.is_connected():
            browser.close()
        
        proc = browser_process_ref.get('process')
        if proc and proc.poll() is None:
            if sys.platform == "win32":
                subprocess.run(f"TASKKILL /F /PID {proc.pid} /T", shell=True, capture_output=True, check=False)
            else:
                proc.kill()

    logging.info("Iniciando uma nova sessão com login automático.")
    new_browser, new_context, new_browser_process_ref, new_page = realizar_login_automatico(playwright)
    new_session_start_time = time.time()

    logging.info("=" * 60)
    logging.info("SESSÃO RENOVADA COM SUCESSO!")
    logging.info("=" * 60)

    return new_page, new_browser, new_context, new_browser_process_ref, new_session_start_time

