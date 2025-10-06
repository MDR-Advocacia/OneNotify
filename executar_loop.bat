@echo off
setlocal

:: --- Configurações ---
:: %~dp0 se expande para o diretório onde este script está localizado, tornando os caminhos mais robustos.
set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%venv"
set "SCRIPT_PRINCIPAL=%SCRIPT_DIR%main.py"
set "LOG_SUPERVISOR=%SCRIPT_DIR%log_supervisor.txt"
set "PAUSA_SUCESSO_SEGUNDOS=1800"
set "PAUSA_FALHA_SEGUNDOS=120"

echo ================================================================ >> "%LOG_SUPERVISOR%"
echo Supervisor iniciado em %date% %time% >> "%LOG_SUPERVISOR%"
echo ================================================================ >> "%LOG_SUPERVISOR%"

:LOOP
echo. >> "%LOG_SUPERVISOR%"
echo ---------------------------------------------------------------- >> "%LOG_SUPERVISOR%"
echo [SUPERVISOR] Iniciando novo ciclo de RPA em %date% %time% >> "%LOG_SUPERVISOR%"
echo ---------------------------------------------------------------- >> "%LOG_SUPERVISOR%"

:: --- Validação de Caminhos ---
echo [SUPERVISOR] Verificando ambiente...
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo.
    echo [SUPERVISOR] ERRO CRITICO: Ambiente virtual nao encontrado em "%VENV_DIR%"
    echo [SUPERVISOR] Verifique se a pasta 'venv' foi criada corretamente neste diretorio.
    echo. >> "%LOG_SUPERVISOR%"
    echo [SUPERVISOR] ERRO CRITICO: Ambiente virtual nao encontrado. Script abortado. >> "%LOG_SUPERVISOR%"
    pause
    exit /b 1
)
if not exist "%SCRIPT_PRINCIPAL%" (
    echo.
    echo [SUPERVISOR] ERRO CRITICO: Script principal 'main.py' nao encontrado.
    echo [SUPERVISOR] Verifique se o arquivo 'main.py' esta neste diretorio.
    echo. >> "%LOG_SUPERVISOR%"
    echo [SUPERVISOR] ERRO CRITICO: 'main.py' nao encontrado. Script abortado. >> "%LOG_SUPERVISOR%"
    pause
    exit /b 1
)

echo [SUPERVISOR] Encerrando processos residuais do Chrome...
taskkill /F /IM chrome.exe /T > nul 2>&1

echo [SUPERVISOR] Ativando ambiente virtual...
call "%VENV_DIR%\Scripts\activate.bat"

echo [SUPERVISOR] Executando o script principal da RPA...
python "%SCRIPT_PRINCIPAL%" 2>> "%LOG_SUPERVISOR%"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo !!!!!!!!!! FALHA DETECTADA !!!!!!!!!!
    echo [SUPERVISOR] O robo encerrou com um erro. Verifique o log para detalhes.
    echo [SUPERVISOR] O script vai reiniciar em 2 minutos. Pressione CTRL+C para cancelar.
    echo. >> "%LOG_SUPERVISOR%"
    echo [SUPERVISOR] !!!!!!!!!! FALHA DETECTADA (Exit Code: %ERRORLEVEL%) em %date% %time% !!!!!!!!!! >> "%LOG_SUPERVISOR%"
    echo [SUPERVISOR] A mensagem de erro do Python (se houver) foi registrada acima. >> "%LOG_SUPERVISOR%"
    echo [SUPERVISOR] Aguardando %PAUSA_FALHA_SEGUNDOS% segundos para reiniciar... >> "%LOG_SUPERVISOR%"
    timeout /t %PAUSA_FALHA_SEGUNDOS% /nobreak > nul
) else (
    echo [SUPERVISOR] Tarefas concluidas. Proxima verificacao em 30 minutos...
    echo [SUPERVISOR] Ciclo de RPA finalizado com SUCESSO em %date% %time%. >> "%LOG_SUPERVISOR%"
    echo [SUPERVISOR] Aguardando %PAUSA_SUCESSO_SEGUNDOS% segundos para o proximo ciclo... >> "%LOG_SUPERVISOR%"
    timeout /t %PAUSA_SUCESSO_SEGUNDOS% /nobreak > nul
)

echo [SUPERVISOR] Desativando ambiente virtual...
call deactivate

goto :LOOP

endlocal

