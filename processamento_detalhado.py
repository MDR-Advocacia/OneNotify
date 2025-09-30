# arquivo: processamento_detalhado.py
import logging
import re
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page, BrowserContext, Error, TimeoutError
from datetime import datetime, timedelta
import database
from pathlib import Path

# Importa a exceção customizada que será usada para sinalizar a sessão expirada.
from session import SessionExpiredError

# --- SEU CÓDIGO ORIGINAL (100% INTÁCTO) ---

def extrair_numero_processo(page: Page) -> Optional[str]:
    """Extrai o número do processo da página de detalhes."""
    try:
        selector_processo = 'div.chip[bb-title="Processo"] span.chip__desc'
        page.wait_for_selector(selector_processo, timeout=10000)
        
        if page.locator(selector_processo).count() > 0:
            numero_processo = page.locator(selector_processo).inner_text().strip()
            logging.info(f"      - Número do Processo encontrado: {numero_processo}")
            return numero_processo
        
    except Error as e:
        logging.warning(f"      - Não foi possível extrair o número do processo: {e}")
    return None

def extrair_andamentos(page: Page, data_notificacao_recente: str) -> List[Dict[str, str]]:
    """Clica no menu 'Andamentos', filtra por data e extrai os dados, tratando o modal de publicações e detalhes expansíveis."""
    andamentos = []
    try:
        logging.info("      - Clicando na aba 'Andamentos'...")
        page.locator('li:has-text("Andamentos")').click(timeout=10000)
        
        tabela_container_selector = 'lista-andamentos-processo'
        page.wait_for_selector(tabela_container_selector, state='visible', timeout=15000)

        primeira_linha_selector = 'tr[ng-repeat-start="item in grupoMes.itens"]'
        try:
            logging.info("      - Aguardando carregamento dos andamentos na tabela...")
            page.wait_for_selector(primeira_linha_selector, timeout=10000)
            logging.info("      - Tabela de andamentos carregada.")
        except TimeoutError:
            logging.info("      - Nenhuma linha de andamento encontrada na tabela após espera.")
            return []

        try:
            data_base = datetime.strptime(data_notificacao_recente, '%d/%m/%Y').date()
            datas_permitidas = { data_base - timedelta(days=i) for i in range(3) } # d-0, d-1, d-2
            logging.info(f"      - Filtrando andamentos para as datas: {[d.strftime('%d/%m/%Y') for d in sorted(list(datas_permitidas))]}")
        except (ValueError, TypeError):
            logging.error(f"      - Data de notificação inválida '{data_notificacao_recente}'. Não será possível filtrar andamentos por data.")
            return []

        linhas = page.locator(primeira_linha_selector).all()
        logging.info(f"      - Encontradas {len(linhas)} linhas de andamento para verificação.")

        for linha in linhas:
            try:
                data_andamento_str = linha.locator('td').nth(4).inner_text(timeout=2000).strip()
                data_andamento = datetime.strptime(data_andamento_str, '%d/%m/%Y').date()

                if data_andamento not in datas_permitidas:
                    continue 

                logging.info(f"      - Processando andamento de {data_andamento_str} (data válida).")
                descricao = linha.locator('td').nth(1).inner_text().strip()
                detalhes = descricao # Por padrão, o detalhe é a própria descrição

                if "PUBLICACAO DJ/DO" in descricao.upper():
                    botao_detalhar = linha.locator('a[bb-tooltip="Detalhar publicação"]')
                    
                    if botao_detalhar.count() > 0:
                        logging.info("        - Andamento de publicação encontrado. Abrindo modal de detalhes...")
                        botao_detalhar.click()
                        modal_selector = 'div.modal__data'
                        page.wait_for_selector(modal_selector, state='visible', timeout=10000)
                        
                        leia_mais_btn = page.locator(f'{modal_selector} button:has-text("Leia mais")')
                        if leia_mais_btn.count() > 0:
                            logging.info("        - Botão 'Leia mais' encontrado. Expandindo texto...")
                            leia_mais_btn.click(timeout=5000)
                            page.wait_for_timeout(500)

                        texto_completo_selector = page.locator(f'{modal_selector} texto-grande-detalhar')
                        detalhes = texto_completo_selector.get_attribute('conteudo-texto') or ""
                        
                        page.keyboard.press("Escape")
                        page.wait_for_selector(modal_selector, state='hidden', timeout=5000)
                        logging.info("        - Modal de publicação fechado com sucesso.")
                    else:
                        logging.warning("        - Andamento de publicação sem botão de detalhar. Capturando texto padrão.")
                        detalhes = descricao
                
                andamentos.append({"data": data_andamento_str, "descricao": descricao, "detalhes": detalhes})
            except (Error, IndexError, ValueError) as e:
                logging.warning(f"      - Erro ao processar uma linha de andamento: {e}")
                continue
        logging.info(f"      - {len(andamentos)} andamento(s) capturado(s) dentro do período de datas.")
    except Error as e:
        logging.warning(f"      - Erro inesperado ao extrair andamentos: {e}")
    return andamentos

def baixar_documentos(page: Page, data_notificacao_recente: str, npj: str) -> List[Dict[str, str]]:
    """Expande as seções de documentos, filtra pela data e baixa os arquivos, tratando o erro 'GED indisponível'."""
    documentos_baixados = []
    try:
        logging.info("      - Procurando e expandindo seções de documentos...")
        
        secao_documentos = page.locator('div.accordion__item[bb-item-title="Documentos"]')
        secao_documentos.wait_for(state='attached', timeout=10000)
        
        if secao_documentos.count() == 0:
            logging.info("      - Nenhuma seção de documentos encontrada na página.")
            return []

        titulo_secao = secao_documentos.locator('.accordion__title')
        if titulo_secao.is_visible():
            if 'mi--keyboard-arrow-down' in (titulo_secao.locator('i').get_attribute('class') or ''):
                 titulo_secao.click()
                 page.wait_for_timeout(1000)

        nome_pasta_npj = re.sub(r'[\\/*?:"<>|]', '_', npj)
        diretorio_download_npj = Path(__file__).resolve().parent / "documentos" / nome_pasta_npj
        diretorio_download_npj.mkdir(parents=True, exist_ok=True)
        
        try:
            data_base = datetime.strptime(data_notificacao_recente, '%d/%m/%Y').date()
            datas_permitidas = {data_base - timedelta(days=i) for i in range(3)}
            logging.info(f"      - Filtrando documentos para as datas: {[d.strftime('%d/%m/%Y') for d in sorted(list(datas_permitidas))]}")
        except (ValueError, TypeError):
            logging.error(f"      - Data de notificação inválida '{data_notificacao_recente}'. Não será possível filtrar documentos por data.")
            return []

        tabela_selector = 'table[ng-table="vm.tabelaDocumento"]'
        tabela_documentos = secao_documentos.locator(tabela_selector)
        tabela_documentos.wait_for(state='visible', timeout=15000)
        
        linhas_documentos = tabela_documentos.locator('tbody tr').all()
        logging.info(f"      - Encontrados {len(linhas_documentos)} documentos para verificação.")

        for linha in linhas_documentos:
            try:
                data_doc_str = linha.locator('td').nth(4).inner_text(timeout=2000).strip()
                data_doc = datetime.strptime(data_doc_str, '%d/%m/%Y').date()

                if data_doc not in datas_permitidas:
                    continue

                link_locator = linha.locator('td').nth(1).locator('a')
                if link_locator.count() > 0:
                    nome_arquivo = link_locator.inner_text().strip()
                    logging.info(f"        - Documento encontrado na data permitida '{data_doc_str}': {nome_arquivo}")
                    
                    try:
                        with page.expect_download(timeout=15000) as download_info:
                            link_locator.click()
                        
                        download = download_info.value
                        caminho_salvo = diretorio_download_npj / download.suggested_filename
                        download.save_as(caminho_salvo)
                        
                        documentos_baixados.append({"nome": nome_arquivo, "caminho": str(caminho_salvo)})
                        logging.info(f"        - Download concluído: {caminho_salvo}")

                    except Error:
                        if "GED indisponível" in page.content():
                            logging.error(f"        - ERRO DE PORTAL: GED indisponível para o arquivo '{nome_arquivo}'.")
                            page.go_back(wait_until="networkidle")
                            raise ValueError("GED Indisponível")
                        else:
                            logging.warning(f"        - Timeout ou outra falha no download do arquivo '{nome_arquivo}'.")
            
            except (Error, IndexError, ValueError) as e:
                if "GED Indisponível" in str(e):
                    raise e
                logging.warning(f"      - Erro ao processar uma linha de documento: {e}")
                continue
                
    except Error as e:
        logging.warning(f"      - Ocorreu um erro geral ao processar documentos: {e}")
    
    return documentos_baixados

def navegar_para_detalhes_do_npj(page: Page, npj: str):
    """Navega diretamente para a página de detalhes do NPJ e garante que o conteúdo esteja sincronizado."""
    logging.info(f"    - Construindo URL de detalhe para o NPJ: {npj}")
    
    match = re.match(r"(\d+)/(\d+)-(\d+)", npj)
    if not match:
        raise ValueError(f"Formato de NPJ inválido: {npj}")
    ano, numero, _ = match.groups()
    id_processo_url = f"{ano}{numero.zfill(7)}"
    
    url_final = f"https://juridico.bb.com.br/paj/app/paj-cadastro/spas/processo/consulta/processo-consulta.app.html#/editar/{id_processo_url}/0/1"
    
    logging.info(f"    - Navegando para a URL de detalhe...")
    page.goto(url_final, wait_until="networkidle", timeout=60000)
    
    npj_formatado = f"{ano}/{numero}-000"
    chip_npj_selector = f'div[bb-title="NPJ"] span.chip__desc:has-text("{npj_formatado}")'
    page.wait_for_selector(chip_npj_selector, timeout=30000)
    logging.info("      - Sincronização com a página do NPJ confirmada.")
    
    if page.locator('text=/processo n(ã|a)o localizado/i').count() > 0:
        raise Error(f"Processo {npj} não foi encontrado no portal (página de erro).")

# --- FUNÇÃO PRINCIPAL ---

def processar_detalhes_de_lote(context: BrowserContext, lote: List[Dict[str, Any]]) -> Dict[str, int]:
    """Processa um lote de NPJs, navegando para a URL de cada um e extraindo os detalhes."""
    stats = {"sucesso": 0, "falha": 0, "andamentos": 0, "documentos": 0}
    
    page = context.new_page()

    for i, item in enumerate(lote):
        npj = item.get('NPJ')
        data_notificacao = item.get('data_recente_notificacao')
        
        logging.info(f"\n[{i+1}/{len(lote)}] Processando NPJ: {npj} (Notificação base: {data_notificacao})")
        
        try:
            try:
                navegar_para_detalhes_do_npj(page, npj)
                
                numero_processo = extrair_numero_processo(page)
                documentos = baixar_documentos(page, data_notificacao, npj)
                stats["documentos"] += len(documentos)
                andamentos = extrair_andamentos(page, data_notificacao)
                stats["andamentos"] += len(andamentos)

                database.atualizar_notificacoes_de_npj_processado(npj, numero_processo, andamentos, documentos)
                stats["sucesso"] += 1

            except TimeoutError as e:
                logging.critical(f"    - Timeout detectado ao processar NPJ {npj}. Provável sessão expirada. Acionando recuperação.")
                database.marcar_npj_como_erro(npj) # <<<< CORREÇÃO APLICADA AQUI
                stats["falha"] += 1
                if not page.is_closed():
                    page.close()
                raise SessionExpiredError("Timeout durante a navegação, indicando possível sessão expirada.") from e

            except ValueError as e:
                if "GED Indisponível" in str(e):
                    logging.error(f"  - ERRO DE PORTAL (GED) ao processar NPJ {npj}. Marcando para nova tentativa.")
                    database.marcar_npj_como_erro(npj) # <<<< CORREÇÃO APLICADA AQUI
                    stats["falha"] += 1
            except Error as e:
                logging.error(f"  - ERRO CRÍTICO ao processar NPJ {npj}: {e}", exc_info=False)
                database.marcar_npj_como_erro(npj) # <<<< CORREÇÃO APLICADA AQUI
                stats["falha"] += 1

        except SessionExpiredError:
             raise

        except Exception as e:
            logging.critical(f"Ocorreu um erro não relacionado ao Playwright.\n{e}", exc_info=True)
            database.marcar_npj_como_erro(npj) # <<<< CORREÇÃO APLICADA AQUI
            stats["falha"] += 1
            if not page.is_closed():
                page.close()
            page = context.new_page()
            
    if not page.is_closed():
        page.close()
        
    logging.info("Processamento do lote concluído.")
    return stats

