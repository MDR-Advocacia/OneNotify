# arquivo: ciencia_notificacoes.py
from playwright.sync_api import Page, TimeoutError
import time

# ALTERAÇÃO: Importa a configuração do novo arquivo central para quebrar a dependência.
from config import TAREFAS_CONFIG

def aguardar_carregamento_ajax(page: Page):
    """Espera o overlay de carregamento 'AJAX' do portal desaparecer."""
    try:
        # Seletor para a máscara de loading que cobre a tela
        loading_overlay_selector = "div.rich-mpnl-mask-div-opaque"
        
        # Espera o overlay aparecer primeiro, mas com um timeout curto.
        # Se não aparecer, ótimo, a ação foi instantânea.
        page.locator(loading_overlay_selector).wait_for(state="visible", timeout=2000)
        
        # Agora, espera o overlay DESAPARECER, com um timeout longo.
        page.locator(loading_overlay_selector).wait_for(state="hidden", timeout=45000)
    except TimeoutError:
        # Se o overlay não apareceu em 2s, é provável que a ação foi rápida.
        # Se ele apareceu mas não desapareceu, a exceção de timeout será lançada.
        # Em ambos os casos, um 'pass' é seguro, pois o robô prosseguirá ou falhará na próxima ação.
        pass

def dar_ciencia_em_lote(page: Page, npjs_sucesso: list[str]):
    """
    Navega pela central de notificações e marca a 'ciência' para uma lista de NPJs
    que foram processados com sucesso, seguindo o fluxo de navegação completo.
    """
    print("\n" + "="*50)
    print("INICIANDO MÓDULO DE CIÊNCIA DE NOTIFICAÇÕES")
    print("="*50)

    if not npjs_sucesso:
        print("[OK] Nenhum NPJ processado com sucesso. Nenhuma ciência a ser registrada.")
        return 0

    URL_CENTRAL_NOTIFICACOES = "https://juridico.bb.com.br/paj/app/paj-central-notificacoes/spas/central-notificacoes/central-notificacoes.app.html"
    npjs_set = set(npjs_sucesso)
    total_ciencias_registradas = 0

    for tarefa in TAREFAS_CONFIG:
        try:
            print(f"\n--- Verificando tarefa para dar ciência: {tarefa['nome']} ---")
            
            print("    - Navegando para a central de notificações...")
            page.goto(URL_CENTRAL_NOTIFICACOES)
            page.wait_for_load_state("networkidle", timeout=60000)
            
            print("    - Localizando o card 'Processos - Visao Advogado'...")
            card_processos = page.locator("div.pendencias-card", has_text="Processos - Visao Advogado")
            card_processos.wait_for(state="visible", timeout=20000)
            
            print("    - Clicando para acessar a lista de tarefas...")
            card_processos.locator("a.mi--forward").click()
            page.wait_for_load_state("networkidle", timeout=30000)

            linha_alvo = page.locator(f"tr:has-text(\"{tarefa['nome']}\")")
            if linha_alvo.count() == 0:
                print(f"    - Tarefa não encontrada na lista. Pulando.")
                continue
            
            celula_contagem = linha_alvo.locator("td").nth(2)
            if celula_contagem.count() == 0:
                 print(f"    - Não foi possível encontrar a contagem para a tarefa. Pulando.")
                 continue

            contagem_texto = celula_contagem.inner_text().strip()
            contagem_numero = int(contagem_texto) if contagem_texto.isdigit() else 0

            if contagem_numero == 0:
                print(f"    - Tarefa sem notificações pendentes. Pulando.")
                continue

            print(f"    - {contagem_numero} itens encontrados. Abrindo detalhes para verificação...")
            linha_alvo.get_by_title("Detalhar notificações e pendências do subtipo").click()
            aguardar_carregamento_ajax(page)

            pagina_atual = 1
            houve_marcacao_nesta_tarefa = False
            
            while True:
                print(f"    - Verificando página {pagina_atual}...")
                try:
                    tabela = page.locator('[id*=":dataTabletableNotificacoesNaoLidas"]')
                    corpo_da_tabela = tabela.locator('tbody[id$=":tb"]')
                    corpo_da_tabela.wait_for(state="visible", timeout=15000)
                except TimeoutError:
                    print("      - Tabela de detalhes não carregou a tempo. Interrompendo esta tarefa.")
                    break

                for linha in corpo_da_tabela.locator("tr").all():
                    npj_encontrado = linha.locator("td").first.inner_text().strip()

                    if npj_encontrado in npjs_set:
                        print(f"      - NPJ {npj_encontrado} encontrado. Marcando ciência...")
                        checkbox = linha.locator('input[type="checkbox"][id*=":darCiencia"]')
                        if checkbox.count() > 0 and not checkbox.is_checked():
                            checkbox.check()
                            total_ciencias_registradas += 1
                            houve_marcacao_nesta_tarefa = True
                            aguardar_carregamento_ajax(page)
                        else:
                            print(f"      - Checkbox para {npj_encontrado} não encontrado ou já marcado.")

                paginador = tabela.locator("tfoot")
                if paginador.count() == 0: break
                
                controles_paginacao = paginador.locator('table.rich-dtascroller-table')
                if controles_paginacao.count() == 0:
                    break

                botao_proxima = controles_paginacao.locator('td.rich-datascr-button').nth(-2)
                
                if botao_proxima.count() == 0:
                    break

                classe_do_botao = botao_proxima.get_attribute("class") or ""
                if "dsbld" in classe_do_botao:
                    break
                
                print("    - Navegando para a próxima página...")
                botao_proxima.click()
                aguardar_carregamento_ajax(page)
                pagina_atual += 1

            if houve_marcacao_nesta_tarefa:
                print(f"    - Confirmando a ciência para a tarefa '{tarefa['nome']}'...")
                confirmar_btn = page.locator('input[type="image"][name*=":j_id193"]')
                if confirmar_btn.count() > 0:
                    confirmar_btn.click()
                    aguardar_carregamento_ajax(page)
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

