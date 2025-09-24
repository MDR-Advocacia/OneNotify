@echo off
setlocal

REM --- Configurações ---
set VENV_DIR=.\venv
set LOG_FILE=agendador_log.txt
set TEMPO_DE_ESPERA_SEGUNDOS=1800
set PAUSA_ANTICHROME_SEGUNDOS=5

echo %date% %time%: Iniciando o agendador de RPA com ciclo fixo. >> %LOG_FILE%
echo Log de execucoes sera salvo em: %LOG_FILE%
echo Pressione Ctrl+C nesta janela para parar o processo a qualquer momento.
echo.

:loop
    REM --- AÇÃO CORRETIVA: Forçar o encerramento de qualquer processo do Chrome ---
    echo %date% %time%: Garantindo que nao ha processos residuais do Chrome... >> %LOG_FILE%
    taskkill /F /IM chrome.exe /T > nul 2>&1
    echo %date% %time%: Pausando por %PAUSA_ANTICHROME_SEGUNDOS% segundos... >> %LOG_FILE%
    timeout /t %PAUSA_ANTICHROME_SEGUNDOS% /nobreak > nul

    echo ================================================================= >> %LOG_FILE%
    echo %date% %time%: Iniciando nova execucao da RPA... >> %LOG_FILE%

    REM --- Ativa o ambiente virtual, executa a RPA e desativa ---
    call "%VENV_DIR%\Scripts\activate.bat"
    python main.py --automated
    call deactivate

    echo %date% %time%: Execucao da RPA finalizada. >> %LOG_FILE%

    REM --- Aguarda um tempo fixo antes do proximo ciclo ---
    echo %date% %time%: Proxima execucao em aproximadamente %TEMPO_DE_ESPERA_SEGUNDOS% segundos... >> %LOG_FILE%
    timeout /t %TEMPO_DE_ESPERA_SEGUNDOS% /nobreak > nul

goto loop
