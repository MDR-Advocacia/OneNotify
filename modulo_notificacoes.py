import logging
import re
import time
from playwright.sync_api import Page, TimeoutError
from config import TAREFAS_CONFIG
import database
from datetime import datetime, timedelta 

def _quantidade_notificacoes(texto: str) -> int:
    somente_digitos = re.sub(r"\D", "", texto or "")
    return int(somente_digitos) if somente_digitos else 0

def _esperar_modal_se_aparecer(modal_carregando, contexto: str, timeout_aparecer: int = 1500, timeout_sumir: int = 45000) -> bool:
    try:
        modal_carregando.wait_for(state='visible', timeout=timeout_aparecer)
    except TimeoutError:
        logging.info(f"    - Modal de carregamento não apareceu em {contexto}; seguindo sem espera extra.")
        return False

    modal_carregando.wait_for(state='hidden', timeout=timeout_sumir)
    return True

def _marcar_checkboxes_visiveis(corpo_da_tabela) -> int:
    checkboxes = corpo_da_tabela.locator('input[type="checkbox"][id*=":darCiencia"]')
    if checkboxes.count() == 0:
        return 0

    return checkboxes.evaluate_all(
        """
        elements => {
            let marcados = 0;
            for (const el of elements) {
                if (!el.checked && !el.disabled) {
                    el.click();
                    marcados += 1;
                }
            }
            return marcados;
        }
        """
    )

def extrair_dados_e_dar_ciencia_em_lote(
    page: Page,
    tarefa: dict,
    start_time_ciclo: float,
    limite_tempo: int,
    confirmar_ciencia: bool = True,
    salvar_banco: bool = True,
    max_paginas: int | None = None,
) -> tuple[list[dict], int, bool, int]:
    """
    Localiza uma tarefa, extrai dados página por página, e dá ciência, respeitando um limite de tempo.
    Retorna a lista de notificações, a contagem de ciências e um booleano indicando se o tempo esgotou.
    """
    notificacoes_para_salvar = []
    npjs_marcados_para_ciencia = set()
    total_marcados_para_ciencia = 0
    houve_marcacao = False
    tempo_esgotado = False
    salvas_no_banco = 0
    ciencia_confirmada = False
    
    try:
        logging.info(f"--- Processando tarefa: {tarefa['nome']} ---")
        
        tabela_principal_selector = 'table[id="tabelaTipoSubtipoGeral"]'
        linha_alvo = page.locator(f"{tabela_principal_selector} tr:has-text(\"{tarefa['nome']}\")")
        
        if linha_alvo.count() == 0:
            logging.warning(f"Tarefa '{tarefa['nome']}' não encontrada. Pulando.")
            return [], 0, False, 0
        
        contagem_texto = linha_alvo.locator("td").nth(2).inner_text().strip()
        quantidade = _quantidade_notificacoes(contagem_texto)
        if quantidade == 0:
            logging.info(f"Tarefa '{tarefa['nome']}' sem notificações pendentes.")
            return [], 0, False, 0

        logging.info(f"{contagem_texto} itens encontrados. Abrindo detalhes...")
        inicio_abertura = time.time()
        linha_alvo.locator('td').last.locator('input[type="button"]').click(timeout=60000)

        tabela_detalhes_selector = '[id*=":dataTabletableNotificacoesNaoLidas"]'

        logging.info("Aguardando o carregamento da tabela de detalhes (isso pode demorar devido ao volume)...")
        page.wait_for_selector(tabela_detalhes_selector, state='visible', timeout=120000)
        logging.info(f"    - Tabela de detalhes carregada em {time.time() - inicio_abertura:.2f}s.")
        tabela_detalhes = page.locator(tabela_detalhes_selector)
        
        corpo_da_tabela = tabela_detalhes.locator('tbody[id$=":tb"]')
        corpo_da_tabela.locator("tr").first.wait_for(state="visible", timeout=20000)

        pagina_atual = 1
        pagina_final_alcancada = False
        modal_carregando = page.locator('#notificacoesNaoLidasForm\\:ajaxLoadingModalBox').first

        if confirmar_ciencia and max_paginas is not None:
            logging.warning(
                "    - Execução limitada a %s página(s): a ciência não será confirmada e nada será salvo neste modo.",
                max_paginas,
            )
            salvar_banco = False

        while True:
            # CHECAGEM DE TEMPO A CADA PÁGINA
            if time.time() - start_time_ciclo > limite_tempo:
                logging.warning(f"Limite de tempo de extração atingido durante a paginação. O processamento desta tarefa será interrompido.")
                tempo_esgotado = True
                break

            if max_paginas is not None and pagina_atual > max_paginas:
                logging.info(f"    - Limite de {max_paginas} página(s) atingido para execução limitada.")
                break

            inicio_pagina = time.time()
            logging.info(f"    - Verificando página {pagina_atual}...")
            inicio_checkboxes = time.time()
            notificacoes_da_pagina = []
            marcados_na_pagina = 0
            
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
                        notificacao = {
                            "NPJ": npj, "tipo_notificacao": tarefa["nome"],
                            "adverso_principal": adverso, "data_notificacao": data_notificacao,
                            "id_processo_portal": id_processo_portal
                        }

                        checkbox = linha.locator('input[type="checkbox"][id*=":darCiencia"]')
                        if checkbox.count() == 0:
                            logging.warning(f"      - NPJ {npj} sem checkbox de ciência; item não será salvo para ciência.")
                            continue

                        if not checkbox.is_checked(timeout=1000):
                            checkbox.check(timeout=5000)

                        if checkbox.is_checked(timeout=1000):
                            notificacoes_da_pagina.append(notificacao)
                            npjs_marcados_para_ciencia.add(npj)
                            marcados_na_pagina += 1
                            total_marcados_para_ciencia += 1
                        else:
                            logging.warning(f"      - Checkbox do NPJ {npj} não ficou marcado; item não será salvo para ciência.")
                except Exception as e:
                    logging.warning(f"      - Erro ao processar uma linha da tabela: {e}")

            if marcados_na_pagina > 0:
                houve_marcacao = True
            logging.info(
                f"    - Página {pagina_atual}: {marcados_na_pagina} checkbox(es) marcado(s) em "
                f"{time.time() - inicio_checkboxes:.2f}s; varredura total em {time.time() - inicio_pagina:.2f}s."
            )

            if notificacoes_da_pagina:
                notificacoes_para_salvar.extend(notificacoes_da_pagina)
                if salvar_banco:
                    logging.info("    - Salvando página %s antes de continuar a paginação...", pagina_atual)
                    inicio_salvamento = time.time()
                    salvas_pagina = database.salvar_notificacoes(notificacoes_da_pagina)
                    faltantes = database.notificacoes_nao_persistidas(notificacoes_da_pagina)
                    if faltantes:
                        logging.error(
                            "    - Bloqueando continuação/ciência: %s notificação(ões) da página %s não foram confirmadas no banco.",
                            len(faltantes),
                            pagina_atual,
                        )
                        tempo_esgotado = True
                        break

                    salvas_no_banco += salvas_pagina
                    logging.info(
                        "    - Página %s persistida e verificada em %.2fs (%s nova(s), %s marcada(s)).",
                        pagina_atual,
                        time.time() - inicio_salvamento,
                        salvas_pagina,
                        len(notificacoes_da_pagina),
                    )

            if max_paginas is not None and pagina_atual >= max_paginas:
                logging.info(f"    - Limite de {max_paginas} página(s) atingido para execução limitada.")
                break
            
            paginador = tabela_detalhes.locator("tfoot")
            botao_proxima = paginador.locator('td.rich-datascr-button:not(.dsbld)[onclick*="page\': \'next\'"]')
            if botao_proxima.count() == 0:
                logging.info("    - Fim da paginação.")
                pagina_final_alcancada = True
                break
            
            logging.info("    - Navegando para a próxima página de detalhes...")
            botao_proxima.click()
            _esperar_modal_se_aparecer(modal_carregando, "paginação")
            
            pagina_atual += 1

        pode_confirmar_ciencia = False
        confirmar_ciencia_ao_final = confirmar_ciencia and max_paginas is None
        if houve_marcacao and confirmar_ciencia_ao_final:
            if not salvar_banco:
                logging.error("    - Bloqueando ciência: confirmar_ciencia=True exige salvar_banco=True.")
            elif not notificacoes_para_salvar:
                logging.error("    - Bloqueando ciência: checkboxes marcados, mas nenhuma notificação foi extraída.")
            elif tempo_esgotado:
                logging.error("    - Bloqueando ciência: a extração foi interrompida antes de concluir a tarefa.")
            elif not pagina_final_alcancada:
                logging.error("    - Bloqueando ciência: paginação não chegou ao fim da tarefa.")
            else:
                pode_confirmar_ciencia = True
                logging.info(
                    "    - Todas as %s notificação(ões) marcadas foram persistidas. Confirmando ciência em lote.",
                    len(notificacoes_para_salvar),
                )

        if houve_marcacao and confirmar_ciencia_ao_final and pode_confirmar_ciencia:
            logging.info("    - Confirmando a ciência...")
            page.locator('input[type="image"][src*="btConfirmar.gif"]').click()
            ciencia_confirmada = True
        elif houve_marcacao and confirmar_ciencia_ao_final:
            tempo_esgotado = True
            logging.warning("    - Ciência NÃO confirmada. Voltando para a lista de tarefas.")
            page.locator('input[type="image"][src*="btVoltar.gif"]').click()
        elif houve_marcacao:
            logging.info("    - Dry-run: checkboxes marcados apenas para teste. Voltando sem confirmar ciência.")
            page.locator('input[type="image"][src*="btVoltar.gif"]').click()
        else:
            logging.info("    - Nenhuma ciência marcada. Voltando para a lista de tarefas.")
            page.locator('input[type="image"][src*="btVoltar.gif"]').click()

        _esperar_modal_se_aparecer(modal_carregando, "retorno/confirmacao")
        if ciencia_confirmada:
            atualizadas = database.marcar_ciencia_enviada(notificacoes_para_salvar)
            logging.info("    - Ciência marcada no banco para %s registro(s).", atualizadas)
        
        logging.info(f"Processamento da tarefa '{tarefa['nome']}' concluído.")
        
    except Exception as e:
        logging.error(f"Falha crítica ao processar a tarefa '{tarefa['nome']}': {e}", exc_info=True)
        tempo_esgotado = True # Sinaliza erro como tempo esgotado para forçar reinício do ciclo

    ciencias = total_marcados_para_ciencia if ciencia_confirmada else 0
    return notificacoes_para_salvar, ciencias, tempo_esgotado, salvas_no_banco

def executar_extracao_e_ciencia(
    page: Page,
    tarefas_a_processar: list[dict],
    start_time_ciclo: float,
    limite_tempo: int,
    confirmar_ciencia: bool = True,
    salvar_banco: bool = True,
    max_paginas_por_tarefa: int | None = None,
) -> tuple[dict, bool, list[dict]]:
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

            notificacoes, ciencias, tempo_esgotado_sub, salvas = extrair_dados_e_dar_ciencia_em_lote(
                page,
                tarefa,
                start_time_ciclo,
                limite_tempo,
                confirmar_ciencia=confirmar_ciencia,
                salvar_banco=salvar_banco,
                max_paginas=max_paginas_por_tarefa,
            )
            if notificacoes:
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
