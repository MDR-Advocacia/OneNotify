#!/usr/bin/env bash
set -uo pipefail

APP_DIR="${APP_DIR:-/app}"
LOG_DIR="${LOG_DIR:-${APP_DIR}/logs}"
SCRIPT_PRINCIPAL="${SCRIPT_PRINCIPAL:-${APP_DIR}/main.py}"
PAUSA_SUCESSO_SEGUNDOS="${RPA_PAUSA_SUCESSO_SEGUNDOS:-1800}"
PAUSA_FALHA_SEGUNDOS="${RPA_PAUSA_FALHA_SEGUNDOS:-120}"

mkdir -p "$LOG_DIR"

log_msg() {
  local message="$1"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SUPERVISOR] ${message}"
}

encerrar_chrome_residual() {
  log_msg "Encerrando processos residuais do Chrome/Chromium..."
  pkill -f "chrome|chromium|chrome_crashpad|Google Chrome" >/dev/null 2>&1 || true
  sleep 2
}

while true; do
  timestamp="$(date '+%Y-%m-%d_%H-%M-%S')"
  log_ciclo="${LOG_DIR}/supervisor_ciclo_${timestamp}.log"

  {
    echo "----------------------------------------------------------------"
    echo "[SUPERVISOR] Iniciando novo ciclo de RPA em $(date '+%Y-%m-%d %H:%M:%S')"
    echo "----------------------------------------------------------------"
  } | tee -a "$log_ciclo"

  if [[ ! -f "$SCRIPT_PRINCIPAL" ]]; then
    log_msg "ERRO CRITICO: script principal nao encontrado em ${SCRIPT_PRINCIPAL}." | tee -a "$log_ciclo"
    sleep "$PAUSA_FALHA_SEGUNDOS"
    continue
  fi

  encerrar_chrome_residual | tee -a "$log_ciclo"
  log_msg "Executando ${SCRIPT_PRINCIPAL}. Log do ciclo: ${log_ciclo}" | tee -a "$log_ciclo"

  set +e
  python "$SCRIPT_PRINCIPAL" >>"$log_ciclo" 2>&1
  exit_code="$?"
  set +e

  log_msg "Ultimas linhas do ciclo:" | tee -a "$log_ciclo"
  tail -n 80 "$log_ciclo" || true
  encerrar_chrome_residual | tee -a "$log_ciclo"

  if [[ "$exit_code" -eq 0 ]]; then
    log_msg "Ciclo finalizado com SUCESSO. Proximo ciclo em ${PAUSA_SUCESSO_SEGUNDOS}s." | tee -a "$log_ciclo"
    sleep "$PAUSA_SUCESSO_SEGUNDOS"
  else
    log_msg "FALHA DETECTADA (exit code ${exit_code}). Reiniciando em ${PAUSA_FALHA_SEGUNDOS}s." | tee -a "$log_ciclo"
    sleep "$PAUSA_FALHA_SEGUNDOS"
  fi
done
