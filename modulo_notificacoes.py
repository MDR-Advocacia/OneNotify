import logging
import re
from playwright.sync_api import Page, TimeoutError
from config import TAREFAS_CONFIG
import database

def extrair_dados_e_dar_ciencia_em_lote(page: Page, tarefa: dict) -> tuple[list[dict], int]:
    """
    Localiza uma tarefa, entra nos detalhes, extrai dados, dá ciência e navega
    pelas páginas de forma robusta, aguardando os carregamentos AJAX.
    """
    notificacoes_para_salvar = []
    npjs_marcados_para_ciencia = set()
    
    try:
        logging.info(f"--- Processando tarefa: {tarefa['nome']} ---")
        
        tabela_principal_selector = 'table[id="tabelaTipoSubtipoGeral"]'
        linha_alvo = page.locator(f"{tabela_principal_selector} tr:has-text(\"{tarefa['nome']}\")")
        
        if linha_alvo.count() == 0:
            logging.warning(f"Tarefa '{tarefa['nome']}' não encontrada. Pulando.")
            return [], 0
        
        contagem_texto = linha_alvo.locator("td").nth(2).inner_text().strip()
        if not contagem_texto.isdigit() or int(contagem_texto.replace('.', '')) == 0:
            logging.info(f"Tarefa '{tarefa['nome']}' sem notificações pendentes. Pulando.")
            return [], 0

        logging.info(f"{contagem_texto} itens encontrados. Abrindo detalhes...")
        linha_alvo.locator('td').last.locator('input[type="button"]').click()

        tabela_detalhes_selector = '[id*=":dataTabletableNotificacoesNaoLidas"]'
        page.wait_for_selector(tabela_detalhes_selector, state='visible', timeout=30000)
        tabela_detalhes = page.locator(tabela_detalhes_selector)
        
        corpo_da_tabela = tabela_detalhes.locator('tbody[id$=":tb"]')
        corpo_da_tabela.locator("tr").first.wait_for(state="visible", timeout=20000)

        pagina_atual = 1
        houve_marcacao = False
        # CORREÇÃO: Usar .first para garantir que sempre pegamos o primeiro modal visível
        modal_carregando = page.locator('#notificacoesNaoLidasForm\\:ajaxLoadingModalBox').first

        while True:
            logging.info(f"    - Verificando página {pagina_atual}...")
            
            for linha in corpo_da_tabela.locator("tr").all():
                try:
                    link_detalhe_locator = linha.locator("td").nth(0).locator("a")
                    npj = link_detalhe_locator.inner_text(timeout=5000).strip()
                    adverso = linha.locator("td").nth(1).inner_text(timeout=5000).strip()
                    data = linha.locator("td").nth(2).inner_text(timeout=5000).strip().split(" ")[0]
                    
                    url_detalhe = link_detalhe_locator.get_attribute('href')
                    id_processo_portal = None
                    if url_detalhe:
                        match = re.search(r'idProcesso=(\d+)', url_detalhe)
                        if match: id_processo_portal = match.group(1)

                    if npj:
                        notificacoes_para_salvar.append({
                            "NPJ": npj, "tipo_notificacao": tarefa["nome"],
                            "adverso_principal": adverso, "data_notificacao": data,
                            "id_processo_portal": id_processo_portal
                        })
                        npjs_marcados_para_ciencia.add(npj)

                        checkbox = linha.locator('input[type="checkbox"][id*=":darCiencia"]')
                        if checkbox.count() > 0 and not checkbox.is_checked():
                            checkbox.check()
                            houve_marcacao = True
                except Exception as e:
                    logging.warning(f"      - Erro ao processar uma linha da tabela: {e}")
            
            paginador = tabela_detalhes.locator("tfoot")
            botao_proxima = paginador.locator('td.rich-datascr-button:not(.dsbld)[onclick*="page\': \'next\'"]')
            if botao_proxima.count() == 0:
                logging.info("    - Fim da paginação.")
                break
            
            logging.info("    - Navegando para a próxima página de detalhes...")
            botao_proxima.click()
            
            try:
                # CORREÇÃO: Aumenta o timeout para o modal aparecer
                modal_carregando.wait_for(state='visible', timeout=10000)
            except TimeoutError:
                logging.warning("    - Modal de carregamento não apareceu na paginação, seguindo em frente.")
            modal_carregando.wait_for(state='hidden', timeout=45000)
            
            pagina_atual += 1

        if houve_marcacao:
            logging.info("    - Confirmando a ciência...")
            page.locator('input[type="image"][src*="btConfirmar.gif"]').click()
        else:
            logging.info("    - Nenhuma ciência marcada. Voltando para a lista de tarefas.")
            page.locator('input[type="image"][src*="btVoltar.gif"]').click()

        try:
            # CORREÇÃO: Aumenta o timeout para o modal de confirmação final
            modal_carregando.wait_for(state='visible', timeout=10000)
        except TimeoutError:
            logging.warning("    - Modal de carregamento final não apareceu, seguindo em frente.")

        modal_carregando.wait_for(state='hidden', timeout=45000)
        
        logging.info(f"Processamento da tarefa '{tarefa['nome']}' concluído.")
        
    except Exception as e:
        logging.error(f"Falha crítica ao processar a tarefa '{tarefa['nome']}': {e}", exc_info=True)

    return notificacoes_para_salvar, len(npjs_marcados_para_ciencia)

def executar_extracao_e_ciencia(page: Page) -> dict:
    """
    Orquestra a navegação inicial e o loop através das tarefas configuradas.
    """
    logging.info("Iniciando módulo de extração e ciência...")
    resultados = {"notificacoes_salvas": 0, "ciencias_registradas": 0}
    
    try:
        logging.info("Navegando para a Central de Notificações...")
        page.goto("https://juridico.bb.com.br/paj/app/paj-central-notificacoes/spas/central-notificacoes/central-notificacoes.app.html")
        page.wait_for_load_state("networkidle", timeout=60000)
        
        logging.info("Acessando a 'Visão do Advogado'...")
        card_processos = page.locator("div.pendencias-card", has_text="Processos - Visao Advogado")
        card_processos.wait_for(state="visible", timeout=45000)
        card_processos.locator("a.mi--forward").click()
        
        tabela_principal_selector = 'table[id="tabelaTipoSubtipoGeral"]'
        page.wait_for_selector(tabela_principal_selector, state='visible', timeout=30000)
        
        for tarefa in TAREFAS_CONFIG:
            notificacoes, ciencias = extrair_dados_e_dar_ciencia_em_lote(page, tarefa)
            if notificacoes:
                salvas = database.salvar_notificacoes(notificacoes)
                resultados["notificacoes_salvas"] += salvas
                resultados["ciencias_registradas"] += ciencias
                logging.info(f"Tarefa '{tarefa['nome']}' finalizada. {salvas} novas notificações salvas. {ciencias} ciências registradas.")

    except Exception as e:
        logging.critical(f"Falha irrecuperável na FASE 2: {e}", exc_info=True)
        raise

    logging.info(f"Extração/ciência concluídas. Salvas: {resultados['notificacoes_salvas']}, Ciências: {resultados['ciencias_registradas']}.")
    return resultados

