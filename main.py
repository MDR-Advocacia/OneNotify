# arquivo: main.py
import sys
import subprocess
from pathlib import Path
import logging
from playwright.sync_api import sync_playwright, Playwright
from datetime import datetime
import database
from autologin import realizar_login_automatico
from modulo_notificacoes import executar_extracao_e_ciencia
from processamento_detalhado import processar_detalhes_de_lote

# --- CONFIGURAÇÃO DO CICLO ---
TAMANHO_LOTE_PROCESSAMENTO = 20

def setup_logging(log_file_path: str):
    """Configura o logging para arquivo e console."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] - %(message)s",
        handlers=[
            logging.FileHandler(log_file_path, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def formatar_duracao(segundos):
    """Formata segundos em uma string legível (minutos e segundos)."""
    if segundos < 0: return "0 segundos"
    if segundos < 60:
        return f"{segundos:.2f} segundos"
    minutos, seg = divmod(segundos, 60)
    return f"{int(minutos)} minuto(s) e {int(seg)} segundo(s)"

def main(playwright: Playwright):
    """Função principal que orquestra a execução completa do robô."""
    database.inicializar_banco()
    database.resetar_notificacoes_em_erro()

    browser_process_ref = {'process': None}
    start_time_geral = datetime.now()
    stats_gerais = {
        "notificacoes_salvas": 0, "ciencias_registradas": 0,
        "andamentos": 0, "documentos": 0, "sucesso": 0, "falha": 0
    }

    try:
        logging.info("FASE 1: LOGIN E CONFIGURAÇÃO DA SESSÃO")
        browser, context, browser_process_ref, page = realizar_login_automatico(playwright)
        
        logging.info("\nFASE 2: EXTRAÇÃO DE NOVAS NOTIFICAÇÕES E REGISTRO DE CIÊNCIA")
        stats_extracao = executar_extracao_e_ciencia(page)
        stats_gerais.update(stats_extracao)

        logging.info("\nFASE 3: PROCESSAMENTO DETALHADO EM LOTES")
        while database.contar_pendentes() > 0:
            lote_para_processar = database.obter_npjs_pendentes_por_lote(TAMANHO_LOTE_PROCESSAMENTO)
            if not lote_para_processar:
                logging.info("Nenhum item pendente restante.")
                break
            
            stats_lote = processar_detalhes_de_lote(context, lote_para_processar)
            stats_gerais["sucesso"] += stats_lote["sucesso"]
            stats_gerais["falha"] += stats_lote["falha"]
            stats_gerais["andamentos"] += stats_lote["andamentos"]
            stats_gerais["documentos"] += stats_lote["documentos"]

    except Exception:
        logging.critical("Ocorreu uma falha inesperada na automação.", exc_info=True)
    
    finally:
        logging.info("Finalizando a automação e fechando o navegador.")
        proc = browser_process_ref.get('process')
        if proc and proc.poll() is None:
            logging.info(f"Encerrando o processo do Chrome (PID: {proc.pid})...")
            if sys.platform == "win32":
                subprocess.run(f"TASKKILL /F /PID {proc.pid} /T", shell=True, capture_output=True)
            else:
                proc.kill()
        
        end_time_geral = datetime.now()
        duracao_total = (end_time_geral - start_time_geral).total_seconds()
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
RESUMO FINAL DA EXECUÇÃO ({log_data['timestamp']})
============================================================
- Duração Total: {formatar_duracao(log_data['duracao_total'])}
- Notificações Salvas: {log_data['notificacoes_salvas']}
- NPJs com Sucesso: {log_data['sucesso']}
- NPJs com Falha: {log_data['falha']}
============================================================
"""
        logging.info(resumo)


if __name__ == "__main__":
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
    setup_logging(log_file)
    
    logging.info("=" * 60)
    logging.info("INICIANDO NOVA EXECUÇÃO DA RPA")
    logging.info("=" * 60)
    
    with sync_playwright() as playwright_instance:
        main(playwright_instance)

