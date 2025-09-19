#!/bin/bash

# --- Script para configurar o ambiente virtual no macOS ---

echo "Verificando a versão do Python..."
# Garante que o python3 está instalado
if ! command -v python3 &> /dev/null
then
    echo "ERRO: Python 3 não encontrado. Por favor, instale o Python 3 para continuar."
    exit 1
fi

echo "Python 3 encontrado."

# Define o nome da pasta do ambiente virtual
VENV_DIR="venv"

# Verifica se o diretório do venv já existe
if [ -d "$VENV_DIR" ]; then
    echo "Ambiente virtual '$VENV_DIR' já existe. Pulando a criação."
else
    echo "Criando ambiente virtual em '$VENV_DIR'..."
    python3 -m venv $VENV_DIR
    if [ $? -ne 0 ]; then
        echo "ERRO: Falha ao criar o ambiente virtual."
        exit 1
    fi
    echo "Ambiente virtual criado com sucesso."
fi

echo "Ativando o ambiente virtual..."
source $VENV_DIR/bin/activate
if [ $? -ne 0 ]; then
    echo "ERRO: Falha ao ativar o ambiente virtual."
    exit 1
fi

echo "Instalando dependências do arquivo requirements.txt..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERRO: Falha ao instalar as dependências."
    deactivate
    exit 1
fi
echo "Dependências instaladas com sucesso."

echo "Instalando os navegadores do Playwright..."
playwright install
if [ $? -ne 0 ]; then
    echo "ERRO: Falha ao instalar os navegadores do Playwright."
    deactivate
    exit 1
fi
echo "Navegadores instalados com sucesso."

echo ""
echo "============================================================"
echo " Ambiente configurado com sucesso!"
echo " Para ativar manualmente no futuro, use o comando:"
echo " source venv/bin/activate"
echo ""
echo " Para iniciar o robô ou o dashboard, execute:"
echo " ./executar.sh"
echo "============================================================"

# Desativa o ambiente ao final do script para não deixar o terminal do usuário ativado
deactivate
