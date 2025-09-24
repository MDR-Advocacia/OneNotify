# arquivo: autologin.py
import time
import subprocess
import sys
from pathlib import Path

# --- CONFIGURAÇÕES DO MÓDULO ---
BAT_FILE_NAME = "abrir_chrome.sh" if sys.platform != "win32" else "abrir_chrome.bat"
BAT_FILE_PATH = Path(__file__).resolve().parent / BAT_FILE_NAME
CDP_ENDPOINT = "http://localhost:9222"
EXTENSION_URL = "chrome-extension://lnidijeaekolpfeckelhkomndglcglhh/index.html"

def realizar_login_automatico(playwright):
    """
    Executa o script de inicialização do Chrome, conecta-se e realiza o login.
    Funciona tanto em Windows (.bat) quanto em macOS/Linux (.sh).
    """
    print("--- MÓDULO DE LOGIN AUTOMÁTICO ---")
    
    popen_args = {
        "shell": True
    }
    if sys.platform == "win32":
        popen_args['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP

    print(f"[>>] Executando o script: {BAT_FILE_PATH}")
    browser_process = subprocess.Popen(str(BAT_FILE_PATH), **popen_args)
    
    browser = None
    for attempt in range(20): 
        time.sleep(2)
        print(f"    Tentativa de conexão nº {attempt + 1}...")
        try:
            browser = playwright.chromium.connect_over_cdp(CDP_ENDPOINT)
            print("[OK] Conectado com sucesso ao navegador!")
            break 
        except Exception:
            if attempt == 19:
                print("[ERRO] Falha ao conectar. Verifique se o Chrome está rodando em modo de depuração.")
            continue
    
    if not browser:
        raise ConnectionError("Não foi possível conectar ao navegador.")

    context = browser.contexts[0]
    
    print(f"[INFO] Navegando para a URL da extensão...")
    extension_page = context.new_page()
    extension_page.goto(EXTENSION_URL)
    extension_page.wait_for_load_state("domcontentloaded")

    search_input = extension_page.get_by_placeholder("Digite ou selecione um sistema pra acessar")
    search_input.wait_for(state="visible", timeout=10000)
    search_input.fill("banco do")

    login_button = extension_page.locator(
        'div[role="menuitem"]:not([disabled])', 
        has_text="Banco do Brasil - Intranet"
    ).first
    login_button.click(timeout=10000)

    extension_page.get_by_role("button", name="ACESSAR").click(timeout=5000)
    
    print("[OK] Login via extensão confirmado!")
    time.sleep(5)
    extension_page.close()
    
    print("--- FIM DO MÓDULO DE LOGIN ---")
    return browser, context, browser_process

if __name__ == "__main__":
    from playwright.sync_api import sync_playwright
    browser_process = None
    try:
        with sync_playwright() as playwright:
            browser, context, browser_process = realizar_login_automatico(playwright)
            print("\nLogin realizado (teste de módulo). O navegador permanecerá aberto.")
            input("Pressione Enter para fechar...")
    finally:
        if browser_process:
            print("Encerrando o processo do navegador...")
            browser_process.kill() 
            print("Processo encerrado.")

