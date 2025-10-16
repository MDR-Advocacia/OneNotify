@echo off
echo.
echo ==========================================================
echo  SCRIPT PARA CORRIGIR DADOS DE MIGRACAO INVERTIDOS
echo ==========================================================
echo.
echo Este script vai procurar por notificacoes da migracao
echo onde a DATA e o NPJ foram salvos em colunas trocadas.
echo Ele vai corrigir os dados e mover os registros para 'Pendente'.
echo.

python corrigir_migracao.py

echo.
echo Processo de correcao finalizado.
pause
