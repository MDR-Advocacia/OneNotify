import logging
import re
import time
from playwright.sync_api import Page, TimeoutError
from config import MARGEM_CHECKPOINT_CIENCIA, PAGINAS_POR_CHECKPOINT_CIENCIA, TAREFAS_CONFIG
import database
from datetime import datetime, timedelta 

def _quantidade_notificacoes(texto: str) -> int:
    somente_digitos = re.sub(r"\D", "", texto or "")
    return int(somente_digitos) if somente_digitos else 0

def _esperar_modal_se_aparecer(
    modal_carregando,
    contexto: str,
    timeout_aparecer: int = 1500,
    timeout_sumir: int = 45000,
    log_ausente: bool = True,
) -> bool:
    try:
        modal_carregando.wait_for(state='visible', timeout=timeout_aparecer)
    except TimeoutError:
        if log_ausente:
            logging.info(f"    - Modal de carregamento não apareceu em {contexto}; seguindo sem espera extra.")
        return False

    modal_carregando.wait_for(state='hidden', timeout=timeout_sumir)
    return True

def _aguardar_modal_sumir_se_visivel(modal_carregando, contexto: str, timeout_sumir: int = 60000) -> bool:
    try:
        if not modal_carregando.is_visible(timeout=150):
            return False
        logging.info("    - Modal visível em %s; aguardando liberação...", contexto)
        modal_carregando.wait_for(state='hidden', timeout=timeout_sumir)
        return True
    except TimeoutError:
        logging.warning("    - Modal não liberou em %s dentro do tempo esperado.", contexto)
        raise

def _aguardar_overlay_ajax_sumir(page: Page, contexto: str, timeout_sumir: int = 300000) -> bool:
    selectors = [
        '#notificacoesNaoLidasForm\\:ajaxLoadingModalBoxDiv',
        '#notificacoesNaoLidasForm\\:ajaxLoadingModalBoxContainer',
        '#notificacoesNaoLidasForm\\:ajaxLoadingModalBox',
    ]
    deadline = time.time() + (timeout_sumir / 1000)
    viu_bloqueio = False

    while time.time() < deadline:
        bloqueado = False
        for selector in selectors:
            loc = page.locator(selector).first
            try:
                if loc.count() > 0 and loc.is_visible(timeout=150):
                    bloqueado = True
                    if not viu_bloqueio:
                        logging.info("    - Overlay AJAX visível em %s; aguardando liberação...", contexto)
                        viu_bloqueio = True
                    restante_ms = max(500, int((deadline - time.time()) * 1000))
                    loc.wait_for(state='hidden', timeout=min(5000, restante_ms))
            except TimeoutError:
                bloqueado = True
            except Exception:
                continue

        if not bloqueado:
            return viu_bloqueio

        time.sleep(0.5)

    raise TimeoutError(f"Overlay AJAX nao liberou em {contexto} dentro do tempo esperado.")

def _ler_paginacao_detalhes(page: Page, tabela_detalhes_selector: str) -> tuple[int | None, int | None]:
    try:
        rodape = page.locator(tabela_detalhes_selector).locator("tfoot").inner_text(timeout=5000)
        match = re.search(r"(\d+)\s*/\s*(\d+)\s*p", rodape, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(2))
    except Exception:
        return None, None
    return None, None

def _ler_total_paginas_detalhes(page: Page, tabela_detalhes_selector: str) -> int | None:
    _, total_paginas = _ler_paginacao_detalhes(page, tabela_detalhes_selector)
    return total_paginas

def _garantir_primeira_pagina_detalhes(
    page: Page,
    tabela_detalhes_selector: str,
    modal_carregando,
    contexto: str,
    timeout_ms: int = 180000,
) -> int | None:
    pagina_atual, total_paginas = _ler_paginacao_detalhes(page, tabela_detalhes_selector)
    if pagina_atual is None:
        logging.warning("    - Não consegui ler a página atual da grade em %s.", contexto)
        return total_paginas

    if pagina_atual <= 1:
        logging.info("    - Grade de detalhes já está na página 1/%s em %s.", total_paginas or "?", contexto)
        return total_paginas

    logging.info(
        "    - Grade de detalhes está na página %s/%s em %s; voltando para a primeira página.",
        pagina_atual,
        total_paginas or "?",
        contexto,
    )
    _aguardar_modal_sumir_se_visivel(modal_carregando, f"antes de voltar para primeira página em {contexto}")
    _aguardar_overlay_ajax_sumir(page, f"antes de voltar para primeira página em {contexto}", timeout_sumir=300000)

    paginador = page.locator(tabela_detalhes_selector).locator("tfoot")
    clicou = paginador.evaluate(
        """
        tfoot => {
            const botoes = Array.from(tfoot.querySelectorAll('td.rich-datascr-button:not(.dsbld)'));
            const primeira = botoes.find(el => (el.getAttribute('onclick') || '').includes("page': 'first'"));
            if (!primeira) return false;
            primeira.click();
            return true;
        }
        """
    )
    if not clicou:
        logging.warning("    - Botão de primeira página não estava disponível em %s.", contexto)
        return total_paginas

    _esperar_modal_se_aparecer(
        modal_carregando,
        f"volta para primeira página em {contexto}",
        timeout_aparecer=1000,
        timeout_sumir=300000,
        log_ausente=False,
    )
    _aguardar_overlay_ajax_sumir(page, f"após voltar para primeira página em {contexto}", timeout_sumir=300000)

    deadline = time.time() + (timeout_ms / 1000)
    while time.time() < deadline:
        pagina_atual, total_paginas = _ler_paginacao_detalhes(page, tabela_detalhes_selector)
        if pagina_atual == 1:
            logging.info("    - Grade de detalhes reposicionada para página 1/%s.", total_paginas or "?")
            return total_paginas
        time.sleep(1)

    raise TimeoutError(f"Grade de detalhes não voltou para a página 1 em {contexto}.")

def _abrir_detalhes_tarefa_pela_seta_superior(
    page: Page,
    tarefa_nome: str,
    tabela_principal_selector: str,
    tabela_detalhes_selector: str,
    modal_carregando,
    contexto: str,
    tentativas: int = 3,
) -> None:
    for tentativa in range(1, tentativas + 1):
        logging.info(
            "    - Abrindo detalhes pela seta superior (%s, tentativa %s/%s)...",
            contexto,
            tentativa,
            tentativas,
        )
        _aguardar_overlay_ajax_sumir(page, f"antes da seta superior em {contexto}", timeout_sumir=300000)
        linha_alvo = page.locator(f"{tabela_principal_selector} tr:has-text(\"{tarefa_nome}\")")
        linha_alvo.locator('td').last.locator('input[type="button"]').click(timeout=60000)
        page.wait_for_selector(tabela_detalhes_selector, state='visible', timeout=120000)
        _esperar_modal_se_aparecer(
            modal_carregando,
            f"abertura pela seta superior em {contexto}",
            timeout_aparecer=1000,
            timeout_sumir=300000,
            log_ausente=False,
        )
        _aguardar_overlay_ajax_sumir(page, f"após seta superior em {contexto}", timeout_sumir=300000)

        pagina_atual, total_paginas = _ler_paginacao_detalhes(page, tabela_detalhes_selector)
        if pagina_atual == 1:
            logging.info(
                "    - Seta superior carregou a grade na página 1/%s.",
                total_paginas or "?",
            )
            return

        logging.warning(
            "    - Seta superior atualizou a consulta, mas preservou a grade na página %s/%s em %s.",
            pagina_atual or "?",
            total_paginas or "?",
            contexto,
        )
        total_reposicionado = _garantir_primeira_pagina_detalhes(
            page,
            tabela_detalhes_selector,
            modal_carregando,
            f"{contexto} após seta superior",
        )
        pagina_reposicionada, total_reposicionado = _ler_paginacao_detalhes(page, tabela_detalhes_selector)
        if pagina_reposicionada == 1:
            logging.info(
                "    - Consulta reaberta e grade reposicionada para página 1/%s.",
                total_reposicionado or "?",
            )
            return
        time.sleep(2)

    raise TimeoutError(
        f"Seta superior nao reposicionou a grade de '{tarefa_nome}' para a pagina 1 em {contexto}."
    )

def _aguardar_consolidacao_ciencia(
    page: Page,
    tarefa_nome: str,
    quantidade_anterior: int,
    total_paginas_anterior: int | None,
    tabela_detalhes_selector: str,
    timeout_ms: int = 300000,
) -> tuple[int, int | None]:
    tabela_principal_selector = 'table[id="tabelaTipoSubtipoGeral"]'
    deadline = time.time() + (timeout_ms / 1000)
    ultima_quantidade = quantidade_anterior
    ultimo_total_paginas = total_paginas_anterior
    ultimo_log = 0.0

    logging.info(
        "    - Aguardando o portal consolidar a ciência de '%s' (%s pendente(s), %s página(s) antes do clique)...",
        tarefa_nome,
        quantidade_anterior,
        total_paginas_anterior or "total desconhecido",
    )

    while time.time() < deadline:
        try:
            page.wait_for_selector(tabela_principal_selector, state='visible', timeout=5000)
            linha_alvo = page.locator(f"{tabela_principal_selector} tr:has-text(\"{tarefa_nome}\")")
            if linha_alvo.count() == 0:
                time.sleep(2)
                continue

            contagem_texto = linha_alvo.locator("td").nth(2).inner_text(timeout=5000).strip()
            ultima_quantidade = _quantidade_notificacoes(contagem_texto)
            if ultima_quantidade < quantidade_anterior:
                logging.info(
                    "    - Contagem do portal atualizada para '%s': %s -> %s.",
                    tarefa_nome,
                    quantidade_anterior,
                    ultima_quantidade,
                )
                return ultima_quantidade, ultimo_total_paginas
        except Exception:
            pass

        total_paginas_atual = _ler_total_paginas_detalhes(page, tabela_detalhes_selector)
        if total_paginas_atual is not None:
            ultimo_total_paginas = total_paginas_atual
            if total_paginas_anterior is not None and total_paginas_atual < total_paginas_anterior:
                logging.info(
                    "    - Total de páginas da grade atualizado para '%s': %s -> %s.",
                    tarefa_nome,
                    total_paginas_anterior,
                    total_paginas_atual,
                )
                return ultima_quantidade, total_paginas_atual

        agora = time.time()
        if agora - ultimo_log >= 15:
            logging.info(
                "    - Portal ainda não consolidou '%s' (contagem %s -> %s; páginas %s -> %s). Aguardando...",
                tarefa_nome,
                quantidade_anterior,
                ultima_quantidade,
                total_paginas_anterior or "desconhecido",
                ultimo_total_paginas or "desconhecido",
            )
            ultimo_log = agora
        time.sleep(2)

    raise TimeoutError(
        f"A tarefa '{tarefa_nome}' nao consolidou a ciência após o clique "
        f"(contagem {quantidade_anterior} -> {ultima_quantidade}; "
        f"páginas {total_paginas_anterior} -> {ultimo_total_paginas})."
    )

def _confirmar_ciencia_com_monitoramento(page: Page) -> None:
    botao_confirmar = page.locator('input[type="image"][src*="btConfirmar.gif"]')

    try:
        with page.expect_response(
            lambda response: (
                response.request.method == "POST"
                and (
                    "notificacoesPendencias" in response.url
                    or "centralNotificacoesPendencias" in response.url
                )
            ),
            timeout=30000,
        ) as resposta_confirmacao:
            botao_confirmar.click(timeout=15000, no_wait_after=True)

        resposta = resposta_confirmacao.value
        logging.info(
            "    - Requisição de confirmação enviada ao BB: HTTP %s (%s).",
            resposta.status,
            resposta.url,
        )
    except TimeoutError:
        logging.warning(
            "    - Não capturei a resposta HTTP da confirmação; seguindo pela validação visual/contagem do portal."
        )

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
) -> tuple[list[dict], int, bool, int, bool]:
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
    bloqueio_ciencia = False
    motivo_interrupcao = ""
    checkpoint_paginas = False
    paginas_no_checkpoint = 0
    
    try:
        logging.info(f"--- Processando tarefa: {tarefa['nome']} ---")
        
        tabela_principal_selector = 'table[id="tabelaTipoSubtipoGeral"]'
        modal_carregando = page.locator('#notificacoesNaoLidasForm\\:ajaxLoadingModalBox').first
        _aguardar_overlay_ajax_sumir(page, "antes de localizar tarefa", timeout_sumir=120000)
        linha_alvo = page.locator(f"{tabela_principal_selector} tr:has-text(\"{tarefa['nome']}\")")
        
        if linha_alvo.count() == 0:
            logging.warning(f"Tarefa '{tarefa['nome']}' não encontrada. Pulando.")
            return [], 0, False, 0, False
        
        contagem_texto = linha_alvo.locator("td").nth(2).inner_text().strip()
        quantidade = _quantidade_notificacoes(contagem_texto)
        if quantidade == 0:
            logging.info(f"Tarefa '{tarefa['nome']}' sem notificações pendentes.")
            return [], 0, False, 0, False

        logging.info(f"{contagem_texto} itens encontrados. Abrindo detalhes...")
        inicio_abertura = time.time()

        tabela_detalhes_selector = '[id*=":dataTabletableNotificacoesNaoLidas"]'
        _abrir_detalhes_tarefa_pela_seta_superior(
            page,
            tarefa["nome"],
            tabela_principal_selector,
            tabela_detalhes_selector,
            modal_carregando,
            "início do lote",
        )

        logging.info("Aguardando o carregamento da tabela de detalhes (isso pode demorar devido ao volume)...")
        page.wait_for_selector(tabela_detalhes_selector, state='visible', timeout=120000)
        _aguardar_overlay_ajax_sumir(page, "após abrir detalhes da tarefa", timeout_sumir=300000)
        logging.info(f"    - Tabela de detalhes carregada em {time.time() - inicio_abertura:.2f}s.")
        tabela_detalhes = page.locator(tabela_detalhes_selector)
        total_paginas_inicial = _ler_total_paginas_detalhes(page, tabela_detalhes_selector)
        if total_paginas_inicial is None and quantidade > 0:
            total_paginas_inicial = (quantidade + 9) // 10
        logging.info("    - Total de páginas da grade no início da tarefa: %s.", total_paginas_inicial or "desconhecido")
        
        corpo_da_tabela = tabela_detalhes.locator('tbody[id$=":tb"]')
        corpo_da_tabela.locator("tr").first.wait_for(state="visible", timeout=20000)

        pagina_atual = 1
        pagina_final_alcancada = False

        if confirmar_ciencia and max_paginas is not None:
            logging.warning(
                "    - Execução limitada a %s página(s): a ciência não será confirmada e nada será salvo neste modo.",
                max_paginas,
            )
            salvar_banco = False

        while True:
            tempo_restante = limite_tempo - (time.time() - start_time_ciclo)
            if tempo_restante <= 0:
                logging.warning("Limite de tempo de extração atingido durante a paginação. O processamento desta tarefa será interrompido.")
                tempo_esgotado = True
                motivo_interrupcao = "tempo_limite"
                break

            if (
                confirmar_ciencia
                and max_paginas is None
                and houve_marcacao
                and tempo_restante <= MARGEM_CHECKPOINT_CIENCIA
            ):
                logging.warning(
                    "Restam %.0fs no ciclo. Fazendo checkpoint de ciência antes da renovação de sessão.",
                    tempo_restante,
                )
                tempo_esgotado = True
                motivo_interrupcao = "checkpoint_pre_renovacao"
                break

            if max_paginas is not None and pagina_atual > max_paginas:
                logging.info(f"    - Limite de {max_paginas} página(s) atingido para execução limitada.")
                break

            inicio_pagina = time.time()
            logging.info(f"    - Verificando página {pagina_atual}...")
            inicio_checkboxes = time.time()
            notificacoes_da_pagina = []
            marcados_na_pagina = 0
            _aguardar_modal_sumir_se_visivel(modal_carregando, "início da página")
            _aguardar_overlay_ajax_sumir(page, "início da página", timeout_sumir=300000)
            
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

                        _aguardar_modal_sumir_se_visivel(modal_carregando, f"antes de marcar NPJ {npj}")
                        _aguardar_overlay_ajax_sumir(page, f"antes de marcar NPJ {npj}", timeout_sumir=300000)
                        if not checkbox.is_checked(timeout=1000):
                            try:
                                checkbox.check(timeout=5000)
                            except TimeoutError:
                                _aguardar_modal_sumir_se_visivel(modal_carregando, f"retry de marcação do NPJ {npj}")
                                _aguardar_overlay_ajax_sumir(page, f"retry de marcação do NPJ {npj}", timeout_sumir=300000)
                                checkbox.check(timeout=8000)
                            _esperar_modal_se_aparecer(
                                modal_carregando,
                                f"marcação do NPJ {npj}",
                                timeout_aparecer=300,
                                timeout_sumir=60000,
                                log_ausente=False,
                            )
                            _aguardar_overlay_ajax_sumir(page, f"após marcar NPJ {npj}", timeout_sumir=300000)

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
                        bloqueio_ciencia = True
                        motivo_interrupcao = "persistencia_incompleta"
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

                paginas_no_checkpoint += 1

            if max_paginas is not None and pagina_atual >= max_paginas:
                logging.info(f"    - Limite de {max_paginas} página(s) atingido para execução limitada.")
                break

            if (
                confirmar_ciencia
                and max_paginas is None
                and PAGINAS_POR_CHECKPOINT_CIENCIA > 0
                and paginas_no_checkpoint >= PAGINAS_POR_CHECKPOINT_CIENCIA
            ):
                logging.warning(
                    "Checkpoint de %s página(s) atingido. Confirmando ciência parcial antes de continuar.",
                    paginas_no_checkpoint,
                )
                checkpoint_paginas = True
                motivo_interrupcao = "checkpoint_por_paginas"
                break

            tempo_restante = limite_tempo - (time.time() - start_time_ciclo)
            if (
                confirmar_ciencia
                and max_paginas is None
                and houve_marcacao
                and tempo_restante <= MARGEM_CHECKPOINT_CIENCIA
            ):
                logging.warning(
                    "Restam %.0fs no ciclo antes da próxima página. Fazendo checkpoint de ciência.",
                    tempo_restante,
                )
                tempo_esgotado = True
                motivo_interrupcao = "checkpoint_pre_paginacao"
                break
            
            paginador = tabela_detalhes.locator("tfoot")
            botao_proxima = paginador.locator('td.rich-datascr-button:not(.dsbld)[onclick*="page\': \'next\'"]')
            if botao_proxima.count() == 0:
                logging.info("    - Fim da paginação.")
                pagina_final_alcancada = True
                break
            
            logging.info("    - Navegando para a próxima página de detalhes...")
            _aguardar_modal_sumir_se_visivel(modal_carregando, "antes da paginação")
            _aguardar_overlay_ajax_sumir(page, "antes da paginação", timeout_sumir=300000)
            botao_proxima.click()
            _esperar_modal_se_aparecer(modal_carregando, "paginação")
            _aguardar_overlay_ajax_sumir(page, "após paginação", timeout_sumir=300000)
            
            pagina_atual += 1

        pode_confirmar_ciencia = False
        ciencia_parcial = False
        confirmar_ciencia_ao_final = confirmar_ciencia and max_paginas is None
        if houve_marcacao and confirmar_ciencia_ao_final:
            if not salvar_banco:
                logging.error("    - Bloqueando ciência: confirmar_ciencia=True exige salvar_banco=True.")
            elif not notificacoes_para_salvar:
                logging.error("    - Bloqueando ciência: checkboxes marcados, mas nenhuma notificação foi extraída.")
            elif bloqueio_ciencia:
                logging.error(
                    "    - Bloqueando ciência: interrupção insegura (%s).",
                    motivo_interrupcao or "motivo_desconhecido",
                )
            elif checkpoint_paginas:
                pode_confirmar_ciencia = True
                ciencia_parcial = True
                logging.warning(
                    "    - Checkpoint por páginas: %s notificação(ões) marcadas foram persistidas e serão confirmadas.",
                    len(notificacoes_para_salvar),
                )
            elif tempo_esgotado:
                pode_confirmar_ciencia = True
                ciencia_parcial = True
                logging.warning(
                    "    - Checkpoint parcial: %s notificação(ões) marcadas foram persistidas e serão confirmadas antes da renovação.",
                    len(notificacoes_para_salvar),
                )
            elif not pagina_final_alcancada:
                logging.error("    - Bloqueando ciência: paginação não chegou ao fim da tarefa.")
            else:
                pode_confirmar_ciencia = True
                logging.info(
                    "    - Todas as %s notificação(ões) marcadas foram persistidas. Confirmando ciência em lote.",
                    len(notificacoes_para_salvar),
                )

        if houve_marcacao and confirmar_ciencia_ao_final and pode_confirmar_ciencia:
            if ciencia_parcial:
                logging.info("    - Confirmando ciência parcial segura...")
            else:
                logging.info("    - Confirmando a ciência...")
            _aguardar_modal_sumir_se_visivel(modal_carregando, "antes de confirmar ciência")
            _aguardar_overlay_ajax_sumir(page, "antes de confirmar ciência", timeout_sumir=300000)
            _confirmar_ciencia_com_monitoramento(page)
            _esperar_modal_se_aparecer(
                modal_carregando,
                "confirmação de ciência",
                timeout_aparecer=5000,
                timeout_sumir=300000,
            )
            _aguardar_overlay_ajax_sumir(page, "após confirmação de ciência", timeout_sumir=300000)
            page.wait_for_selector('table[id="tabelaTipoSubtipoGeral"]', state='visible', timeout=120000)
            _aguardar_consolidacao_ciencia(
                page,
                tarefa["nome"],
                quantidade,
                total_paginas_inicial,
                tabela_detalhes_selector,
            )
            _aguardar_overlay_ajax_sumir(page, "após consolidação de ciência", timeout_sumir=300000)
            ciencia_confirmada = True
        elif houve_marcacao and confirmar_ciencia_ao_final:
            tempo_esgotado = True
            logging.warning("    - Ciência NÃO confirmada. Voltando para a lista de tarefas.")
            _aguardar_modal_sumir_se_visivel(modal_carregando, "antes de voltar sem ciência")
            _aguardar_overlay_ajax_sumir(page, "antes de voltar sem ciência", timeout_sumir=300000)
            page.locator('input[type="image"][src*="btVoltar.gif"]').click()
        elif houve_marcacao:
            logging.info("    - Dry-run: checkboxes marcados apenas para teste. Voltando sem confirmar ciência.")
            _aguardar_modal_sumir_se_visivel(modal_carregando, "antes de voltar no dry-run")
            _aguardar_overlay_ajax_sumir(page, "antes de voltar no dry-run", timeout_sumir=300000)
            page.locator('input[type="image"][src*="btVoltar.gif"]').click()
        else:
            logging.info("    - Nenhuma ciência marcada. Voltando para a lista de tarefas.")
            _aguardar_modal_sumir_se_visivel(modal_carregando, "antes de voltar sem marcações")
            _aguardar_overlay_ajax_sumir(page, "antes de voltar sem marcações", timeout_sumir=300000)
            page.locator('input[type="image"][src*="btVoltar.gif"]').click()

        _esperar_modal_se_aparecer(modal_carregando, "retorno/confirmacao")
        _aguardar_overlay_ajax_sumir(page, "retorno/confirmacao", timeout_sumir=300000)
        if ciencia_confirmada:
            atualizadas = database.marcar_ciencia_enviada(notificacoes_para_salvar)
            logging.info("    - Ciência marcada no banco para %s registro(s).", atualizadas)
        
        logging.info(f"Processamento da tarefa '{tarefa['nome']}' concluído.")
        
    except Exception as e:
        logging.error(f"Falha crítica ao processar a tarefa '{tarefa['nome']}': {e}", exc_info=True)
        tempo_esgotado = True # Sinaliza erro como tempo esgotado para forçar reinício do ciclo

    ciencias = total_marcados_para_ciencia if ciencia_confirmada else 0
    repetir_tarefa = checkpoint_paginas and ciencia_confirmada
    return notificacoes_para_salvar, ciencias, tempo_esgotado, salvas_no_banco, repetir_tarefa

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
        while tarefas_restantes:
            tarefa = tarefas_restantes[0]
            if time.time() - start_time_ciclo > limite_tempo:
                logging.warning("Limite de tempo de extração atingido antes de iniciar nova tarefa. O ciclo será interrompido.")
                tempo_esgotado = True
                break

            notificacoes, ciencias, tempo_esgotado_sub, salvas, repetir_tarefa = extrair_dados_e_dar_ciencia_em_lote(
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

            if tempo_esgotado_sub:
                tempo_esgotado = True
                break

            if repetir_tarefa:
                logging.info(
                    "Checkpoint confirmado para '%s'. Continuando a mesma tarefa na tela atual, sem reiniciar navegação.",
                    tarefa["nome"],
                )
                continue

            tarefas_restantes.pop(0)
        
        return resultados, tempo_esgotado, tarefas_restantes

    except Exception as e:
        logging.critical(f"Falha irrecuperável na FASE 2: {e}", exc_info=True)
        # Em caso de falha grave, sinaliza para reiniciar e retorna as tarefas que não foram processadas
        return resultados, True, tarefas_a_processar
