# arquivo: main.py
import sys
import traceback
from playwright.sync_api import sync_playwright
import time
from datetime import datetime
from autologin import realizar_login_automatico
import database
import extracao_notificacoes
import processamento_detalhado

def formatar_duracao(segundos):
    """Formata segundos em uma string legível (minutos e segundos)."""
    if segundos < 0: return "0 segundos"
    if segundos < 60:
        return f"{segundos:.2f} segundos"
    minutos, seg = divmod(segundos, 60)
    return f"{int(minutos)} minuto(s) e {int(seg)} segundo(s)"

def main():
    database.inicializar_banco()
    start_time = time.time()
    
    stats_extracao = {"notificacoes": 0}
    stats_processamento = {"sucesso": 0, "falha": 0, "andamentos": 0, "documentos": 0}

    browser = None
    browser_process = None
    # O bloco 'with' já garante que o playwright será fechado.
    # O 'try/except/finally' interno trata erros durante a execução da automação.
    with sync_playwright() as playwright:
        try:
            browser, context, browser_process = realizar_login_automatico(playwright)
            time.sleep(60)
            page = context.new_page()
            
            page.goto("https://juridico.bb.com.br/paj/juridico")
            page.locator("#aPaginaInicial").wait_for(state="visible", timeout=30000)
            print("✅ Verificação de login OK.")
            
            url_central_notificacoes = "https://juridico.bb.com.br/paj/app/paj-central-notificacoes/spas/central-notificacoes/central-notificacoes.app.html"
            page.goto(url_central_notificacoes)
            page.wait_for_load_state("networkidle", timeout=60000)
            print("✅ Central de Notificações carregada.")
            
            terceiro_card = page.locator("div.box-body").locator("div.pendencias-card").nth(2)
            terceiro_card.locator("a.mi--forward").click()
            page.wait_for_load_state("networkidle", timeout=30000)
            url_lista_tarefas = page.url
            print(f"✅ URL da lista de tarefas capturada: {url_lista_tarefas}")

            stats_extracao["notificacoes"] = extracao_notificacoes.extrair_novas_notificacoes(page, url_lista_tarefas)
            stats_processamento = processamento_detalhado.processar_detalhes_pendentes(page)

        except Exception as e:
            print(f"\n❌ Ocorreu uma falha crítica na automação: {e}")
            stats_processamento["falha"] = "Crítico"
            # Re-lança a exceção para que ela seja capturada pelo bloco principal e encerre o script com erro.
            raise
        finally:
            end_time = time.time()
            duracao_total = end_time - start_time
            
            # --- Monta o dicionário de log ---
            total_npjs_processados = stats_processamento.get("sucesso", 0) + (1 if stats_processamento.get("falha") == "Crítico" else stats_processamento.get("falha", 0))
            tempo_medio = duracao_total / total_npjs_processados if total_npjs_processados > 0 else 0

            log_data = {
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "duracao_total": duracao_total, # Salva o valor numérico para o dashboard
                "tempo_medio_npj": tempo_medio,
                "notificacoes_salvas": stats_extracao.get("notificacoes", 0),
                "andamentos_capturados": stats_processamento.get("andamentos", 0),
                "documentos_baixados": stats_processamento.get("documentos", 0),
                "npjs_sucesso": stats_processamento.get("sucesso", 0),
                "npjs_falha": stats_processamento.get("falha", 0)
            }
            
            # Salva o log no banco de dados
            database.salvar_log_execucao(log_data)

            # --- Imprime o resumo no terminal ---
            resumo = f"""
============================================================
📊 RESUMO DA EXECUÇÃO DA RPA ({log_data['timestamp']})
============================================================
- Tempo Total de Execução: {formatar_duracao(log_data['duracao_total'])}
- Média por NPJ Processado: {formatar_duracao(log_data['tempo_medio_npj'])}

- Notificações Novas Salvas: {log_data['notificacoes_salvas']}
- Andamentos Capturados: {log_data['andamentos_capturados']}
- Documentos Baixados: {log_data['documentos_baixados']}

- Processos com Sucesso: {log_data['npjs_sucesso']}
- Processos com Falha: {log_data['npjs_falha']}
============================================================
"""
            print(resumo)

            # --- LÓGICA DE ENCERRAMENTO CONDICIONAL ---
            # Verifica se o script está rodando em modo manual (ou seja, sem o argumento '--automated')
            is_manual_run = '--automated' not in sys.argv

            if 'browser' in locals() and browser and browser.is_connected():
                if is_manual_run:
                    input("\n... Pressione Enter para fechar o navegador e encerrar a RPA ...")
                browser.close()
            elif browser_process:
                browser_process.kill()

# Bloco de execução principal
if __name__ == "__main__":
    try:
        main()
        # Se main() terminar sem erros, o script sairá com código 0 (sucesso) por padrão.
    except Exception as e:
        # Se uma exceção não tratada escapar de main(), ela será capturada aqui.
        print("\n!!! OCORREU UM ERRO CRITICO FINAL NA EXECUCAO DA RPA !!!")
        # O traceback já foi impresso dentro da função 'main' se o erro foi lá.
        # Aqui, apenas garantimos que o script termine com um código de erro.
        sys.exit(1)

