# arquivo: autologin.py (CORRIGIDO)
import time
import subprocess
import sys # Importa o módulo 'sys' para verificar o sistema operacional
from pathlib import Path

# --- CONFIGURAÇÕES DO MÓDULO ---
# Altera dinamicamente o nome do script a ser executado
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
    
    # Prepara os argumentos para o subprocesso de forma multiplataforma
    popen_args = {
        "shell": True
    }
    if sys.platform == "win32":
        # Adiciona a flag 'creationflags' APENAS se estiver no Windows
        popen_args['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP

    print(f"▶️  Executando o script: {BAT_FILE_PATH}")
    # O operador ** descompacta o dicionário de argumentos
    browser_process = subprocess.Popen(str(BAT_FILE_PATH), **popen_args)
    
    browser = None
    # Aumentei o número de tentativas para dar tempo ao navegador de iniciar
    for attempt in range(20): 
        time.sleep(2)
        print(f"    Tentativa de conexão nº {attempt + 1}...")
        try:
            browser = playwright.chromium.connect_over_cdp(CDP_ENDPOINT)
            print("✅ Conectado com sucesso ao navegador!")
            break 
        except Exception:
            # Se for a última tentativa e falhar, exibe uma mensagem
            if attempt == 19:
                print("❌ Falha ao conectar. Verifique se o Chrome está rodando em modo de depuração.")
            continue
    
    if not browser:
        raise ConnectionError("Não foi possível conectar ao navegador.")

    context = browser.contexts[0]
    
    print(f"🚀 Navegando para a URL da extensão...")
    extension_page = context.new_page()
    extension_page.goto(EXTENSION_URL)
    extension_page.wait_for_load_state("domcontentloaded")

    search_input = extension_page.get_by_placeholder("Digite ou selecione um sistema pra acessar")
    search_input.wait_for(state="visible", timeout=10000) # Aumentado o timeout
    search_input.fill("banco do")

    login_button = extension_page.locator(
        'div[role="menuitem"]:not([disabled])', 
        has_text="Banco do Brasil - Intranet"
    ).first
    login_button.click(timeout=10000)

    extension_page.get_by_role("button", name="ACESSAR").click(timeout=5000)
    
    print("✔️  Login via extensão confirmado!")
    time.sleep(5)
    extension_page.close()
    
    print("--- FIM DO MÓDULO DE LOGIN ---")
    return browser, context, browser_process

# Bloco de teste para execução direta do módulo
if __name__ == "__main__":
    from playwright.sync_api import sync_playwright
    browser_process = None # Inicializa a variável
    try:
        with sync_playwright() as playwright:
            browser, context, browser_process = realizar_login_automatico(playwright)
            print("\nLogin realizado (teste de módulo). O navegador permanecerá aberto.")
            input("Pressione Enter para fechar...")
    finally:
        if browser_process:
            print("Encerrando o processo do navegador...")
            # Método multiplataforma para encerrar o processo
            browser_process.kill() 
            print("Processo encerrado.")