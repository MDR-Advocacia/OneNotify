RPA para Monitoramento e Processamento de Notificações Jurídicas
Este projeto é uma solução de Automação de Processos Robóticos (RPA) desenvolvida em Python para automatizar a coleta, processamento e gestão de notificações de um portal jurídico. A automação acessa o sistema, extrai novas notificações, busca informações detalhadas como andamentos e documentos, e armazena tudo em um banco de dados local.
Para facilitar a análise dos resultados, o projeto inclui um dashboard web local com filtros, paginação e um sistema de gerenciamento de status das notificações.
(Exemplo da interface do Dashboard)
<!--- Substitua pelo URL ou caminho de uma imagem do seu dashboard --->
✨ Funcionalidades Principais
Arquitetura Modular: O código é desacoplado em módulos com responsabilidades únicas (extração, processamento, banco de dados, visualização), facilitando a manutenção e a escalabilidade.
Extração Inteligente: Acessa a central de notificações e extrai de forma paginada todos os novos alertas para os tipos configurados.
Processamento Detalhado: Para cada notificação, navega até a página do processo (NPJ) e realiza uma busca contextual por andamentos e documentos em uma janela de tempo de 3 dias (D, D-1, D-2).
Tratamento de Andamentos: Captura todos os tipos de andamentos. Para publicações DJ/DO, abre o modal de detalhes, expande o conteúdo e extrai o texto completo. Para outros, registra o título e a data.
Download de Documentos: Encontra e baixa todos os documentos (.pdf, .txt, etc.) dentro da janela de tempo, organizando-os em pastas por NPJ.
Banco de Dados Persistente: Utiliza SQLite para armazenar todas as informações coletadas, criando um histórico robusto e consultável.
Dashboard Web Interativo: Uma interface web local (criada com Flask) permite:
Visualizar todas as notificações em uma tabela paginada.
Filtrar por status (Novo, Processado, Arquivado, etc.) e por tipo de notificação.
Arquivar e desarquivar notificações tratadas.
Visualizar textos de publicações em um menu expansível.
Baixar documentos com um clique.
Log de Execuções: Cada execução da RPA gera um registro de log com métricas de performance (duração total, tempo médio por NPJ, itens processados, sucessos e falhas).
Modo de Teste: Caso não haja notificações novas, o robô ativa um modo de teste, reprocessando os 5 últimos NPJs bem-sucedidos para garantir que a lógica de extração detalhada continue funcional.
Executor Simplificado: Um script .bat oferece um menu simples para iniciar a automação ou o dashboard web separadamente.
🛠️ Tecnologias Utilizadas
Python 3
Playwright: Para automação e controle do navegador.
SQLite3: Para o banco de dados local.
Flask: Para a criação do dashboard web.
📂 Estrutura do Projeto
/seu_projeto/
|
|-- executar.bat                # Menu para iniciar a RPA ou o Dashboard
|-- main.py                     # Orquestrador principal da automação
|-- extracao_notificacoes.py    # Módulo responsável pela extração das notificações
|-- processamento_detalhado.py  # Módulo para busca de andamentos e documentos
|-- database.py                 # Gerenciador do banco de dados SQLite
|-- visualizador_web.py         # Servidor Flask para o dashboard
|-- autologin.py                # (Fornecido pelo usuário) Lógica de login no portal
|-- rpa.db                      # Arquivo do banco de dados (criado na primeira execução)
|-- /downloads/                 # Pasta onde os documentos baixados são salvos


🚀 Como Executar
1. Pré-requisitos
Python 3.8 ou superior instalado.
O arquivo autologin.py, contendo a lógica de login específica do portal, deve estar presente no diretório raiz.
2. Instalação
Abra o terminal na pasta do projeto e instale as dependências necessárias:
# Instalar as bibliotecas Python
pip install playwright flask

# Instalar os navegadores que o Playwright utiliza
playwright install


3. Execução
Para iniciar, basta dar um duplo clique no arquivo executar.bat. Ele abrirá um menu no terminal:
====================================================
 MENU DE EXECUCAO - AUTOMACAO DE PROCESSOS
====================================================

 Escolha uma opcao:

 1. Executar a Automacao (RPA)
 2. Iniciar o Dashboard de Visualizacao
 3. Sair

Digite o numero da sua escolha e pressione Enter:


Opção 1: Inicia o robô. Ele realizará o login, extrairá as notificações e processará os detalhes. Ao final, exibirá um resumo da execução e salvará um log no banco de dados.
Opção 2: Inicia o servidor web do dashboard e abre a página http://127.0.0.1:5000 no seu navegador padrão para que você possa analisar os resultados.
Importante: Na primeira vez que executar, o arquivo rpa.db será criado automaticamente. Se precisar resetar o banco de dados, basta apagar este arquivo e executar a automação novamente.
