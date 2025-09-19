# arquivo: extracao_notificacoes.py
from playwright.sync_api import Page, TimeoutError
from datetime import datetime, timedelta
import database 

def extrair_dados_com_paginacao(page: Page, id_tabela: str, colunas_desejadas: list[str], limite_registros: int) -> list[dict]:
    # (O código desta função permanece o mesmo)
    # ...
    dados_extraidos = []
    
    try:
        tabela = page.locator(f'[id="{id_tabela}"]')
        corpo_da_tabela = tabela.locator(f'tbody[id$=":tb"]')
        corpo_da_tabela.locator("tr").first.wait_for(state="visible", timeout=20000)
        print("    - Tabela de notificações encontrada.")
    except TimeoutError:
        print("    - ⚠️ A tabela de notificações não foi encontrada a tempo. Pulando tarefa.")
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
        print(f"\n--- Extraindo dados da página {pagina_atual} ---")
        
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
        
        if len(dados_extraidos) >= limite_registros:
            print(f"    - Limite de {limite_registros} registros atingido. Encerrando extração desta tarefa.")
            break

        paginador = tabela.locator("tfoot")
        if paginador.count() == 0:
            print("    - Paginador não encontrado. Assumindo página única.")
            break
            
        botao_proxima = paginador.locator('td.rich-datascr-button[onclick*="fastforward"]')
        if botao_proxima.count() == 0:
            print("    - Botão 'Próxima Página' (fastforward) não encontrado.")
            break

        classe_do_botao = botao_proxima.get_attribute("class") or ""
        if "dsbld" in classe_do_botao:
            print("    - Não há mais páginas para extrair.")
            break
            
        print("\n    - Clicando em 'Próxima Página'...")
        botao_proxima.click()
        page.wait_for_load_state("networkidle", timeout=30000)
        pagina_atual += 1

    return dados_extraidos


def extrair_novas_notificacoes(page: Page, url_lista_tarefas: str) -> int:
    """
    Navega pela central, extrai os dados básicos, salva no DB e retorna a contagem de itens encontrados.
    """
    print("\n" + "="*20)
    print("INICIANDO MÓDULO DE EXTRAÇÃO DE NOTIFICAÇÕES")
    print("="*20)
    
    # CORREÇÃO: "Adverso Principal" agora é uma coluna opcional para todas as tarefas.
    # A lógica de extração tratará os casos onde ela não existe.
    TAREFAS_CONFIG = [
        #{ "nome": "Pedido Pendente de Finalização", "colunas": ["NPJ", "Adverso Principal", "Gerado em"] },
        { "nome": "Andamento de publicação em processo de condução terceirizada", "colunas": ["NPJ", "Adverso Principal", "Gerada em"] },
        { "nome": "Doc. anexado por empresa externa em processo terceirizado", "colunas": ["NPJ", "Adverso Principal", "Gerada em"] },
        { "nome": "Inclusão de Documentos no NPJ", "colunas": ["NPJ", "Adverso Principal", "Qtd Dias Gerada"] },
    ]
    
    notificacoes_coletadas = []

    for tarefa in TAREFAS_CONFIG:
        try:
            print(f"\n--- Processando tarefa: {tarefa['nome']} ---")
            page.goto(url_lista_tarefas)
            page.wait_for_load_state("networkidle")

            linha_alvo = page.locator(f"tr:has-text(\"{tarefa['nome']}\")")
            if linha_alvo.count() == 0:
                print(f"    - Tarefa '{tarefa['nome']}' não encontrada na página. Pulando.")
                continue

            contagem_texto = linha_alvo.locator("td").nth(2).inner_text().strip()
            contagem_numero = int(contagem_texto) if contagem_texto.isdigit() else 0
            print(f"    - {contagem_numero} itens encontrados.")

            if contagem_numero > 0:
                linha_alvo.get_by_title("Detalhar notificações e pendências do subtipo").click()
                page.wait_for_load_state("networkidle", timeout=30000)
                
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
                        notificacoes_coletadas.append({
                            "NPJ": item.get("NPJ"),
                            "tipo_notificacao": tarefa["nome"],
                            # A chave 'Adverso Principal' será pega se existir; senão, será vazia.
                            "adverso_principal": item.get("Adverso Principal", ""), 
                            "data_notificacao": data_notif
                        })

        except Exception as e:
            print(f"    - ❌ ERRO ao processar tarefa '{tarefa['nome']}': {e}")
            continue

    if notificacoes_coletadas:
        database.salvar_notificacoes(notificacoes_coletadas)
    else:
        print("\nNenhuma nova notificação encontrada para ser salva.")
    
    return len(notificacoes_coletadas)

