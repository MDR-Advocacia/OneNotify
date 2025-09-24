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
TAMANHO_LOTE = 2 

def formatar_duracao(segundos):
    if segundos < 0: return "0 segundos"
    if segundos < 60:
        return f"{segundos:.2f} segundos"
    minutos, seg = divmod(segundos, 60)
    return f"{int(minutos)} minuto(s) e {int(seg)} segundo(s)"

def executar_ciclo_extracao_e_ciencia(playwright):
    stats = {"notificacoes_salvas": 0, "ciencias_registradas": 0, "sucesso": False}
    browser = None
    browser_process = None
    try:
        browser, _, browser_process = realizar_login_automatico(playwright)
        time.sleep(60)
        page = browser.contexts[0].new_page()
        
        notificacoes_brutas, npjs_coletados = extracao_notificacoes.extrair_e_obter_npjs(page)
        
        if notificacoes_brutas:
            stats["notificacoes_salvas"] = database.salvar_notificacoes(notificacoes_brutas)
        else:
            print("\nNenhuma nova notificação encontrada para ser salva.")

        if npjs_coletados:
            stats["ciencias_registradas"] = ciencia_notificacoes.registrar_ciencia_para_npjs(page, npjs_coletados)
        else:
            print("\nNenhum NPJ para registrar ciência nesta execução.")
        
        stats["sucesso"] = True
    except Exception as e:
        print(f"[ERRO] Ocorreu uma falha crítica no ciclo de extração e ciência: {e}")
        traceback.print_exc()
        stats["sucesso"] = False
    finally:
        print("\n--- Finalizando ciclo de extração e ciência. ---")
        if browser and browser.is_connected():
            print("    - Desconectando do navegador...")
            browser.close()
        if browser_process:
            print("    - Encerrando o processo do navegador...")
            browser_process.kill()
            
    return stats

def executar_ciclo_processamento(playwright):
    stats_ciclo = {
        "sucesso": 0, "falha": 0, "andamentos": 0, "documentos": 0
    }
    browser = None
    browser_process = None
    try:
        browser, _, browser_process = realizar_login_automatico(playwright)
        time.sleep(60)
        page = browser.contexts[0].new_page()
        
        page.goto("https://juridico.bb.com.br/paj/juridico")
        page.locator("#aPaginaInicial").wait_for(state="visible", timeout=30000)
        print("[OK] Verificação de login OK.")
        
        stats_processamento, _ = processamento_detalhado.processar_detalhes_pendentes(page, TAMANHO_LOTE)
        stats_ciclo.update(stats_processamento)
        
    except Exception as e:
        print(f"\n[ERRO] Ocorreu uma falha crítica no ciclo de processamento: {e}")
        stats_ciclo["falha"] = (stats_ciclo.get("falha", 0) or 0) + 1
        traceback.print_exc()
    finally:
        print("\n--- Finalizando ciclo de processamento, fechando navegador para renovar a sessão. ---")
        if browser and browser.is_connected():
            print("    - Desconectando do navegador...")
            browser.close()
        if browser_process:
            print("    - Encerrando o processo do navegador...")
            browser_process.kill()

    return stats_ciclo

def main():
    database.inicializar_banco()
    
    start_time_geral = time.time()
    stats_gerais = {
        "notificacoes_salvas": 0, "sucesso": 0, "falha": 0, "andamentos": 0, 
        "documentos": 0, "ciencias_registradas": 0
    }

    # --- CICLO DEDICADO DE EXTRAÇÃO E CIÊNCIA ---
    print("\n" + "="*60)
    print("INICIANDO CICLO DE EXTRAÇÃO E CIÊNCIA")
    print("="*60)
    with sync_playwright() as playwright:
        stats_extracao = executar_ciclo_extracao_e_ciencia(playwright)
        stats_gerais["notificacoes_salvas"] = stats_extracao["notificacoes_salvas"]
        stats_gerais["ciencias_registradas"] = stats_extracao["ciencias_registradas"]

    # --- CONTROLE DE FLUXO ---
    if not stats_extracao.get("sucesso", False):
        print("\n[CRÍTICO] O ciclo de extração e ciência falhou. O robô será encerrado para evitar inconsistências.")
        sys.exit(1)

    # --- LOOP DE CICLOS DE PROCESSAMENTO ---
    ciclo_num = 1
    while True:
        database.resetar_notificacoes_em_erro()
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
        
        stats_gerais["sucesso"] += stats_ciclo.get("sucesso", 0)
        stats_gerais["falha"] += stats_ciclo.get("falha", 0)
        stats_gerais["andamentos"] += stats_ciclo.get("andamentos", 0)
        stats_gerais["documentos"] += stats_ciclo.get("documentos", 0)
        
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
        "duracao_total": duracao_total, "tempo_medio_npj": tempo_medio,
        **stats_gerais
    }
    
    database.salvar_log_execucao(log_data)

    resumo = f"""
============================================================
RESUMO FINAL DA EXECUÇÃO DA RPA ({log_data['timestamp']})
============================================================
- Tempo Total de Execução: {formatar_duracao(log_data['duracao_total'])}
- Média por NPJ Processado: {formatar_duracao(log_data['tempo_medio_npj'])}

- Notificações Novas Salvas: {log_data['notificacoes_salvas']}
- Andamentos Capturados: {log_data['andamentos']}
- Documentos Baixados: {log_data['documentos']}

- Processos com Sucesso: {log_data['sucesso']}
- Processos com Falha: {log_data['falha']}
- Notificações com Ciência: {log_data['ciencias_registradas']}
============================================================
"""
    print(resumo)

    if '--automated' not in sys.argv:
        input("\n... Processo finalizado. Pressione Enter para sair ...")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("\n!!! OCORREU UM ERRO CRITICO FINAL NA EXECUCAO DA RPA !!!")
        traceback.print_exc()
        sys.exit(1)

