@echo off
setlocal

:: --- Configurações ---
set VENV_DIR=.\venv
set SCRIPT_PRINCIPAL=main.py
set LOG_SUPERVISOR=log_supervisor.txt
set PAUSA_SUCESSO_SEGUNDOS=1800
set PAUSA_FALHA_SEGUNDOS=120

echo ================================================================ >> %LOG_SUPERVISOR%
echo Supervisor iniciado em %date% %time% >> %LOG_SUPERVISOR%
echo ================================================================ >> %LOG_SUPERVISOR%

:LOOP
echo. >> %LOG_SUPERVISOR%
echo ---------------------------------------------------------------- >> %LOG_SUPERVISOR%
echo [SUPERVISOR] Iniciando novo ciclo de RPA em %date% %time% >> %LOG_SUPERVISOR%
echo ---------------------------------------------------------------- >> %LOG_SUPERVISOR%

echo [SUPERVISOR] Encerrando processos residuais do Chrome...
taskkill /F /IM chrome.exe /T > nul 2>&1

echo [SUPERVISOR] Ativando ambiente virtual...
call "%VENV_DIR%\Scripts\activate.bat"

echo [SUPERVISOR] Executando o script principal da RPA...
python "%SCRIPT_PRINCIPAL%"

rem --- Verifica se a execução anterior teve erro ---
if %ERRORLEVEL% NEQ 0 (
    echo [SUPERVISOR] ERRO DETECTADO (Exit Code: %ERRORLEVEL%) em %date% %time%. >> %LOG_SUPERVISOR%
    echo [SUPERVISOR] O robô encontrou uma falha. Aguardando %PAUSA_FALHA_SEGUNDOS% segundos para reiniciar... >> %LOG_SUPERVISOR%
    echo [SUPERVISOR] Aguardando %PAUSA_FALHA_SEGUNDOS% segundos antes de reiniciar...
    timeout /t %PAUSA_FALHA_SEGUNDOS% /nobreak > nul
) else (
    echo [SUPERVISOR] Execucao finalizada com SUCESSO em %date% %time%. >> %LOG_SUPERVISOR%
    echo [SUPERVISOR] Aguardando %PAUSA_SUCESSO_SEGUNDOS% segundos para o proximo ciclo... >> %LOG_SUPERVISOR%
    echo [SUPERVISOR] Tarefas concluidas. Proxima verificacao em 30 minutos...
    timeout /t %PAUSA_SUCESSO_SEGUNDOS% /nobreak > nul
)

echo [SUPERVISOR] Desativando ambiente virtual...
call deactivate

goto :LOOP

endlocal

