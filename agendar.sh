#!/bin/bash
# Script para agendar e executar a RPA em loop no macOS/Linux

# --- Configurações ---
VENV_DIR="./venv" # Diretório do ambiente virtual
LOG_FILE="agendador_log.txt" # Arquivo de log
CICLO_SEGUNDOS=1800 # 30 minutos
INTERVALO_EM_CASO_DE_EXCESSO=120 # 2 minutos

echo "$(date): Iniciando o agendador de RPA com ciclo fixo." | tee -a "$LOG_FILE"
echo "Log de execuções será salvo em: $LOG_FILE"
echo "Pressione Ctrl+C nesta janela para parar o processo a qualquer momento."
echo ""

# Loop infinito
while true; do
    # Captura o tempo de início
    INICIO_SEGUNDOS=$(date +%s)

    echo "================================================================" | tee -a "$LOG_FILE"
    echo "$(date): Iniciando nova execução da RPA..." | tee -a "$LOG_FILE"
    
    # Ativa o ambiente virtual, executa a RPA e desativa
    source "$VENV_DIR/bin/activate"
    python3 main.py --automated
    deactivate
    
    echo "$(date): Execução da RPA finalizada." | tee -a "$LOG_FILE"

    # Captura o tempo de fim e calcula a duração
    FIM_SEGUNDOS=$(date +%s)
    DURACAO_SEGUNDOS=$((FIM_SEGUNDOS - INICIO_SEGUNDOS))

    echo "$(date): Duração da execução: $DURACAO_SEGUNDOS segundos." | tee -a "$LOG_FILE"

    # Calcula o tempo de espera para o próximo ciclo
    if [ "$DURACAO_SEGUNDOS" -ge "$CICLO_SEGUNDOS" ]; then
        echo "$(date): A execução excedeu o tempo de ciclo. Aguardando $INTERVALO_EM_CASO_DE_EXCESSO segundos." | tee -a "$LOG_FILE"
        TEMPO_ESPERA=$INTERVALO_EM_CASO_DE_EXCESSO
    else
        TEMPO_ESPERA=$((CICLO_SEGUNDOS - DURACAO_SEGUNDOS))
    fi

    # Limpa processos residuais do Chrome (específico para macOS/Linux)
    echo "$(date): Limpando processos residuais do Chrome..." | tee -a "$LOG_FILE"
    pkill -f "Google Chrome" > /dev/null 2>&1

    # Aguarda o tempo calculado
    echo "$(date): Próxima execução em aproximadamente $TEMPO_ESPERA segundos..." | tee -a "$LOG_FILE"
    sleep "$TEMPO_ESPERA"
done
