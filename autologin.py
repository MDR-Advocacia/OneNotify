import os
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Browser, BrowserContext, Error, Page, Playwright, TimeoutError


BAT_FILE_NAME = "abrir_chrome.sh" if sys.platform != "win32" else "abrir_chrome.bat"
BAT_FILE_PATH = Path(__file__).resolve().parent / BAT_FILE_NAME

CDP_ENDPOINT = os.getenv("CHROME_CDP_ENDPOINT", os.getenv("CDP_ENDPOINT", "http://localhost:9222"))
LEGACY_EXTENSION_URL = os.getenv(
    "ONELOG_LEGACY_EXTENSION_URL",
    os.getenv("ONELOG_EXTENSION_URL", "chrome-extension://lnidijeaekolpfeckelhkomndglcglhh/index.html"),
)
LOGIN_MODE = os.getenv("ONELOG_LOGIN_MODE", "profile").strip().lower()
ONELOG_LOGIN_TIMEOUT_MS = int(os.getenv("ONELOG_LOGIN_TIMEOUT_MS", "360000"))
ONELOG_READY_SELECTOR = os.getenv("ONELOG_READY_SELECTOR", "#aPaginaInicial")
PORTAL_URL_PREFIX = os.getenv("ONELOG_PORTAL_URL_PREFIX", "https://juridico.bb.com.br")
FORCE_LEGACY_PROFILE_FLOW = os.getenv("ONELOG_FORCE_LEGACY_PROFILE_FLOW", "false").lower() == "true"


def _start_browser_process():
    browser_start_command = os.getenv("BROWSER_START_COMMAND")
    if browser_start_command:
        print(f"[>>] Iniciando navegador via BROWSER_START_COMMAND: {browser_start_command}")
        return subprocess.Popen(browser_start_command, shell=True)

    popen_args = {"shell": True}
    if sys.platform == "win32":
        popen_args["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    print(f"[>>] Garantindo que o Chrome esta em execucao via: {BAT_FILE_PATH}")
    return subprocess.Popen(str(BAT_FILE_PATH), **popen_args)


def _connect_browser(playwright: Playwright) -> Browser:
    for attempt in range(25):
        time.sleep(2)
        print(f"    Tentativa de conexao no {attempt + 1}...")
        try:
            browser = playwright.chromium.connect_over_cdp(CDP_ENDPOINT)
            print("[OK] Conectado com sucesso ao navegador!")
            return browser
        except Error:
            if attempt == 24:
                raise ConnectionError(
                    "Falha ao conectar. Verifique se o Chrome esta rodando em modo de depuracao."
                )
    raise ConnectionError("Nao foi possivel conectar ao navegador.")


def _close_context_pages(context: BrowserContext):
    pages = [page for page in context.pages if not page.is_closed()]
    for page in pages[1:]:
        if not page.is_closed():
            page.close()


def _get_work_page(context: BrowserContext) -> Page:
    for page in context.pages:
        if not page.is_closed():
            return page
    return context.new_page()


def _wait_for_onelog_extension_id(context: BrowserContext, timeout_ms: int = 30000) -> str:
    deadline = time.time() + (timeout_ms / 1000)
    while time.time() < deadline:
        for worker in context.service_workers:
            if worker.url.startswith("chrome-extension://") and worker.url.endswith("/background.js"):
                return worker.url.split("/")[2]

        for page in context.pages:
            if page.url.startswith("chrome-extension://"):
                return page.url.split("/")[2]

        extension_id = _get_extension_id_from_cdp_targets()
        if extension_id:
            return extension_id

        time.sleep(0.5)

    raise TimeoutError(
        "Extensao OneLog nao foi carregada no Chrome. "
        "Confirme ONELOG_EXTENSION_DIR e os argumentos --load-extension."
    )


def _get_extension_id_from_cdp_targets() -> str | None:
    extension_ids = _get_extension_ids_from_cdp_targets()
    return extension_ids[0] if extension_ids else None


def _get_extension_ids_from_cdp_targets() -> list[str]:
    parsed = urlparse(CDP_ENDPOINT)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return []

    try:
        with urllib.request.urlopen(f"{parsed.scheme}://{parsed.netloc}/json/list", timeout=2) as response:
            targets = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []

    extension_ids = []
    for target in targets:
        url = target.get("url", "")
        if url.startswith("chrome-extension://"):
            extension_id = url.split("/")[2]
            if extension_id not in extension_ids:
                extension_ids.append(extension_id)
    return extension_ids


def _extension_id_from_url(extension_url: str) -> str | None:
    if not extension_url.startswith("chrome-extension://"):
        return None
    try:
        return extension_url.split("/")[2]
    except IndexError:
        return None


def _find_portal_page(context: BrowserContext) -> Page | None:
    for page in context.pages:
        if not page.is_closed() and page.url.startswith(PORTAL_URL_PREFIX):
            return page
    return None


def _wait_for_portal_page(context: BrowserContext, extension_page: Page, timeout_ms: int) -> Page:
    deadline = time.time() + (timeout_ms / 1000)
    last_error = ""

    while time.time() < deadline:
        portal_page = _find_portal_page(context)
        if portal_page:
            return portal_page

        if not extension_page.is_closed():
            try:
                error_text = extension_page.locator("#error-msg").inner_text(timeout=500).strip()
                if error_text and error_text != last_error:
                    last_error = error_text
                    print(f"[ONELOG] Status de erro na extensao: {last_error}")
            except Exception:
                pass

            try:
                status_text = extension_page.locator("#status-text").inner_text(timeout=500).strip()
                if status_text:
                    print(f"[ONELOG] {status_text}")
            except Exception:
                pass

        time.sleep(2)

    if last_error:
        raise TimeoutError(f"OneLog nao abriu o portal dentro do tempo limite. Ultimo erro: {last_error}")
    raise TimeoutError("OneLog nao abriu o portal dentro do tempo limite.")


def _trigger_onelog_login(context: BrowserContext) -> Page:
    extension_id = _wait_for_onelog_extension_id(context)
    popup_url = f"chrome-extension://{extension_id}/popup.html"
    print(f"[ONELOG] Abrindo popup da extensao: {popup_url}")

    extension_page = _get_work_page(context)
    extension_page.goto(popup_url)
    extension_page.wait_for_load_state("domcontentloaded", timeout=30000)

    username = os.getenv("ONELOG_USERNAME", "").strip()
    password = os.getenv("ONELOG_PASSWORD", "").strip()

    access_button = extension_page.locator("#btn-access")
    login_form_visible = False
    try:
        extension_page.locator("#username").wait_for(state="visible", timeout=5000)
        login_form_visible = True
    except TimeoutError:
        login_form_visible = False

    if username and password and login_form_visible:
        print("[ONELOG] Credenciais informadas via ambiente. Acionando login completo.")
        extension_page.locator("#username").fill(username)
        extension_page.locator("#password").fill(password)
        extension_page.locator("#btn-login").click()
    else:
        try:
            access_button.wait_for(state="visible", timeout=10000)
            print("[ONELOG] Acesso via usuario/sessao ja carregado no OneLog.")
            access_button.click()
        except TimeoutError as exc:
            if username and password:
                raise RuntimeError(
                    "OneLog abriu, mas nem o formulario de login nem o botao de acesso ficaram visiveis."
                ) from exc
            raise RuntimeError(
                "OneLog abriu sem usuario salvo no perfil e sem ONELOG_USERNAME/ONELOG_PASSWORD. "
                "Preencha essas variaveis no .env ou faca o primeiro login manual pelo noVNC."
            ) from exc

    portal_page = _wait_for_portal_page(context, extension_page, ONELOG_LOGIN_TIMEOUT_MS)
    portal_page.wait_for_load_state("domcontentloaded", timeout=60000)

    if ONELOG_READY_SELECTOR:
        print(f"[ONELOG] Aguardando seletor de confirmacao: {ONELOG_READY_SELECTOR}")
        portal_page.locator(ONELOG_READY_SELECTOR).wait_for(state="visible", timeout=90000)

    try:
        portal_page.wait_for_load_state("networkidle", timeout=45000)
    except TimeoutError:
        print("[ONELOG] networkidle nao estabilizou; seguindo com a pagina carregada.")

    if not extension_page.is_closed():
        extension_page.close()

    print("[SUCESSO] Login via OneLog concluido.")
    return portal_page


def _trigger_legacy_extension_login(context: BrowserContext) -> Page:
    print(f"[LEGACY] Abrindo pagina da extensao legada: {LEGACY_EXTENSION_URL}")
    extension_page = _get_work_page(context)
    try:
        extension_page.goto(LEGACY_EXTENSION_URL)
        search_input = extension_page.get_by_placeholder("Digite ou selecione um sistema pra acessar")
        search_input.wait_for(state="visible", timeout=15000)

        search_input.fill("banco do")
        extension_page.locator(
            'div[role="menuitem"]:not([disabled])',
            has_text="Banco do Brasil - Intranet",
        ).first.click()

        print("[LEGACY] Ativando escutador para a pagina do portal...")
        with context.expect_page(timeout=90000) as new_page_info:
            extension_page.get_by_role("button", name="ACESSAR").click()

        portal_page = new_page_info.value
        portal_page.wait_for_load_state("domcontentloaded", timeout=60000)
        portal_page.locator("#aPaginaInicial").wait_for(state="visible", timeout=90000)
        portal_page.wait_for_load_state("networkidle", timeout=45000)

        if not extension_page.is_closed():
            extension_page.close()

        print("[SUCESSO] Login via extensao legada concluido.")
        return portal_page
    except Exception:
        if not extension_page.is_closed():
            extension_page.close()
        raise


def _trigger_profile_login(context: BrowserContext) -> Page:
    legacy_extension_id = _extension_id_from_url(LEGACY_EXTENSION_URL)
    loaded_extension_ids = _get_extension_ids_from_cdp_targets()
    should_try_legacy = FORCE_LEGACY_PROFILE_FLOW or (
        legacy_extension_id and legacy_extension_id in loaded_extension_ids
    )

    if should_try_legacy:
        try:
            print("[PROFILE] Tentando fluxo OneCost: extensao ja instalada no perfil do Chrome.")
            return _trigger_legacy_extension_login(context)
        except Exception as exc:
            print(f"[PROFILE] Fluxo do perfil nao ficou disponivel: {exc}")
    else:
        print(
            "[PROFILE] Extensao legada do OneCost nao detectada no perfil "
            f"(esperada: {legacy_extension_id or '-'}; carregadas: {loaded_extension_ids or '-'})."
        )

    print("[PROFILE] Usando extensao OneLog carregada no container como fallback.")
    return _trigger_onelog_login(context)


def _terminate_browser_process(browser_process_ref: dict):
    proc = browser_process_ref.get("process")
    if proc and proc.poll() is None:
        if sys.platform == "win32":
            subprocess.run(f"TASKKILL /F /PID {proc.pid} /T", shell=True, capture_output=True)
        else:
            proc.kill()


def realizar_login_automatico(playwright: Playwright) -> tuple[Browser, BrowserContext, dict, Page]:
    print("--- MODULO DE LOGIN AUTOMATICO (CDP + ONELOG) ---")

    browser_process = _start_browser_process()
    browser = _connect_browser(playwright)
    context = browser.contexts[0]
    _close_context_pages(context)

    browser_process_ref = {"process": browser_process}

    try:
        if LOGIN_MODE in {"legacy", "old"}:
            portal_page = _trigger_legacy_extension_login(context)
        elif LOGIN_MODE in {"onelog", "popup", "pro"}:
            portal_page = _trigger_onelog_login(context)
        else:
            portal_page = _trigger_profile_login(context)

        return browser, context, browser_process_ref, portal_page

    except Exception as exc:
        print("\n" + "=" * 60)
        print("[ERRO CRITICO] Falha grave durante o processo de login automatizado.")
        print(f"Detalhes do erro: {exc}")
        print("=" * 60 + "\n")
        _terminate_browser_process(browser_process_ref)
        raise
