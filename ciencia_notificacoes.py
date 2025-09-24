# arquivo: ciencia_notificacoes.py
from playwright.sync_api import Page, TimeoutError
import time
from config import TAREFAS_CONFIG

def registrar_ciencia_para_npjs(page: Page, npjs_para_dar_ciencia: list[str]):
    """
    Navega pela central de notificações e marca a 'ciência' para uma lista de NPJs,
    ideal para registrar ciência logo após a extração.
    """
    print("\n" + "="*50)
    print("INICIANDO MÓDULO DE CIÊNCIA DE NOTIFICAÇÕES")
    print("="*50)

    if not npjs_para_dar_ciencia:
        print("Nenhum NPJ fornecido. Nenhuma ciência a ser registrada.")
        return 0

    URL_JURIDICO_HOME = "https://juridico.bb.com.br/paj/juridico"
    URL_CENTRAL_NOTIFICACOES = "https://juridico.bb.com.br/paj/app/paj-central-notificacoes/spas/central-notificacoes/central-notificacoes.app.html"
    npjs_set = set(npjs_para_dar_ciencia)
    total_ciencias_registradas = 0

    try:
        print("[INFO] Verificando e estabilizando a sessão...")
        page.goto(URL_JURIDICO_HOME)
        page.locator("#aPaginaInicial").wait_for(state="visible", timeout=45000)
        print("[OK] Sessão estabilizada. Navegando para a Central de Notificações...")
        
        page.goto(URL_CENTRAL_NOTIFICACOES)
        page.wait_for_load_state("networkidle", timeout=60000)
        
        print("[INFO] Aguardando o card de 'Processos' ficar visível...")
        card_processos = page.locator("div.pendencias-card", has_text="Processos - Visao Advogado")
        card_processos.wait_for(state="visible", timeout=45000)
        
        card_processos.locator("a.mi--forward").click()
        page.wait_for_load_state("networkidle", timeout=30000)
        url_lista_tarefas = page.url
    except Exception as e:
        print(f"[ERRO] Falha crítica ao navegar para a lista de tarefas: {e}")
        raise # Lança o erro para ser capturado pelo main.py

    for tarefa in TAREFAS_CONFIG:
        if not npjs_set:
            print("[INFO] Todos os NPJs necessários já tiveram ciência registrada. Encerrando o módulo.")
            break
            
        try:
            print(f"\n--- Verificando tarefa para dar ciência: {tarefa['nome']} ---")
            page.goto(url_lista_tarefas)
            page.wait_for_load_state("networkidle", timeout=60000)

            linha_alvo = page.locator(f"tr:has-text(\"{tarefa['nome']}\")")
            if linha_alvo.count() == 0:
                print(f"    - Tarefa não encontrada na lista. Pulando.")
                continue
            
            contagem_texto = linha_alvo.locator("td").nth(2).inner_text().strip()
            contagem_numero = int(contagem_texto) if contagem_texto.isdigit() else 0

            if contagem_numero == 0:
                print(f"    - Tarefa sem notificações pendentes. Pulando.")
                continue

            print(f"    - {contagem_numero} itens encontrados. Abrindo detalhes para verificação...")
            linha_alvo.get_by_title("Detalhar notificações e pendências do subtipo").click()
            
            page.locator('div.rich-modalpanel-shade').wait_for(state='hidden', timeout=30000)

            pagina_atual = 1
            houve_marcacao_nesta_tarefa = False
            
            while True:
                print(f"    - Verificando página {pagina_atual}...")
                try:
                    tabela = page.locator('[id*=":dataTabletableNotificacoesNaoLidas"]')
                    corpo_da_tabela = tabela.locator('tbody[id$=":tb"]')
                    corpo_da_tabela.locator("tr").first.wait_for(state="visible", timeout=15000)
                except TimeoutError:
                    print("      - Tabela de detalhes não carregou ou está vazia. Interrompendo esta tarefa.")
                    break

                num_rows = corpo_da_tabela.locator("tr").count()
                for i in range(num_rows):
                    linha = corpo_da_tabela.locator("tr").nth(i)
                    try:
                        if linha.locator("td").count() == 0:
                            continue
                        
                        npj_encontrado = linha.locator("td").first.inner_text(timeout=5000).strip()

                        if npj_encontrado in npjs_set:
                            print(f"      - NPJ {npj_encontrado} encontrado. Marcando ciência...")
                            checkbox = linha.locator('input[type="checkbox"][id*=":darCiencia"]')
                            if checkbox.count() > 0 and not checkbox.is_checked():
                                checkbox.check()
                                page.locator('div.rich-modalpanel-shade').wait_for(state='hidden', timeout=30000)
                                total_ciencias_registradas += 1
                                houve_marcacao_nesta_tarefa = True
                                npjs_set.remove(npj_encontrado)
                                print(f"      - NPJ {npj_encontrado} removido da lista de pendentes.")
                            else:
                                print(f"      - Checkbox para {npj_encontrado} não encontrado ou já marcado.")
                    except TimeoutError:
                        print(f"      - [AVISO] Timeout ao ler conteúdo da linha {i+1}. Pulando.")
                        continue
                    except Exception as e_row:
                        print(f"      - [ERRO] Erro inesperado ao processar linha {i+1}: {e_row}")
                        continue
                
                if not npjs_set:
                    print("      - Todos os NPJs desta sessão foram encontrados. Interrompendo paginação.")
                    break

                paginador = tabela.locator("tfoot")
                if paginador.count() == 0: break
                
                controles_paginacao = paginador.locator('table.rich-dtascroller-table')
                if controles_paginacao.count() == 0: break
                botao_proxima = controles_paginacao.locator('td.rich-datascr-button').nth(-2)
                if botao_proxima.count() == 0: break
                classe_do_botao = botao_proxima.get_attribute("class") or ""
                if "dsbld" in classe_do_botao: break
                
                print("    - Navegando para a próxima página...")
                botao_proxima.click()
                page.locator('div.rich-modalpanel-shade').wait_for(state='hidden', timeout=30000)
                pagina_atual += 1

            if houve_marcacao_nesta_tarefa:
                print(f"    - Confirmando a ciência para a tarefa '{tarefa['nome']}'...")
                confirmar_btn = page.locator('input[type="image"][src*="btConfirmar.gif"]')
                if confirmar_btn.count() > 0:
                    confirmar_btn.click()
                    page.wait_for_load_state("networkidle", timeout=45000)
                    print("    - [OK] Ação de ciência confirmada.")
                else:
                    print("    - [AVISO] Botão de confirmar não encontrado após marcar os checkboxes.")

        except Exception as e:
            print(f"    - [ERRO] Falha ao processar ciência para a tarefa '{tarefa['nome']}': {e}")
            continue
    
    print("\n" + "="*50)
    print("MÓDULO DE CIÊNCIA DE NOTIFICAÇÕES CONCLUÍDO")
    print(f"Total de ciências registradas: {total_ciencias_registradas}")
    print("="*50)
    return total_ciencias_registradas

