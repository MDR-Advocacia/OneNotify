# arquivo: extracao_notificacoes.py
from playwright.sync_api import Page, TimeoutError
from datetime import datetime, timedelta
import re
import time
from config import TAREFAS_CONFIG

def extrair_dados_com_paginacao(page: Page, id_tabela: str, colunas_desejadas: list[str], limite_registros: int) -> list[dict]:
    """
    Extrai dados de uma tabela com paginação, usando seletores robustos e esperas explícitas
    para garantir a estabilidade.
    """
    dados_extraidos = []
    
    try:
        tabela = page.locator(f'table[id="{id_tabela}"]')
        corpo_da_tabela = tabela.locator(f'tbody[id$=":tb"]')
        corpo_da_tabela.locator("tr").first.wait_for(state="visible", timeout=20000)
        print("    - Tabela de notificações encontrada.")
    except TimeoutError:
        print("    - [AVISO] A tabela de notificações não foi encontrada a tempo. Pulando tarefa.")
        return []
    
    indices_colunas = {}
    headers = tabela.locator("thead th")
    for i in range(headers.count()):
        header_text = headers.nth(i).inner_text().strip()
        if header_text in colunas_desejadas:
            indices_colunas[header_text] = i
    
    print(f"    - Mapeamento de colunas: {indices_colunas}")
    pagina_atual = 1
    
    while True:
        if len(dados_extraidos) >= limite_registros:
            print(f"    - Limite de {limite_registros} registros atingido. Encerrando extração desta tarefa.")
            break
            
        print(f"\n    --- Extraindo dados da página {pagina_atual} ---")
        corpo_da_tabela.wait_for(state="visible")
        
        for linha in corpo_da_tabela.locator("tr").all():
            if len(dados_extraidos) >= limite_registros:
                break
            
            item = {}
            for nome_coluna, indice in indices_colunas.items():
                try:
                    item[nome_coluna] = linha.locator("td").nth(indice).inner_text().strip()
                except Exception:
                    item[nome_coluna] = "" 
            dados_extraidos.append(item)
        
        print(f"    - {len(dados_extraidos)} de {limite_registros} registros extraídos até agora.")

        paginador_locator = f'table[id="{id_tabela}"] > tfoot'
        try:
            page.locator(paginador_locator).wait_for(state="visible", timeout=5000)
        except TimeoutError:
            print("    - Paginador (tfoot) não encontrado. Assumindo página única.")
            break

        controles_paginacao = page.locator(f'{paginador_locator} table.rich-dtascroller-table')
        if controles_paginacao.count() == 0:
            print("    - Controles de paginação (rich-dtascroller-table) não encontrados. Fim da extração.")
            break

        botao_proxima = controles_paginacao.locator('td.rich-datascr-button').nth(-2)
        if botao_proxima.count() == 0:
            print("    - Botão 'Próxima Página' não pôde ser localizado por posição. Fim da paginação.")
            break

        classe_do_botao = botao_proxima.get_attribute("class") or ""
        if "dsbld" in classe_do_botao:
            print("    - Não há mais páginas para extrair (botão desabilitado).")
            break
            
        print("\n    - Clicando em 'Próxima Página'...")
        botao_proxima.click()
        page.wait_for_load_state("networkidle", timeout=30000)
        pagina_atual += 1

    return dados_extraidos

def extrair_e_obter_npjs(page: Page) -> tuple[list[dict], list[str]]:
    """
    Navega pela central, extrai os dados básicos e retorna uma tupla com:
    1. A lista de dicionários de notificações para salvar no DB.
    2. A lista de strings de NPJs únicos para dar ciência.
    """
    print("\n" + "="*50)
    print("INICIANDO MÓDULO DE EXTRAÇÃO DE NOTIFICAÇÕES")
    print("="*50)
    
    URL_JURIDICO_HOME = "https://juridico.bb.com.br/paj/juridico"
    URL_CENTRAL_NOTIFICACOES = "https://juridico.bb.com.br/paj/app/paj-central-notificacoes/spas/central-notificacoes/central-notificacoes.app.html"
    notificacoes_coletadas = []
    npjs_unicos = set()

    try:
        print("[INFO] Verificando e estabilizando a sessão...")
        page.goto(URL_JURIDICO_HOME)
        page.locator("#aPaginaInicial").wait_for(state="visible", timeout=45000)
        print("[OK] Sessão estabilizada. Navegando para a Central de Notificações...")

        page.goto(URL_CENTRAL_NOTIFICACOES)
        page.wait_for_load_state("networkidle", timeout=60000)
        print("[OK] Central de Notificações carregada.")
        
        print("[INFO] Aguardando o card de 'Processos' ficar visível...")
        card_processos = page.locator("div.pendencias-card", has_text="Processos - Visao Advogado")
        card_processos.wait_for(state="visible", timeout=45000)
        
        card_processos.locator("a.mi--forward").click()
        page.wait_for_load_state("networkidle", timeout=30000)
        url_lista_tarefas = page.url
        print(f"[OK] URL da lista de tarefas capturada: {url_lista_tarefas}")

    except Exception as e:
        print(f"[ERRO] Falha crítica ao navegar para a lista de tarefas: {e}")
        raise  # Lança o erro para ser capturado pelo main.py

    for tarefa in TAREFAS_CONFIG:
        try:
            print(f"\n--- Processando tarefa: {tarefa['nome']} ---")
            page.goto(url_lista_tarefas)
            page.wait_for_load_state("networkidle")
            
            tabela_subtipos = page.locator("#tabelaTipoSubtipoGeral")
            tabela_subtipos.wait_for(state="visible", timeout=15000)
            
            celula_tarefa = tabela_subtipos.locator("td", has_text=re.compile(f"^{re.escape(tarefa['nome'])}$"))
            
            if celula_tarefa.count() == 0:
                print(f"    - Tarefa '{tarefa['nome']}' não encontrada com exatidão na tabela de subtipos. Pulando.")
                continue
            
            linha_alvo = celula_tarefa.locator("xpath=..")

            contagem_texto = linha_alvo.locator("td").nth(2).inner_text().strip()
            contagem_numero = int(contagem_texto) if contagem_texto.isdigit() else 0
            print(f"    - {contagem_numero} itens encontrados.")

            if contagem_numero > 0:
                botao_detalhar = linha_alvo.locator('input[title="Detalhar notificações e pendências do subtipo"]')
                botao_detalhar.click(force=True)
                
                print("    - Aguardando carregamento completo da lista detalhada...")
                page.wait_for_load_state("networkidle", timeout=45000)
                time.sleep(2) 
                
                id_tabela = "notificacoesNaoLidasForm:notificacoesNaoLidasDetalhamentoForm:dataTabletableNotificacoesNaoLidas"
                dados_brutos = extrair_dados_com_paginacao(page, id_tabela, tarefa["colunas"], limite_registros=contagem_numero)

                for item in dados_brutos:
                    data_notif = None
                    if 'Gerada em' in item and item['Gerada em']:
                        data_notif = item['Gerada em'].split(" ")[0]
                    elif 'Qtd Dias Gerada' in item and item['Qtd Dias Gerada'].isdigit():
                        dias_atras = int(item['Qtd Dias Gerada'])
                        data_notif_obj = datetime.now() - timedelta(days=dias_atras)
                        data_notif = data_notif_obj.strftime('%d/%m/%Y')

                    if data_notif and item.get("NPJ"):
                        npj = item.get("NPJ")
                        npjs_unicos.add(npj)
                        notificacoes_coletadas.append({
                            "NPJ": npj,
                            "tipo_notificacao": tarefa["nome"],
                            "adverso_principal": item.get("Adverso Principal", ""), 
                            "data_notificacao": data_notif
                        })

        except Exception as e:
            print(f"    - [ERRO] ao processar tarefa '{tarefa['nome']}': {e}")
            continue
    
    return notificacoes_coletadas, list(npjs_unicos)

