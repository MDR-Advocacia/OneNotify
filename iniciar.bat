@echo off
set VENV_DIR=.\venv

echo Verificando a existencia do ambiente virtual...

REM Verifica se a pasta do venv existe
if not exist "%VENV_DIR%" (
    echo Criando ambiente virtual em '%VENV_DIR%'...
    python -m venv %VENV_DIR%
    if %errorlevel% neq 0 (
        echo.
        echo ERRO: Falha ao criar o ambiente virtual.
        echo Verifique se o Python esta instalado e no PATH do sistema.
        pause
        exit /b 1
    )
)

echo Ativando o ambiente virtual...
call "%VENV_DIR%\Scripts\activate.bat"

echo.
echo Instalando dependencias do requirements.txt...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo ERRO: Falha ao instalar as dependencias.
    pause
    exit /b 1
)

echo.
echo =======================================================
echo  Ambiente virtual pronto e dependencias instaladas!
echo =======================================================
echo.
echo Para reativar este ambiente no futuro, execute no seu terminal:
echo %VENV_DIR%\Scripts\activate
echo.
pause
