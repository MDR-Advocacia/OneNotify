#!/bin/bash

VENV_DIR="./venv"
LOG_DIR="./logs"
SCRIPT_PRINCIPAL="main.py"

# Garante que o diretório de logs existe
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/log_$(date +%Y-%m-%d_%H-%M-%S).txt"

echo "================================================================"
echo "$(date): Iniciando execução da RPA..."
echo "Log detalhado em: $LOG_FILE"
echo ""

    echo "Encerrando processos residuais do Chrome..."
    pkill -f "Google Chrome" > /dev/null 2>&1
    sleep 2

    echo "Ativando ambiente virtual..."
    source "$VENV_DIR/bin/activate"

    echo "Executando o script principal da RPA..."
    python3 "$SCRIPT_PRINCIPAL"

    echo "Desativando ambiente virtual..."
    deactivate


echo ""
echo "$(date): Execução da RPA finalizada."
echo "================================================================"
echo ""
echo "Processo finalizado. Verifique o log para detalhes."

