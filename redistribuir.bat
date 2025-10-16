@echo off
echo.
echo =================================================================
echo           ATENCAO: SCRIPT DE REDISTRIBUICAO DE TAREFAS
echo =================================================================
echo.
echo Este script ira alterar o campo 'responsavel' de TODAS as
echo notificacoes ja processadas no banco de dados.
echo.
echo Verifique se os perfis dos usuarios estao corretamente
echo configurados no painel antes de continuar.
echo.
set /p "continuar=Voce tem certeza que deseja continuar (S/N)? "

if /i "%continuar%" NEQ "S" (
    echo Operacao cancelada.
    goto :eof
)

echo.
echo Iniciando o script de redistribuicao...
python redistribuir_tarefas.py

echo.
echo Script finalizado.
pause
