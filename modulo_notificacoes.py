import logging
import re
import time
from playwright.sync_api import Page, TimeoutError
from config import TAREFAS_CONFIG
import database
from datetime import datetime, timedelta 

def extrair_dados_e_dar_ciencia_em_lote(page: Page, tarefa: dict, start_time_ciclo: float, limite_tempo: int) -> tuple[list[dict], int, bool]:
    """
    Localiza uma tarefa, extrai dados página por página, e dá ciência, respeitando um limite de tempo.
    Retorna a lista de notificações, a contagem de ciências e um booleano indicando se o tempo esgotou.
    """
    notificacoes_para_salvar = []
    npjs_marcados_para_ciencia = set()
    houve_marcacao = False
    tempo_esgotado = False
    
    try:
        logging.info(f"--- Processando tarefa: {tarefa['nome']} ---")
        
        tabela_principal_selector = 'table[id="tabelaTipoSubtipoGeral"]'
        linha_alvo = page.locator(f"{tabela_principal_selector} tr:has-text(\"{tarefa['nome']}\")")
        
        if linha_alvo.count() == 0:
            logging.warning(f"Tarefa '{tarefa['nome']}' não encontrada. Pulando.")
            return [], 0, False
        
        contagem_texto = linha_alvo.locator("td").nth(2).inner_text().strip()
        if not contagem_texto.isdigit() or int(contagem_texto.replace('.', '')) == 0:
            logging.info(f"Tarefa '{tarefa['nome']}' sem notificações pendentes.")
            return [], 0, False

        logging.info(f"{contagem_texto} itens encontrados. Abrindo detalhes...")
        linha_alvo.locator('td').last.locator('input[type="button"]').click()

        tabela_detalhes_selector = '[id*=":dataTabletableNotificacoesNaoLidas"]'
        page.wait_for_selector(tabela_detalhes_selector, state='visible', timeout=30000)
        tabela_detalhes = page.locator(tabela_detalhes_selector)
        
        corpo_da_tabela = tabela_detalhes.locator('tbody[id$=":tb"]')
        corpo_da_tabela.locator("tr").first.wait_for(state="visible", timeout=20000)

        pagina_atual = 1
        modal_carregando = page.locator('#notificacoesNaoLidasForm\\:ajaxLoadingModalBox').first

        while True:
            # CHECAGEM DE TEMPO A CADA PÁGINA
            if time.time() - start_time_ciclo > limite_tempo:
                logging.warning(f"Limite de tempo de extração atingido durante a paginação. O processamento desta tarefa será interrompido.")
                tempo_esgotado = True
                break

            logging.info(f"    - Verificando página {pagina_atual}...")
            
            for linha in corpo_da_tabela.locator("tr").all():
                try:
                    link_detalhe_locator = linha.locator("td").nth(0).locator("a")
                    npj = link_detalhe_locator.inner_text(timeout=5000).strip()
                    adverso = linha.locator("td").nth(1).inner_text(timeout=5000).strip()
                    
                    # --- NOVA LÓGICA CONDICIONAL PARA DATA ---
                    data_notificacao = ""
                    if tarefa['nome'] == 'Inclusão de Documentos no NPJ':
                        try:
                            # Pega a coluna "Qtd Dias Gerada" (índice 4, ou 5ª coluna)
                            dias_gerada_str = linha.locator("td").nth(4).inner_text(timeout=5000).strip()
                            dias_gerada = int(dias_gerada_str)
                            # Calcula a data
                            data_calculada = datetime.now().date() - timedelta(days=dias_gerada)
                            data_notificacao = data_calculada.strftime('%d/%m/%Y')
                            logging.info(f"      - Data calculada para '{tarefa['nome']}': {data_notificacao} (baseado em {dias_gerada} dias)")
                        except (ValueError, IndexError) as e:
                            logging.warning(f"      - Não foi possível calcular a data para NPJ {npj}. Usando data de hoje. Erro: {e}")
                            data_notificacao = datetime.now().strftime('%d/%m/%Y')
                    else:
                        # Mantém a lógica original para todas as outras tarefas
                        data_notificacao = linha.locator("td").nth(2).inner_text(timeout=5000).strip().split(" ")[0]
                    
                    url_detalhe = link_detalhe_locator.get_attribute('href')
                    id_processo_portal = None
                    if url_detalhe:
                        match = re.search(r'idProcesso=(\d+)', url_detalhe)
                        if match: id_processo_portal = match.group(1)

                    if npj:
                        notificacoes_para_salvar.append({
                            "NPJ": npj, "tipo_notificacao": tarefa["nome"],
                            "adverso_principal": adverso, "data_notificacao": data_notificacao,
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
            modal_carregando.wait_for(state='visible', timeout=10000)
        except TimeoutError:
            logging.warning("    - Modal de carregamento final não apareceu, seguindo em frente.")

        modal_carregando.wait_for(state='hidden', timeout=45000)
        
        logging.info(f"Processamento da tarefa '{tarefa['nome']}' concluído.")
        
    except Exception as e:
        logging.error(f"Falha crítica ao processar a tarefa '{tarefa['nome']}': {e}", exc_info=True)
        tempo_esgotado = True # Sinaliza erro como tempo esgotado para forçar reinício do ciclo

    return notificacoes_para_salvar, len(npjs_marcados_para_ciencia), tempo_esgotado

def executar_extracao_e_ciencia(page: Page, tarefas_a_processar: list[dict], start_time_ciclo: float, limite_tempo: int) -> tuple[dict, bool, list[dict]]:
    """
    Orquestra a extração e ciência para uma lista de tarefas, respeitando um limite de tempo.
    Retorna os resultados, se o tempo esgotou, e a lista de tarefas restantes.
    """
    resultados = {"notificacoes_salvas": 0, "ciencias_registradas": 0}
    tempo_esgotado = False

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
        
        tarefas_restantes = list(tarefas_a_processar)
        for tarefa in tarefas_a_processar:
            if time.time() - start_time_ciclo > limite_tempo:
                logging.warning("Limite de tempo de extração atingido antes de iniciar nova tarefa. O ciclo será interrompido.")
                tempo_esgotado = True
                break

            notificacoes, ciencias, tempo_esgotado_sub = extrair_dados_e_dar_ciencia_em_lote(page, tarefa, start_time_ciclo, limite_tempo)
            if notificacoes:
                salvas = database.salvar_notificacoes(notificacoes)
                resultados["notificacoes_salvas"] += salvas
                resultados["ciencias_registradas"] += ciencias
                logging.info(f"Tarefa '{tarefa['nome']}' finalizada. {salvas} novas notificações salvas. {ciencias} ciências registradas.")
            
            tarefas_restantes.pop(0)

            if tempo_esgotado_sub:
                tempo_esgotado = True
                break
        
        return resultados, tempo_esgotado, tarefas_restantes

    except Exception as e:
        logging.critical(f"Falha irrecuperável na FASE 2: {e}", exc_info=True)
        # Em caso de falha grave, sinaliza para reiniciar e retorna as tarefas que não foram processadas
        return resultados, True, tarefas_a_processar

