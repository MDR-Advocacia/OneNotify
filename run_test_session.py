# arquivo: run_test_session.py
import sys
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from autologin import realizar_login_automatico
import database
import processamento_detalhado

def formatar_duracao(segundos):
    """Formata segundos em uma string legível (minutos e segundos)."""
    if segundos < 0: return "0 segundos"
    if segundos < 60:
        return f"{segundos:.2f} segundos"
    minutos, seg = divmod(segundos, 60)
    return f"{int(minutos)} minuto(s) e {int(seg)} segundo(s)"

def main_test_session():
    """
    Executa um ciclo de processamento focado apenas nos itens pendentes,
    ideal para processar casos de teste criados manualmente.
    """
    database.inicializar_banco()
    start_time = time.time()
    
    stats_processamento = {"sucesso": 0, "falha": 0, "andamentos": 0, "documentos": 0}

    with sync_playwright() as playwright:
        browser = None
        browser_process = None
        try:
            browser, context, browser_process = realizar_login_automatico(playwright)
            page = context.new_page()
            
            # Apenas uma verificação simples de que o login funcionou
            page.goto("https://juridico.bb.com.br/paj/juridico")
            page.locator("#aPaginaInicial").wait_for(state="visible", timeout=30000)
            print("✅ Verificação de login OK. Iniciando processamento de pendentes.")

            # Pula a extração e vai direto para o processamento detalhado
            stats_processamento = processamento_detalhado.processar_detalhes_pendentes(page)

        except Exception as e:
            print(f"\n❌ Ocorreu uma falha crítica na sessão de teste: {e}")
            raise
        finally:
            end_time = time.time()
            duracao_total = end_time - start_time
            
            total_processado = stats_processamento.get("sucesso", 0) + stats_processamento.get("falha", 0)
            tempo_medio = duracao_total / total_processado if total_processado > 0 else 0

            log_data = {
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S") + " (TESTE)",
                "duracao_total": duracao_total,
                "tempo_medio_npj": tempo_medio,
                "notificacoes_salvas": 0, # Nenhum notificação extraída
                "andamentos_capturados": stats_processamento.get("andamentos", 0),
                "documentos_baixados": stats_processamento.get("documentos", 0),
                "npjs_sucesso": stats_processamento.get("sucesso", 0),
                "npjs_falha": stats_processamento.get("falha", 0)
            }
            database.salvar_log_execucao(log_data)

            resumo = f"""
============================================================
📊 RESUMO DA SESSÃO DE TESTE ({log_data['timestamp']})
============================================================
- Tempo Total: {formatar_duracao(log_data['duracao_total'])}
- Média por NPJ: {formatar_duracao(log_data['tempo_medio_npj'])}
- Andamentos Capturados: {log_data['andamentos_capturados']}
- Documentos Baixados: {log_data['documentos_baixados']}
- Processos com Sucesso: {log_data['npjs_sucesso']}
- Processos com Falha: {log_data['npjs_falha']}
============================================================
"""
            print(resumo)

            if 'browser' in locals() and browser and browser.is_connected():
                input("\n... Sessão de teste concluída. Pressione Enter para fechar o navegador ...")
                browser.close()
            elif browser_process:
                browser_process.kill()

if __name__ == "__main__":
    try:
        main_test_session()
    except Exception:
        print("\n!!! OCORREU UM ERRO CRÍTICO FINAL NA SESSÃO DE TESTE !!!")
        sys.exit(1)
