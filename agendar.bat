@echo off
title OneNotify - Agendador de RPA (Ciclo Fixo v2)

set VENV_DIR=.\venv
set LOG_FILE=agendador_log.txt
set CICLO_SEGUNDOS=1800
set INTERVALO_EM_CASO_DE_EXCESSO=120

echo %date% %time%: Iniciando o agendador de RPA com ciclo fixo. >> %LOG_FILE%
echo Log de execucoes sera salvo em: %LOG_FILE%
echo.
echo Pressione Ctrl+C nesta janela para parar o processo a qualquer momento.
echo.

:loop
:: --- Captura o tempo de início de forma robusta ---
set "HORA_INICIO=%time: =0%"
set /a INICIO_SEGUNDOS = (%HORA_INICIO:~0,2%)*3600 + (%HORA_INICIO:~3,2%)*60 + (%HORA_INICIO:~6,2%)

echo ================================================================ >> %LOG_FILE%
echo %date% %time%: Iniciando nova execucao da RPA... >> %LOG_FILE%
echo %date% %time%: Iniciando nova execucao da RPA...

:: Ativa o ambiente virtual e executa a RPA
call %VENV_DIR%\Scripts\activate.bat
python main.py --automated
call %VENV_DIR%\Scripts\deactivate.bat

echo %date% %time%: Execucao da RPA finalizada. >> %LOG_FILE%
echo %date% %time%: Execucao da RPA finalizada.

:: --- Captura o tempo de fim e calcula a duração ---
set "HORA_FIM=%time: =0%"
set /a FIM_SEGUNDOS = (%HORA_FIM:~0,2%)*3600 + (%HORA_FIM:~3,2%)*60 + (%HORA_FIM:~6,2%)
set /a DURACAO_SEGUNDOS = FIM_SEGUNDOS - INICIO_SEGUNDOS

:: Corrige o cálculo caso a execução passe da meia-noite
if %DURACAO_SEGUNDOS% LSS 0 set /a DURACAO_SEGUNDOS += 86400

echo %date% %time%: Duracao da execucao: %DURACAO_SEGUNDOS% segundos. >> %LOG_FILE%

:: --- Calcula o tempo de espera para o próximo ciclo ---
if %DURACAO_SEGUNDOS% GEQ %CICLO_SEGUNDOS% (
    echo %date% %time%: A execucao excedeu o tempo de ciclo. Aguardando %INTERVALO_EM_CASO_DE_EXCESSO% segundos. >> %LOG_FILE%
    set "TEMPO_ESPERA=%INTERVALO_EM_CASO_DE_EXCESSO%"
) else (
    set /a TEMPO_ESPERA = CICLO_SEGUNDOS - DURACAO_SEGUNDOS
)

:: --- Limpa processos do Chrome ANTES de esperar ---
echo %date% %time%: Limpando processos residuais do Chrome... >> %LOG_FILE%
echo %date% %time%: Limpando processos residuais do Chrome...
taskkill /F /IM chrome.exe /T > nul 2>&1

:: --- Aguarda o tempo calculado ---
echo %date% %time%: Aguardando %TEMPO_ESPERA% segundos para a proxima execucao... >> %LOG_FILE%
echo %date% %time%: Proxima execucao em aproximadamente %TEMPO_ESPERA% segundos...
timeout /t %TEMPO_ESPERA% /nobreak > nul

goto :loop

