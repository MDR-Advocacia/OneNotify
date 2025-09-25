# arquivo: processamento_detalhado.py
import logging
from playwright.sync_api import Page, BrowserContext
from datetime import datetime, timedelta
from pathlib import Path
import re
import database

def extrair_andamentos(page: Page, datas_alvo: set[str]) -> list[dict]:
    """Na seção 'Andamentos', varre a tabela e captura andamentos na janela de datas."""
    andamentos_encontrados = []
    try:
        logging.info("    - Verificando a seção 'Andamentos'...")
        page.locator("li:has-text('Andamentos')").click()
        page.wait_for_load_state("networkidle")

        for linha in page.locator('tr[ng-repeat-start="item in grupoMes.itens"]').all():
            try:
                data = linha.locator("td").nth(4).inner_text().strip()
                if data not in datas_alvo:
                    continue

                tipo = linha.locator("td").nth(1).inner_text().strip()
                andamento = {"data": data, "tipo": tipo, "texto": None}

                if "PUBLICACAO DJ/DO" in tipo.upper():
                    botao_detalhar = linha.locator('a[bb-tooltip="Detalhar publicação"]')
                    if botao_detalhar.count() > 0:
                        botao_detalhar.click()
                        modal = page.locator("div.modal__content")
                        modal.wait_for(state="visible")
                        andamento["texto"] = modal.locator("texto-grande-detalhar p[align='justify']").inner_text().strip()
                        modal.locator("div.modal__close").click()
                        modal.wait_for(state="hidden")
                
                andamentos_encontrados.append(andamento)
            except Exception as e:
                logging.warning(f"        - Erro ao processar uma linha de andamento: {e}")
    except Exception as e:
        logging.error(f"    - Falha ao extrair andamentos: {e}")
    return andamentos_encontrados

def baixar_documentos(page: Page, npj: str, datas_alvo: set[str]) -> list[dict]:
    """Na seção 'Dados do Processo', baixa arquivos na janela de datas."""
    docs_baixados = []
    try:
        logging.info("    - Verificando a seção 'Dados do Processo' para documentos...")
        page.get_by_text("Dados do Processo", exact=True).click()
        page.wait_for_load_state("networkidle")

        acordeao = page.locator('div.accordion__item[bb-item-title="Documentos"]')
        if "is-open" not in (acordeao.get_attribute("class") or ""):
            acordeao.locator(".accordion__title").click()
            page.wait_for_load_state("networkidle")
        
        pasta_base = Path("downloads")
        pasta_npj = pasta_base / re.sub(r'[\\/*?:"<>|]', "_", npj)
        pasta_npj.mkdir(parents=True, exist_ok=True)
        
        for linha in page.locator('table[ng-table="vm.tabelaDocumento"] tbody tr').all():
            data = linha.locator("td").nth(-2).inner_text().strip()
            if data in datas_alvo:
                link = linha.locator("a[href*='/download/']")
                if link.count() > 0:
                    with page.expect_download(timeout=60000) as download_info:
                        link.click()
                    download = download_info.value
                    caminho = pasta_npj / download.suggested_filename
                    download.save_as(caminho)
                    docs_baixados.append({
                        "data": data, "nome_arquivo": download.suggested_filename,
                        "caminho_relativo": str(caminho.relative_to(pasta_base)).replace("\\", "/")
                    })
    except Exception as e:
        logging.error(f"    - Falha ao baixar documentos: {e}")
    return docs_baixados

def extrair_numero_processo(page: Page) -> str:
    try:
        return page.locator("div[bb-title='Processo'] span[ng-if='desc'] span").inner_text().strip()
    except Exception:
        return ""

def processar_detalhes_de_lote(context: BrowserContext, lote: list[dict]) -> dict:
    """Processa um lote de notificações pendentes, abrindo uma nova aba para cada NPJ."""
    stats = {"sucesso": 0, "falha": 0, "andamentos": 0, "documentos": 0}
    if not lote:
        return stats

    url_base = "https://juridico.bb.com.br/paj/app/paj-cadastro/spas/processo/consulta/processo-consulta.app.html#/editar/"
    
    for i, item in enumerate(lote):
        npj = item['NPJ']
        data_notif = item['data_recente_notificacao']
        logging.info(f"\n[{i+1}/{len(lote)}] Processando NPJ: {npj}")
        
        page_processo = None
        try:
            page_processo = context.new_page()
            data_base = datetime.strptime(data_notif, '%d/%m/%Y')
            datas_alvo = { (data_base - timedelta(days=d)).strftime('%d/%m/%Y') for d in range(3) }
            
            ano, resto = npj.split('/')
            numero, variacao = resto.split('-')
            url = f"{url_base}{ano + numero}/{int(variacao)}/1"
            
            page_processo.goto(url)
            page_processo.locator("i.ci.ci--barcode").first.wait_for(state="visible", timeout=45000)
            
            num_proc = extrair_numero_processo(page_processo)
            andamentos = extrair_andamentos(page_processo, datas_alvo)
            documentos = baixar_documentos(page_processo, npj, datas_alvo)
            
            stats["andamentos"] += len(andamentos)
            stats["documentos"] += len(documentos)
            
            database.atualizar_notificacoes_de_npj_processado(npj, num_proc, andamentos, documentos)
            stats["sucesso"] += 1
        except Exception as e:
            logging.error(f"    - ERRO GERAL no NPJ {npj}: {e}", exc_info=True)
            stats["falha"] += 1
            database.marcar_npj_como_erro(npj)
        finally:
            if page_processo and not page_processo.is_closed():
                page_processo.close()
            
    return stats

