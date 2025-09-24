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
import ciencia_notificacoes

# --- CONFIGURAÇÃO DO CICLO ---
TAMANHO_LOTE = 50 # Processa 50 NPJs por ciclo de login/logout

def formatar_duracao(segundos):
    """Formata segundos em uma string legível (minutos e segundos)."""
    if segundos < 0: return "0 segundos"
    if segundos < 60:
        return f"{segundos:.2f} segundos"
    minutos, seg = divmod(segundos, 60)
    return f"{int(minutos)} minuto(s) e {int(seg)} segundo(s)"

def executar_ciclo_extracao(playwright):
    """
    Executa um ciclo rápido e dedicado apenas para extrair novas notificações.
    Isso garante que a lista de trabalho esteja sempre atualizada antes de começar
    os ciclos de processamento intensivo.
    """
    print("\n" + "="*60)
    print("INICIANDO CICLO DEDICADO DE EXTRAÇÃO DE NOTIFICAÇÕES")
    print("="*60)
    
    notificacoes_salvas = 0
    browser_process = None
    browser = None
    try:
        browser, context, browser_process = realizar_login_automatico(playwright)
        time.sleep(60)
        page = context.new_page()
        
        # A função de extração agora é autônoma e sabe para onde navegar.
        notificacoes_salvas = extracao_notificacoes.extrair_novas_notificacoes(page)

    except Exception as e:
        print(f"\n[ERRO] Ocorreu uma falha crítica no ciclo de extração: {e}")
        traceback.print_exc()
    finally:
        print("\n--- Finalizando ciclo de extração. ---")
        if browser and browser.is_connected():
            browser.close()
        elif browser_process:
            browser_process.kill()
            
    return notificacoes_salvas

def executar_ciclo_processamento(playwright):
    """
    Executa um ciclo de processamento focado: login, processamento de lote e ciência.
    NÃO faz extração para economizar o tempo de sessão.
    """
    stats_ciclo = {
        "sucesso": 0, "falha": 0, "andamentos": 0, 
        "documentos": 0, "registradas": 0
    }
    browser_process = None
    browser = None

    try:
        browser, context, browser_process = realizar_login_automatico(playwright)
        time.sleep(60)
        page = context.new_page()
        
        # Verificação rápida para garantir que a sessão está ativa
        page.goto("https://juridico.bb.com.br/paj/juridico")
        page.locator("#aPaginaInicial").wait_for(state="visible", timeout=30000)
        print("[OK] Verificação de login OK.")
        
        stats_processamento, npjs_de_sucesso_ciclo = processamento_detalhado.processar_detalhes_pendentes(page, TAMANHO_LOTE)
        stats_ciclo.update(stats_processamento)
        
        if npjs_de_sucesso_ciclo:
            url_central_notificacoes = "https://juridico.bb.com.br/paj/app/paj-central-notificacoes/spas/central-notificacoes/central-notificacoes.app.html"
            stats_ciclo["registradas"] = ciencia_notificacoes.dar_ciencia_em_lote(page, url_central_notificacoes, npjs_de_sucesso_ciclo)

    except Exception as e:
        print(f"\n[ERRO] Ocorreu uma falha crítica no ciclo de processamento: {e}")
        # Se falhar, incrementa o contador de falhas baseado no tamanho do lote para refletir o impacto
        stats_ciclo["falha"] += TAMANHO_LOTE 
        traceback.print_exc()
    finally:
        print("\n--- Finalizando ciclo de processamento, fechando navegador para renovar a sessão. ---")
        if browser and browser.is_connected():
            browser.close()
        elif browser_process:
            browser_process.kill()
            
    return stats_ciclo

def main():
    database.inicializar_banco()
    database.resetar_notificacoes_em_erro()
    
    start_time_geral = time.time()
    
    stats_gerais = {
        "notificacoes": 0, "sucesso": 0, "falha": 0, 
        "andamentos": 0, "documentos": 0, "registradas": 0
    }

    # --- ETAPA 1: CICLO DE EXTRAÇÃO ---
    with sync_playwright() as playwright:
        notificacoes_salvas = executar_ciclo_extracao(playwright)
        stats_gerais["notificacoes"] = notificacoes_salvas

    # --- ETAPA 2: LOOP DE PROCESSAMENTO ---
    ciclo_num = 1
    while True:
        pendentes_antes = database.contar_pendentes()
        if pendentes_antes == 0:
            print("\n[OK] Nenhuma notificação pendente para processar. Encerrando.")
            break

        print("\n" + "="*60)
        print(f"INICIANDO CICLO DE PROCESSAMENTO Nº {ciclo_num}")
        print(f"Notificações pendentes antes do ciclo: {pendentes_antes}")
        print("="*60)

        with sync_playwright() as playwright:
            stats_ciclo = executar_ciclo_processamento(playwright)
        
        for key in stats_gerais:
            stats_gerais[key] += stats_ciclo.get(key, 0)

        pendentes_depois = database.contar_pendentes()
        print(f"\n--- FIM DO CICLO Nº {ciclo_num} ---")
        print(f"Notificações pendentes restantes: {pendentes_depois}")

        if pendentes_depois == 0:
            print("[OK] Todas as notificações foram processadas.")
            break
        
        if pendentes_depois >= pendentes_antes and stats_ciclo.get("sucesso", 0) == 0:
            print("[AVISO] O número de pendentes não diminuiu e nenhum item teve sucesso. Encerrando para evitar loop infinito.")
            break

        ciclo_num += 1
        print("Aguardando 15 segundos antes de iniciar o próximo ciclo...")
        time.sleep(15)

    end_time_geral = time.time()
    duracao_total = end_time_geral - start_time_geral
    total_npjs_processados = stats_gerais["sucesso"] + stats_gerais["falha"]
    tempo_medio = duracao_total / total_npjs_processados if total_npjs_processados > 0 else 0

    log_data = {
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "duracao_total": duracao_total,
        "tempo_medio_npj": tempo_medio,
        "notificacoes_salvas": stats_gerais["notificacoes"],
        "andamentos_capturados": stats_gerais["andamentos"],
        "documentos_baixados": stats_gerais["documentos"],
        "npjs_sucesso": stats_gerais["sucesso"],
        "npjs_falha": stats_gerais["falha"],
        "ciencias_registradas": stats_gerais["registradas"]
    }
    
    database.salvar_log_execucao(log_data)

    resumo = f"""
============================================================
RESUMO FINAL DA EXECUÇÃO DA RPA ({log_data['timestamp']})
============================================================
- Tempo Total de Execução: {formatar_duracao(log_data['duracao_total'])}
- Média por NPJ Processado: {formatar_duracao(log_data['tempo_medio_npj'])}

- Notificações Novas Salvas: {log_data['notificacoes_salvas']}
- Andamentos Capturados: {log_data['andamentos_capturados']}
- Documentos Baixados: {log_data['documentos_baixados']}

- Processos com Sucesso: {log_data['npjs_sucesso']}
- Processos com Falha: {log_data['npjs_falha']}
- Notificações com Ciência: {log_data['ciencias_registradas']}
============================================================
"""
    print(resumo)

    is_manual_run = '--automated' not in sys.argv
    if is_manual_run:
        input("\n... Processo finalizado. Pressione Enter para sair ...")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("\n!!! OCORREU UM ERRO CRITICO FINAL NA EXECUCAO DA RPA !!!")
        traceback.print_exc()
        sys.exit(1)

