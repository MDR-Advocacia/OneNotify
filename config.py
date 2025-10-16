import logging

# --- CONFIGURAÇÕES GERAIS ---
TAMANHO_LOTE = 50
# NOVO: Limite de tempo em segundos para cada ciclo de extração na FASE 2. (25 minutos)
TEMPO_LIMITE_EXTRACAO = 25 * 60 

# --- CONFIGURAÇÕES DE LOG ---
LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s [%(levelname)s] - %(message)s'

# --- CONFIGURAÇÕES DE TAREFAS ---
TAREFAS_CONFIG = [
    {
        "nome": "Andamento de publicação em processo de condução terceirizada",
        "url_path": "andamento-publicacao-terceirizado"
    },
    {
        "nome": "Doc. anexado por empresa externa em processo terceirizado",
        "url_path": "documento-anexado-empresa-externa-terceirizado"
    },
    {
        "nome": "Inclusão de Documentos no NPJ",
        "url_path": "inclusao-documentos-npj"
    },
]
