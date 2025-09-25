@echo off
setlocal

set VENV_DIR=.\venv
set LOG_DIR=.\logs
set SCRIPT_PRINCIPAL=main.py

rem --- Garante que o diretório de logs existe ---
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set DATA_HORA=%date:~10,4%-%date:~4,2%-%date:~7,2%_%time:~0,2%-%time:~3,2%-%time:~6,2%
set DATA_HORA=%DATA_HORA: =0%
set LOG_FILE=%LOG_DIR%\log_%DATA_HORA%.txt

echo ================================================================
echo %date% %time%: Iniciando execucao da RPA...
echo Log detalhado em: %LOG_FILE%
echo.

(
    echo Encerrando processos residuais do Chrome...
    taskkill /F /IM chrome.exe /T > nul 2>&1

    echo Ativando ambiente virtual...
    call "%VENV_DIR%\Scripts\activate.bat"
    
    echo Executando o script principal da RPA...
    python "%SCRIPT_PRINCIPAL%"

    echo Desativando ambiente virtual...
    call deactivate

) >> "%LOG_FILE%" 2>&1

echo.
echo %date% %time%: Execucao da RPA finalizada.
echo ================================================================
echo.
echo Processo finalizado. Verifique o log para detalhes.

endlocal

