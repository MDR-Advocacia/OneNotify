# arquivo: config.py
import logging

# --- CONFIGURAÇÕES GERAIS ---
TAMANHO_LOTE = 50

# --- CONFIGURAÇÕES DE LOG ---
# Adiciona as variáveis de configuração de log que estavam faltando
LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s [%(levelname)s] - %(message)s'

# --- CONFIGURAÇÕES DE TAREFAS ---
# Lista de tarefas a serem processadas na Fase 2
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

