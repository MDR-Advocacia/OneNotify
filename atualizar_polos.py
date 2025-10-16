import sqlite3
import re
import logging
import time
from tqdm import tqdm
from autologin import realizar_login_automatico
import database
from playwright.sync_api import sync_playwright, Page, Error as PlaywrightError, TimeoutError, Browser
from session import SessionExpiredError # Importa a exceção de sessão

# Configuração básica de log para exibir informações
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def navegar_para_detalhes_do_npj(page: Page, npj: str):
    """Navega diretamente para a página de detalhes do NPJ, construindo a URL."""
    logging.info(f"  - Construindo URL de detalhe para o NPJ: {npj}")
    match = re.match(r"(\d+)/(\d+)-(\d+)", npj)
    if not match:
        raise ValueError(f"Formato de NPJ inválido: {npj}")
    ano, numero, _ = match.groups()
    id_processo_url = f"{ano}{numero.zfill(7)}"
    url_final = f"https://juridico.bb.com.br/paj/app/paj-cadastro/spas/processo/consulta/processo-consulta.app.html#/editar/{id_processo_url}/0/1"
    
    logging.info(f"  - Navegando para a URL de detalhe...")
    try:
        page.goto(url_final, wait_until="networkidle", timeout=60000)
        
        # Garante que a página carregou o NPJ correto antes de prosseguir
        npj_formatado = f"{ano}/{numero}-000"
        chip_npj_selector = f'div[bb-title="NPJ"] span.chip__desc:has-text("{npj_formatado}")'
        page.wait_for_selector(chip_npj_selector, timeout=30000)
        logging.info("    - Sincronização com a página do NPJ confirmada.")
        
        if page.locator('text=/processo n(ã|a)o localizado/i').count() > 0:
            raise PlaywrightError(f"Processo {npj} não foi encontrado no portal (página de erro).")

    except TimeoutError as e:
        # Se ocorrer um timeout na navegação, pode ser que a sessão expirou.
        logging.warning(f"Timeout ao navegar para o NPJ {npj}. Isso pode indicar uma sessão expirada.")
        raise SessionExpiredError("Timeout durante a navegação, possível sessão expirada.") from e


def extrair_polo(page: Page):
    """Extrai o polo (Ativo/Passivo) do cabeçalho da página."""
    try:
        selector_polo = 'div[bb-title="Polo"] span.chip__desc'
        page.wait_for_selector(selector_polo, timeout=10000)
        if page.locator(selector_polo).count() > 0:
            polo = page.locator(selector_polo).inner_text().strip()
            logging.info(f"    - Polo do BB encontrado: {polo}")
            return polo
        logging.warning("    - Não foi possível encontrar o elemento do Polo na página.")
    except (PlaywrightError, TimeoutError):
        logging.warning(f"    - Elemento 'Polo' não encontrado no tempo esperado.")
    return None

def atualizar_polos_existentes():
    """
    Script para percorrer as notificações no banco de dados que não possuem
    a informação de "polo", navegar para a página de detalhes e atualizar o banco,
    com capacidade de renovar a sessão automaticamente.
    """
    conn = None
    browser: Browser | None = None
    
    try:
        database.inicializar_banco()
        conn = sqlite3.connect(database.DATABASE_PATH)
        cursor = conn.cursor()
        logging.info("Conectado ao banco de dados.")

        with sync_playwright() as p:
            ainda_existem_npjs = True
            while ainda_existem_npjs:
                try:
                    cursor.execute("SELECT id, NPJ FROM notificacoes WHERE (polo IS NULL OR polo = '' OR polo = 'N/A' OR polo = 'Erro_Atualizacao') AND NPJ IS NOT NULL AND NPJ != ''")
                    notificacoes_a_processar = cursor.fetchall()

                    if not notificacoes_a_processar:
                        logging.info("Nenhuma notificação com polo pendente encontrada. Tudo em dia!")
                        ainda_existem_npjs = False
                        continue

                    logging.info(f"Encontradas {len(notificacoes_a_processar)} notificações para atualizar o polo.")

                    logging.info("Iniciando o navegador e fazendo login no portal...")
                    browser, context, _, _ = realizar_login_automatico(p)
                    login_time = time.time() # Inicia o timer da sessão
                    
                    if not context:
                        logging.error("Falha crítica no login com Playwright. Abortando a operação.")
                        return
                    
                    page = context.new_page()
                    logging.info("Login realizado com sucesso. Iniciando a atualização dos polos...")

                    for notificacao_id, npj in tqdm(notificacoes_a_processar, desc="Atualizando Polos"):
                        # Verifica o tempo da sessão antes de cada iteração
                        if time.time() - login_time > (25 * 60): # 25 minutos
                            raise SessionExpiredError("Limite de 25 minutos atingido, forçando a renovação da sessão.")

                        try:
                            navegar_para_detalhes_do_npj(page, npj)
                            polo = extrair_polo(page)
                            
                            if polo:
                                cursor.execute("UPDATE notificacoes SET polo = ? WHERE id = ?", (polo, notificacao_id))
                            else:
                                cursor.execute("UPDATE notificacoes SET polo = ? WHERE id = ?", ('N/A', notificacao_id))
                            
                            conn.commit()

                        except SessionExpiredError:
                            raise # Re-lança para ser capturada pelo loop principal e renovar a sessão
                        except (PlaywrightError, ValueError) as e:
                            logging.error(f"Erro de automação ao processar NPJ {npj} (ID: {notificacao_id}): {e}")
                            cursor.execute("UPDATE notificacoes SET polo = ? WHERE id = ?", ('Erro_Atualizacao', notificacao_id))
                            conn.commit()
                        except Exception as e:
                            logging.critical(f"Erro inesperado ao processar o NPJ {npj} (ID: {notificacao_id}): {e}", exc_info=True)
                    
                    ainda_existem_npjs = False 
                    logging.info("\nAtualização de polos concluída!")

                except SessionExpiredError as e:
                    logging.warning(f"Sessão expirada detectada: {e}. Tentando renovar a sessão...")
                    if browser and browser.is_connected():
                        browser.close()
                    
            
    except sqlite3.Error as e:
        logging.error(f"Erro no banco de dados: {e}", exc_info=True)
    except Exception as e:
        logging.critical(f"Ocorreu um erro geral e irrecuperável: {e}", exc_info=True)
    finally:
        if browser and browser.is_connected():
            browser.close()
        if conn:
            logging.info("Fechando a conexão com o banco de dados.")
            conn.close()

if __name__ == '__main__':
    atualizar_polos_existentes()

