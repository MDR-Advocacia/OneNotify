#!/bin/bash

# --- Script de menu para executar a automação ou o dashboard no macOS ---

# Função para exibir o menu
mostrar_menu() {
    clear
    echo "===================================================="
    echo "          MENU DE EXECUÇÃO - ONENOTIFY"
    echo "===================================================="
    echo ""
    echo " Escolha uma opção:"
    echo ""
    echo " 1. Executar a Automação (RPA)"
    echo " 2. Iniciar o Dashboard de Visualização"
    echo " 3. Sair"
    echo ""
}

# Loop principal do menu
while true; do
    mostrar_menu
    read -p " Digite o número da sua escolha e pressione Enter: " escolha

    # Ativa o ambiente virtual antes de executar qualquer opção
    if [ -d "venv" ]; then
        source venv/bin/activate
    else
        echo "ERRO: Ambiente virtual 'venv' não encontrado."
        echo "Por favor, execute o script './iniciar_ambiente.sh' primeiro."
        exit 1
    fi

    case $escolha in
        1)
            echo "Iniciando a automação (RPA)..."
            # Supondo que o script principal se chame 'main.py'
            python3 main.py
            echo "Automação finalizada. Pressione Enter para voltar ao menu."
            read
            ;;
        2)
            echo "Iniciando o Dashboard de Visualização..."
            python3 visualizador_web.py
            echo "Dashboard finalizado. Pressione Enter para voltar ao menu."
            read
            ;;
        3)
            echo "Saindo..."
            deactivate
            exit 0
            ;;
        *)
            echo "Opção inválida. Pressione Enter para tentar novamente."
            read
            ;;
    esac
    
    # Desativa o ambiente virtual após a execução da opção
    deactivate
done
