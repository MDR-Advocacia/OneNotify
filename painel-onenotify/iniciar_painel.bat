@echo off
TITLE Painel OneNotify - Gerenciador

ECHO ==========================================================
ECHO           INICIANDO AMBIENTE DO PAINEL ONENOTIFY
ECHO ==========================================================
ECHO.

ECHO [1/2] Iniciando Servidor Backend (Flask) em uma nova janela...
REM Inicia o backend em uma nova janela, ativa o venv e executa o Flask com acesso via rede
start "Backend - Flask" cmd /k "echo Ativando ambiente virtual... && venv-painel-stable\Scripts\activate.bat && echo Iniciando servidor Flask... && flask --app server run --host=0.0.0.0"

ECHO.
ECHO [2/2] Iniciando Interface Frontend (React) em uma nova janela...
REM Aguarda um pouco para o backend começar a subir antes de iniciar o front
timeout /t 5 /nobreak > nul
REM Define a variavel HOST para 0.0.0.0 para que o React seja acessivel na rede, usando aspas para evitar espacos
start "Frontend - React" cmd /k "echo Configurando para acesso na rede... && set "HOST=0.0.0.0" && echo Iniciando servidor de desenvolvimento React... && npm start"

ECHO.
ECHO ==========================================================
ECHO   Servidores iniciados. Verifique as novas janelas.
ECHO   Acesse de outros PCs usando: http://SEU_IP_DA_REDE:3000
ECHO   Este gerenciador pode ser fechado.
ECHO ==========================================================
ECHO.
pause

