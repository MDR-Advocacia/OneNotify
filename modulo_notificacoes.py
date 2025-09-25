# arquivo: modulo_notificacoes.py
import logging
from playwright.sync_api import Page
from config import TAREFAS_CONFIG
import database

def extrair_dados_e_dar_ciencia_em_lote(page: Page, tarefa: dict) -> tuple[list[dict], int]:
    """
    Entra na página de detalhes de uma tarefa, extrai os dados, salva no banco
    e marca a ciência, tudo em uma única passagem.
    """
    notificacoes_para_salvar = []
    npjs_marcados_para_ciencia = set()
    
    try:
        logging.info(f"--- Processando tarefa: {tarefa['nome']} ---")
        
        page.goto("https://juridico.bb.com.br/paj/app/paj-central-notificacoes/spas/central-notificacoes/central-notificacoes.app.html")
        page.wait_for_load_state("networkidle")

        linha_alvo = page.locator(f"tr:has-text(\"{tarefa['nome']}\")")
        if linha_alvo.count() == 0:
            logging.warning(f"Tarefa '{tarefa['nome']}' não encontrada. Pulando.")
            return [], 0
        
        contagem_texto = linha_alvo.locator("td").nth(2).inner_text().strip()
        if not contagem_texto.isdigit() or int(contagem_texto) == 0:
            logging.info(f"Tarefa '{tarefa['nome']}' sem notificações pendentes. Pulando.")
            return [], 0

        logging.info(f"{contagem_texto} itens encontrados. Abrindo detalhes...")
        linha_alvo.get_by_title("Detalhar notificações e pendências do subtipo").click()
        
        page.locator('div.rich-modalpanel-shade').wait_for(state='hidden', timeout=30000)
        page.wait_for_load_state("networkidle")
        
        tabela = page.locator('[id*=":dataTabletableNotificacoesNaoLidas"]')
        corpo_da_tabela = tabela.locator('tbody[id$=":tb"]')
        corpo_da_tabela.locator("tr").first.wait_for(state="visible", timeout=20000)

        pagina_atual = 1
        houve_marcacao = False

        while True:
            logging.info(f"    - Verificando página {pagina_atual}...")
            
            for linha in corpo_da_tabela.locator("tr").all():
                try:
                    npj = linha.locator("td").nth(0).inner_text(timeout=5000).strip()
                    adverso = linha.locator("td").nth(1).inner_text(timeout=5000).strip()
                    data = linha.locator("td").nth(2).inner_text(timeout=5000).strip().split(" ")[0]

                    if npj:
                        notificacoes_para_salvar.append({
                            "NPJ": npj, "tipo_notificacao": tarefa["nome"],
                            "adverso_principal": adverso, "data_notificacao": data
                        })
                        npjs_marcados_para_ciencia.add(npj)

                        checkbox = linha.locator('input[type="checkbox"][id*=":darCiencia"]')
                        if checkbox.count() > 0 and not checkbox.is_checked():
                            checkbox.check()
                            houve_marcacao = True
                except Exception as e:
                    logging.warning(f"      - Erro ao processar uma linha: {e}")
            
            paginador = tabela.locator("tfoot")
            botao_proxima = paginador.locator('td.rich-datascr-button:not(.dsbld)').nth(-2)
            if botao_proxima.count() == 0:
                break
            
            logging.info("    - Navegando para a próxima página...")
            botao_proxima.click()
            page.locator('div.rich-modalpanel-shade').wait_for(state='hidden', timeout=30000)
            pagina_atual += 1

        if houve_marcacao:
            logging.info("    - Confirmando a ciência...")
            page.locator('input[type="image"][src*="btConfirmar.gif"]').click()
            page.wait_for_load_state("networkidle", timeout=45000)
        
        page.go_back()
        page.wait_for_load_state("networkidle")

    except Exception as e:
        logging.error(f"Falha ao processar a tarefa '{tarefa['nome']}': {e}", exc_info=True)

    return notificacoes_para_salvar, len(npjs_marcados_para_ciencia)

def executar_extracao_e_ciencia(page: Page) -> dict:
    """
    Orquestra a extração e o registro de ciência para todas as tarefas configuradas.
    """
    logging.info("Iniciando módulo de extração e ciência...")
    stats = {"notificacoes_salvas": 0, "ciencias_registradas": 0}

    try:
        page.goto("https://juridico.bb.com.br/paj/app/paj-central-notificacoes/spas/central-notificacoes/central-notificacoes.app.html")
        page.wait_for_load_state("networkidle")
        
        card_processos = page.locator("div.pendencias-card", has_text="Processos - Visao Advogado")
        card_processos.wait_for(state="visible", timeout=45000)
        card_processos.locator("a.mi--forward").click()
        page.wait_for_load_state("networkidle")

        for tarefa_config in TAREFAS_CONFIG:
            novas, qtd_ciencias = extrair_dados_e_dar_ciencia_em_lote(page, tarefa_config)
            
            if novas:
                stats["notificacoes_salvas"] += database.salvar_notificacoes(novas)
            stats["ciencias_registradas"] += qtd_ciencias

    except Exception as e:
        logging.critical(f"Falha irrecuperável na extração/ciência: {e}", exc_info=True)
        return stats

    logging.info(f"Extração/ciência concluídas. Salvas: {stats['notificacoes_salvas']}, Ciências: {stats['ciencias_registradas']}.")
    return stats

