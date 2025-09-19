# arquivo: processamento_detalhado.py
import traceback
from playwright.sync_api import Page, TimeoutError
from datetime import datetime, timedelta
from pathlib import Path
import database
import re

# --- FUNÇÃO RESTAURADA E MELHORADA ---
# Esta função foi trazida da sua versão antiga, pois contém a lógica
# essencial para abrir o modal e extrair o texto completo da publicação.
def extrair_andamentos_na_janela(page: Page, datas_alvo: set[str]) -> list[dict]:
    """
    Na seção 'Andamentos', varre a tabela, captura qualquer andamento
    dentro da janela de datas e extrai o texto detalhado se for uma publicação.
    """
    andamentos_encontrados = []
    try:
        page.locator("li:has-text('Andamentos')").click()
        page.wait_for_load_state("networkidle", timeout=20000)
        print("    - Seção 'Andamentos' carregada.")

        page.locator('table[bb-expandable-table]').first.wait_for(state="visible", timeout=15000)
        linhas = page.locator('tr[ng-repeat-start="item in grupoMes.itens"]').all()
        print(f"    - Verificando {len(linhas)} andamentos na tela...")

        for linha in linhas:
            try:
                data_encontrada = linha.locator("td").nth(4).inner_text().strip()
                if data_encontrada not in datas_alvo:
                    continue

                tipo_andamento = linha.locator("td").nth(1).inner_text().strip()
                print(f"    - Andamento na data alvo: {data_encontrada} | Tipo: {tipo_andamento}")

                andamento_info = {"data": data_encontrada, "tipo": tipo_andamento, "texto": None}

                # Lógica crucial para extrair texto de publicações
                if "PUBLICACAO DJ/DO" in tipo_andamento.upper():
                    botao_detalhar = linha.locator('a[bb-tooltip="Detalhar publicação"]')
                    if botao_detalhar.count() > 0:
                        print("      - Abrindo modal de publicação...")
                        botao_detalhar.click()
                        
                        modal = page.locator("div.modal__content")
                        modal.wait_for(state="visible", timeout=10000)
                        
                        try:
                            # Tenta expandir o texto clicando em "Leia mais"
                            leia_mais_botao = modal.locator("texto-grande-detalhar").get_by_role("button", name="Leia mais")
                            leia_mais_botao.wait_for(state="visible", timeout=3000)
                            leia_mais_botao.click()
                            modal.get_by_role("button", name="Leia menos").wait_for(state="visible", timeout=5000)
                            print("      - Texto expandido.")
                        except TimeoutError:
                            print("      - Texto já completo ou botão 'Leia mais' não encontrado.")

                        texto_completo = modal.locator("texto-grande-detalhar p[align='justify']").inner_text()
                        andamento_info["texto"] = texto_completo.strip() if texto_completo else "Texto não extraído."
                        print("      - ✅ Texto da publicação capturado.")
                        
                        modal.locator("div.modal__close").click()
                        modal.wait_for(state="hidden", timeout=5000)
                
                andamentos_encontrados.append(andamento_info)
            except Exception as e_linha:
                print(f"      - ⚠️ Erro ao processar uma linha de andamento: {e_linha}")
                continue

    except Exception as e:
        print(f"    - ⚠️ Aviso geral durante a extração de andamentos: {e}")
    
    return andamentos_encontrados

def baixar_documentos_na_janela(page: Page, npj: str, datas_alvo: set[str]) -> list[dict]:
    """
    Na seção 'Dados do Processo', expande a aba 'Documentos', encontra e baixa
    os arquivos que estão dentro da janela de datas alvo.
    """
    documentos_baixados = []
    try:
        print("    - Navegando para 'Dados do Processo' para buscar documentos...")
        page.get_by_text("Dados do Processo", exact=True).click()
        page.wait_for_load_state("networkidle", timeout=20000)

        acordeao_documentos = page.locator('div.accordion__item[bb-item-title="Documentos"]')
        if "is-open" not in (acordeao_documentos.get_attribute("class") or ""):
            acordeao_documentos.locator(".accordion__title").click()
            page.wait_for_load_state("networkidle", timeout=20000)
        
        pasta_base = Path("downloads")
        pasta_npj_sanitizada = re.sub(r'[\\/*?:"<>|]', "_", npj) # Remove caracteres inválidos
        caminho_completo_npj = pasta_base / pasta_npj_sanitizada
        caminho_completo_npj.mkdir(parents=True, exist_ok=True)
        
        tabela_documentos = page.locator('table[ng-table="vm.tabelaDocumento"]')
        tabela_documentos.locator("tbody tr").first.wait_for(state="visible", timeout=15000)
        
        linhas = tabela_documentos.locator("tbody tr").all()
        print(f"    - Verificando {len(linhas)} documentos...")

        for linha in linhas:
            celulas = linha.locator("td").all()
            if len(celulas) < 5: continue
            
            data_documento = celulas[-2].inner_text().strip()

            if data_documento in datas_alvo:
                link_download = linha.locator("a[href*='/download/']")
                if link_download.count() > 0:
                    nome_arquivo = link_download.inner_text().strip()
                    print(f"      - Documento na data alvo: {data_documento} | Arquivo: {nome_arquivo}")

                    try:
                        with page.expect_download(timeout=60000) as download_info:
                            link_download.click()
                        download = download_info.value
                        
                        caminho_salvar = caminho_completo_npj / download.suggested_filename
                        download.save_as(caminho_salvar)
                        
                        documentos_baixados.append({
                            "data": data_documento,
                            "nome_arquivo": download.suggested_filename,
                            "caminho_relativo": str(caminho_salvar.relative_to(pasta_base)).replace("\\", "/")
                        })
                        print(f"      - ✅ Download concluído: {caminho_salvar}")
                    except Exception as e_download:
                        print(f"      - ❌ ERRO ao baixar o arquivo '{nome_arquivo}': {e_download}")

    except Exception as e:
        print(f"    - ⚠️ Aviso durante o processo de download de documentos: {e}")
        
    return documentos_baixados

def extrair_numero_processo(page: Page) -> str:
    """Extrai o número do processo da tela de detalhes."""
    try:
        seletor = "div[bb-title='Processo'] span[ng-if='desc'] span"
        elemento = page.locator(seletor)
        if elemento.count() > 0:
            numero = elemento.inner_text().strip()
            print(f"    - Número do Processo encontrado: {numero}")
            return numero
    except Exception as e:
        print(f"    - ⚠️ Aviso ao extrair número do processo: {e}")
    return ""

def processar_detalhes_pendentes(page: Page):
    """
    Processa notificações pendentes, extraindo detalhes, andamentos e documentos.
    A lógica de modo de teste foi removida para simplificar; agora processa
    qualquer notificação com status 'Pendente'.
    """
    print("\n" + "="*50)
    print("INICIANDO MÓDULO DE PROCESSAMENTO DETALHADO")
    print("="*50)

    stats = {"sucesso": 0, "falha": 0, "andamentos": 0, "documentos": 0}
    notificacoes_para_processar = database.obter_notificacoes_pendentes()

    if not notificacoes_para_processar:
        print("✅ Nenhuma notificação pendente para processar.")
        return stats

    url_base = "https://juridico.bb.com.br/paj/app/paj-cadastro/spas/processo/consulta/processo-consulta.app.html#/editar/"
    
    total_a_processar = len(notificacoes_para_processar)
    print(f"Total de {total_a_processar} notificação(ões) a serem processadas.")

    for i, notificacao in enumerate(notificacoes_para_processar):
        notificacao_id = notificacao['id']
        npj = notificacao['NPJ']
        data_notificacao_str = notificacao['data_notificacao']
        
        print(f"\n[{i+1}/{total_a_processar}] Processando Notificação ID: {notificacao_id} (NPJ: {npj})")
        
        try:
            # Cria a janela de datas (D, D-1, D-2) para a busca
            data_base = datetime.strptime(data_notificacao_str, '%d/%m/%Y')
            datas_alvo = { (data_base - timedelta(days=d)).strftime('%d/%m/%Y') for d in range(3) }
            print(f"    - Janela de datas para busca: {sorted(list(datas_alvo), reverse=True)}")

            # Constrói a URL do NPJ
            ano, resto = npj.split('/')
            numero, variacao_str = resto.split('-')
            url_final = f"{url_base}{ano + numero}/{int(variacao_str)}/1"
            
            page.goto(url_final)
            page.locator("i.ci.ci--barcode").first.wait_for(state="visible", timeout=20000)
            print("    - Página de detalhes do NPJ carregada.")

            # 1. Extrai o número do processo
            numero_processo = extrair_numero_processo(page)

            # 2. Extrai andamentos com a lógica detalhada
            andamentos_coletados = extrair_andamentos_na_janela(page, datas_alvo)
            stats["andamentos"] += len(andamentos_coletados)

            # 3. Extrai documentos
            documentos_coletados = baixar_documentos_na_janela(page, npj, datas_alvo)
            stats["documentos"] += len(documentos_coletados)

            # 4. Atualiza o banco de dados com sucesso
            database.atualizar_registro_processado(
                notificacao_id, 
                numero_processo, 
                andamentos_coletados, 
                documentos_coletados
            )
            stats["sucesso"] += 1

        except Exception as e:
            print(f"    - ❌ ERRO GERAL no processamento da notificação {notificacao_id} (NPJ {npj}): {e}")
            traceback.print_exc()
            stats["falha"] += 1
            database.marcar_como_erro(notificacao_id)
            continue
            
    print("\n" + "="*50)
    print("PROCESSAMENTO DETALHADO CONCLUÍDO")
    print("="*50)
    return stats

