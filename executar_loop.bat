@echo off
setlocal enabledelayedexpansion

:: --- Configurações ---
set "SCRIPT_DIR=%~dp0"
set "LOG_DIR=%SCRIPT_DIR%logs"
set "VENV_DIR=%SCRIPT_DIR%venv"
set "SCRIPT_PRINCIPAL=%SCRIPT_DIR%main.py"
set "PAUSA_SUCESSO_SEGUNDOS=1800"
set "PAUSA_FALHA_SEGUNDOS=120"

:: --- Criação da pasta de logs ---
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:LOOP
cls

:: --- Geração de timestamp robusto via WMIC (independente de localidade) ---
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /format:list') do set "datetime=%%I"
set "YYYY=!datetime:~0,4!"
set "MM=!datetime:~4,2!"
set "DD=!datetime:~6,2!"
set "HH=!datetime:~8,2!"
set "MIN=!datetime:~10,2!"
set "SEC=!datetime:~12,2!"
set "TIMESTAMP=!YYYY!-!MM!-!DD!_!HH!-!MIN!-!SEC!"
set "LOG_CICLO=%LOG_DIR%\supervisor_ciclo_!TIMESTAMP!.log"

echo ---------------------------------------------------------------- >> "%LOG_CICLO%"
echo [SUPERVISOR] Iniciando novo ciclo de RPA em %date% %time% >> "%LOG_CICLO%"
echo ---------------------------------------------------------------- >> "%LOG_CICLO%"

:: --- Validação de Caminhos ---
echo [SUPERVISOR] Verificando ambiente...
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [SUPERVISOR] ERRO CRITICO: Ambiente virtual nao encontrado. Script abortado. >> "%LOG_CICLO%"
    pause
    exit /b 1
)
if not exist "%SCRIPT_PRINCIPAL%" (
    echo [SUPERVISOR] ERRO CRITICO: Script principal 'main.py' nao encontrado. Script abortado. >> "%LOG_CICLO%"
    pause
    exit /b 1
)

echo [SUPERVISOR] Encerrando processos residuais do Chrome...
taskkill /F /IM chrome.exe /T > nul 2>&1

echo [SUPERVISOR] Ativando ambiente virtual...
call "%VENV_DIR%\Scripts\activate.bat"

echo [SUPERVISOR] Executando o script principal da RPA...
echo [SUPERVISOR] Log detalhado desta execucao em: %LOG_CICLO%

:: Redireciona a saida de erro (2) para o log do ciclo
python "%SCRIPT_PRINCIPAL%" 2>> "%LOG_CICLO%"

if %ERRORLEVEL% NEQ 0 (
    goto :HANDLE_FAILURE
) else (
    goto :HANDLE_SUCCESS
)

:: --- SUB-ROTINA DE SUCESSO ---
:HANDLE_SUCCESS
echo.
echo [SUPERVISOR] Tarefas concluidas com sucesso.
echo [SUPERVISOR] Pressione CTRL+C para interromper o loop.
echo [SUPERVISOR] Ciclo de RPA finalizado com SUCESSO. >> "%LOG_CICLO%"

powershell -Command "$curTop = [System.Console]::CursorTop; for ($i = %PAUSA_SUCESSO_SEGUNDOS%; $i -ge 1; $i--) { [System.Console]::SetCursorPosition(0, $curTop); $min = [int]($i/60); $sec = $i%%60; Write-Host -NoNewline ('[PAUSA] Proximo ciclo em: {0}m {1:00}s...' -f $min, $sec).PadRight([System.Console]::WindowWidth - 1); Start-Sleep -Seconds 1 }"
echo.
goto :LOOP

:: --- SUB-ROTINA DE FALHA ---
:HANDLE_FAILURE
echo.
echo !!!!!!!!!! FALHA DETECTADA !!!!!!!!!!
echo [SUPERVISOR] O robo encerrou com um erro. Verifique o log para detalhes.
echo [SUPERVISOR] O script vai reiniciar em breve. Pressione CTRL+C para cancelar.
echo [SUPERVISOR] !!!!!!!!!! FALHA DETECTADA (Exit Code: %ERRORLEVEL%) em %date% %time% !!!!!!!!!! >> "%LOG_CICLO%"

powershell -Command "$curTop = [System.Console]::CursorTop; for ($i = %PAUSA_FALHA_SEGUNDOS%; $i -ge 1; $i--) { [System.Console]::SetCursorPosition(0, $curTop); Write-Host -NoNewline ('[REINICIANDO] Em: {0}s...' -f $i).PadRight([System.Console]::WindowWidth - 1); Start-Sleep -Seconds 1 }"
echo.
goto :LOOP

endlocal
pause

