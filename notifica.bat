@echo off
title Menu de Execucao - RPA
:menu
cls
echo ====================================================
echo  MENU DE EXECUCAO - AUTOMACAO DE PROCESSOS
echo ====================================================
echo.
echo  Escolha uma opcao:
echo.
echo  1. Executar a Automacao (RPA)
echo  2. Iniciar o Dashboard de Visualizacao
echo  3. Sair
echo.
set /p choice="Digite o numero da sua escolha e pressione Enter: "

if "%choice%"=="1" goto run_rpa
if "%choice%"=="2" goto run_dashboard
if "%choice%"=="3" goto exit_script

echo Opcao invalida. Pressione qualquer tecla para tentar novamente.
pause > nul
goto menu

:run_rpa
cls
echo Iniciando a Automacao (RPA)...
python main.py
echo.
echo Automacao concluida. Pressione qualquer tecla para voltar ao menu.
pause > nul
goto menu

:run_dashboard
cls
echo Iniciando o Dashboard de Visualizacao...
echo.
echo Acesse http://127.0.0.1:5000 no seu navegador.
echo Pressione CTRL+C neste terminal para parar o servidor.
echo.
python visualizador_web.py
echo.
echo Servidor finalizado. Pressione qualquer tecla para voltar ao menu.
pause > nul
goto menu

:exit_script
exit
