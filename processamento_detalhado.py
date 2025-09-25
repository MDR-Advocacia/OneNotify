# arquivo: processamento_detalhado.py
import logging
import re
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page, BrowserContext, Error, TimeoutError
from datetime import datetime, timedelta
import database

# --- FUNÇÕES AUXILIARES DE EXTRAÇÃO (REFEITAS COM BASE NO HTML CORRETO) ---

def extrair_numero_processo(page: Page) -> Optional[str]:
    """Extrai o número do processo da nova página de detalhes."""
    try:
        # Seletor para o "chip" que contém o número do processo (ex: 0020517-64.2004.8.14.0301)
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
    """Clica no menu 'Andamentos', filtra por data e extrai os dados, tratando o modal de publicações."""
    andamentos = []
    try:
        logging.info("      - Clicando na aba 'Andamentos'...")
        page.locator('li:has-text("Andamentos")').click(timeout=10000)
        
        tabela_container_selector = 'lista-andamentos-processo'
        page.wait_for_selector(tabela_container_selector, state='visible', timeout=15000)

        # --- Lógica de Filtro de Data ---
        try:
            data_base = datetime.strptime(data_notificacao_recente, '%d/%m/%Y').date()
            datas_permitidas = { data_base - timedelta(days=i) for i in range(3) } # d-0, d-1, d-2
            logging.info(f"      - Filtrando andamentos para as datas: {[d.strftime('%d/%m/%Y') for d in sorted(list(datas_permitidas))]}")
        except (ValueError, TypeError):
            logging.error(f"      - Data de notificação inválida '{data_notificacao_recente}'. Não será possível filtrar andamentos por data.")
            return []

        linhas = page.locator('tr[ng-repeat-start="item in grupoMes.itens"]').all()
        logging.info(f"      - Encontradas {len(linhas)} linhas de andamento para verificação.")

        for linha in linhas:
            try:
                data_andamento_str = linha.locator('td').nth(4).inner_text(timeout=2000).strip()
                data_andamento = datetime.strptime(data_andamento_str, '%d/%m/%Y').date()

                if data_andamento not in datas_permitidas:
                    continue 

                logging.info(f"      - Processando andamento de {data_andamento_str} (data válida).")
                descricao = linha.locator('td').nth(1).inner_text().strip()
                detalhes = ""

                if "PUBLICACAO DJ/DO" in descricao.upper():
                    botao_detalhar = linha.locator('a[ng-click*="openModalDetalharNovaPublicacao"]')
                    if botao_detalhar.count() > 0:
                        botao_detalhar.click()
                        modal_selector = 'div.modal__data'
                        page.wait_for_selector(modal_selector, state='visible', timeout=10000)
                        
                        leia_mais_btn = page.locator(f'{modal_selector} button:has-text("Leia mais")')
                        if leia_mais_btn.count() > 0:
                            leia_mais_btn.click(timeout=5000)
                            page.wait_for_timeout(500) 

                        texto_completo_selector = page.locator(f'{modal_selector} texto-grande-detalhar p')
                        detalhes = texto_completo_selector.inner_text().strip()
                        
                        # O modal não tem um botão de fechar visível, mas pode responder ao ESC ou a um clique fora
                        page.locator('div.modal__header').click(force=True) # Clica no header para garantir foco
                        page.keyboard.press("Escape")
                        page.wait_for_selector(modal_selector, state='hidden', timeout=5000)
                    else:
                        linha.click()
                        page.wait_for_timeout(500)
                        detalhes = linha.locator('xpath=./following-sibling::tr[1]//span[contains(@class, "ng-binding")]').first.inner_text().strip()
                else:
                    linha.click()
                    page.wait_for_timeout(500)
                    detalhes = linha.locator('xpath=./following-sibling::tr[1]//span[contains(@class, "ng-binding")]').first.inner_text().strip()

                andamentos.append({"data": data_andamento_str, "descricao": descricao, "detalhes": detalhes})
            except (Error, IndexError) as e:
                logging.warning(f"      - Erro ao processar uma linha de andamento: {e}")
                continue
        logging.info(f"      - {len(andamentos)} andamento(s) capturado(s) dentro do período de datas.")
    except Error as e:
        logging.warning(f"      - Erro inesperado ao extrair andamentos: {e}")
    return andamentos

def baixar_documentos(page: Page) -> List[Dict[str, str]]:
    """Expande todas as seções de documentos e tenta baixar os arquivos."""
    documentos_baixados = []
    try:
        logging.info("      - Procurando e expandindo seções de documentos...")
        secoes_documentos = page.locator('div.accordion__title:has-text("Documentos")').all()
        if not secoes_documentos:
            logging.info("      - Nenhuma seção de documentos encontrada na página.")
            return []
            
        for secao in secoes_documentos:
            if secao.is_visible():
                secao.click()
                page.wait_for_timeout(1000)

        logging.info("      - Buscando links para download...")
        links_download = page.locator('a[href*="/paj/rest/processo/v1/processos/documentos"]').all()
        
        if not links_download:
            logging.info("      - Nenhum link de download de documento encontrado.")
            return []

        logging.info(f"      - Encontrados {len(links_download)} link(s) de documento(s).")
        for i in range(len(links_download)):
            link_atual = page.locator('a[href*="/paj/rest/processo/v1/processos/documentos"]').nth(i)
            nome_arquivo = link_atual.locator('xpath=./ancestor::tr/td[1]').inner_text(timeout=5000).strip()
            
            try:
                with page.expect_download(timeout=90000) as download_info:
                    link_atual.click()
                download = download_info.value
                caminho_salvo = f"documentos/{download.suggested_filename}"
                download.save_as(caminho_salvo)
                documentos_baixados.append({"nome": nome_arquivo, "caminho": caminho_salvo})
                logging.info(f"        - Download concluído: {caminho_salvo}")
            except Error as e:
                logging.warning(f"        - Falha no download do arquivo '{nome_arquivo}': {e}")
                
    except Error as e:
        logging.warning(f"      - Ocorreu um erro geral ao processar documentos: {e}")
    return documentos_baixados

# --- FUNÇÃO DE NAVEGAÇÃO DIRETA ---

def navegar_para_detalhes_do_npj(page: Page, npj: str):
    """Navega diretamente para a página de detalhes do NPJ usando a URL correta."""
    logging.info(f"    - Construindo URL de detalhe para o NPJ: {npj}")
    
    match = re.match(r"(\d+)/(\d+)-(\d+)", npj)
    if not match:
        raise ValueError(f"Formato de NPJ inválido: {npj}")
    ano, numero, _ = match.groups()
    id_processo_url = f"{ano}{numero.zfill(7)}"
    url_detalhe = f"https://juridico.bb.com.br/paj/app/paj-cadastro/spas/processo/consulta/processo-consulta.app.html#/editar/{id_processo_url}/0/1"
    
    logging.info(f"    - Navegando para a URL de detalhe...")
    page.goto(url_detalhe, wait_until="networkidle", timeout=60000)
    page.wait_for_selector('comum-resumo-processo', timeout=30000)
    if page.locator('text=/processo n(ã|a)o localizado/i').count() > 0:
        raise Error(f"Processo {npj} não foi encontrado no portal (página de erro).")

# --- FUNÇÃO PRINCIPAL DE PROCESSAMENTO ---

def processar_detalhes_de_lote(context: BrowserContext, lote: List[Dict[str, Any]]) -> Dict[str, int]:
    """Processa um lote de NPJs, navegando para a URL de cada um e extraindo os detalhes."""
    stats = {"sucesso": 0, "falha": 0, "andamentos": 0, "documentos": 0}
    for i, item in enumerate(lote):
        npj = item.get('NPJ')
        data_notificacao = item.get('data_recente_notificacao')
        new_page = None
        
        logging.info(f"\n[{i+1}/{len(lote)}] Processando NPJ: {npj} (Notificação base: {data_notificacao})")
        
        try:
            new_page = context.new_page()
            navegar_para_detalhes_do_npj(new_page, npj)
            numero_processo = extrair_numero_processo(new_page)
            
            # 1. Baixar documentos da tela inicial
            documentos = baixar_documentos(new_page)
            stats["documentos"] += len(documentos)
            # 2. Navegar e extrair andamentos
            andamentos = extrair_andamentos(new_page, data_notificacao)
            stats["andamentos"] += len(andamentos)

            database.atualizar_notificacoes_de_npj_processado(npj, numero_processo, andamentos, documentos)
            stats["sucesso"] += 1

        except Error as e:
            logging.error(f"  - ERRO CRÍTICO ao processar NPJ {npj}: {e}", exc_info=False)
            database.marcar_npj_como_erro(npj)
            stats["falha"] += 1
        finally:
            if new_page and not new_page.is_closed():
                new_page.close()
    logging.info("Processamento do lote concluído.")
    return stats

