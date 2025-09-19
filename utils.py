# arquivo: utils.py
from playwright.sync_api import Page

def extrair_dados_com_paginacao(page: Page, id_tabela: str, colunas_desejadas: list[str], limite_registros: int) -> list[dict]:
    """Extrai dados de uma tabela com paginação. (Função original refatorada)."""
    dados_extraidos = []
    tabela = page.locator(f'[id="{id_tabela}"]')
    corpo_da_tabela = tabela.locator('tbody[id$=":tb"]')
    
    try:
        corpo_da_tabela.locator("tr").first.wait_for(state="visible", timeout=20000)
    except Exception:
        print("    - Tabela de dados não apareceu no tempo esperado. Nenhum dado extraído.")
        return []

    print("    - Tabela encontrada. Mapeando colunas...")
    indices_colunas = {}
    headers = tabela.locator("thead th")
    for i in range(headers.count()):
        header_text = headers.nth(i).inner_text().strip()
        if header_text in colunas_desejadas:
            indices_colunas[header_text] = i
    
    print(f"    - Mapeamento de colunas: {indices_colunas}")
    pagina_atual = 1
    
    while len(dados_extraidos) < limite_registros:
        print(f"\n    --- Extraindo dados da página {pagina_atual} ---")
        corpo_da_tabela.wait_for(state="visible")
        
        for linha in corpo_da_tabela.locator("tr").all():
            if len(dados_extraidos) >= limite_registros:
                break
            item = {
                nome_coluna: linha.locator("td").nth(indice).inner_text().strip()
                for nome_coluna, indice in indices_colunas.items()
            }
            dados_extraidos.append(item)
        
        print(f"    - {len(dados_extraidos)} de {limite_registros} registros extraídos até agora.")

        paginador = tabela.locator("tfoot")
        if not paginador.count(): break
        
        # O seletor original usava 'fastforward', mas o 'Next' é mais comum.
        # Vamos usar um seletor mais genérico para a próxima página.
        botao_proxima = paginador.locator('td.rich-datascr-button:not(.rich-datascr-button-dsbld)[onclick*="scroller.fastforward"]')
        
        if not botao_proxima.count():
             break # Não há mais páginas

        print("    - Clicando em 'Próxima Página'...")
        botao_proxima.click()
        page.wait_for_load_state("networkidle", timeout=30000)
        pagina_atual += 1

    return dados_extraidos[:limite_registros]
