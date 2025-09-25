# arquivo: database.py
import sqlite3
import json
import logging
from datetime import datetime

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
DB_NOME = "rpa_refatorado.db"
TABELA_NOTIFICACOES = "notificacoes"
TABELA_LOGS = "logs_execucao"

def inicializar_banco():
    """Garante que o banco de dados e as tabelas necessárias existam."""
    try:
        with sqlite3.connect(DB_NOME) as conn:
            cursor = conn.cursor()
            
            # Tabela de Notificações
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABELA_NOTIFICACOES} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                NPJ TEXT NOT NULL,
                tipo_notificacao TEXT NOT NULL,
                data_notificacao TEXT NOT NULL,
                adverso_principal TEXT,
                status TEXT NOT NULL DEFAULT 'Pendente',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                numero_processo TEXT,
                andamentos TEXT,
                documentos TEXT
            )
            """)
            cursor.execute(f"""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_notificacao_unica
            ON {TABELA_NOTIFICACOES} (NPJ, tipo_notificacao, data_notificacao)
            """)
            
            # Tabela de Logs
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABELA_LOGS} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                duracao_total REAL,
                tempo_medio_npj REAL,
                notificacoes_salvas INTEGER,
                ciencias_registradas INTEGER,
                andamentos_capturados INTEGER,
                documentos_baixados INTEGER,
                npjs_sucesso INTEGER,
                npjs_falha INTEGER
            )
            """)
            print(f"[OK] Banco de dados '{DB_NOME}' verificado com sucesso.")
    except sqlite3.Error as e:
        logging.error(f"ERRO ao inicializar o banco de dados: {e}", exc_info=True)
        raise

def resetar_notificacoes_em_erro():
    """Redefine o status de notificações em 'Erro' para 'Pendente'."""
    try:
        with sqlite3.connect(DB_NOME) as conn:
            cursor = conn.cursor()
            query = f"UPDATE {TABELA_NOTIFICACOES} SET status = 'Pendente' WHERE status = 'Erro'"
            cursor.execute(query)
            if cursor.rowcount > 0:
                logging.info(f"{cursor.rowcount} notificações com erro foram resetadas para 'Pendente'.")
    except sqlite3.Error as e:
        logging.error(f"ERRO ao resetar notificações com erro: {e}", exc_info=True)

def salvar_notificacoes(lista_notificacoes: list[dict]) -> int:
    """Salva uma lista de novas notificações, ignorando duplicatas."""
    if not lista_notificacoes:
        return 0
    
    registros_a_inserir = [
        (item['NPJ'], item['tipo_notificacao'], item.get('adverso_principal'), item['data_notificacao'])
        for item in lista_notificacoes
    ]
    
    try:
        with sqlite3.connect(DB_NOME) as conn:
            cursor = conn.cursor()
            query = f"""
            INSERT OR IGNORE INTO {TABELA_NOTIFICACOES} 
            (NPJ, tipo_notificacao, adverso_principal, data_notificacao) 
            VALUES (?, ?, ?, ?)
            """
            cursor.executemany(query, registros_a_inserir)
            return cursor.rowcount
    except sqlite3.Error as e:
        logging.error(f"ERRO ao salvar notificações: {e}", exc_info=True)
        return 0

def obter_npjs_pendentes_por_lote(tamanho_lote: int) -> list[dict]:
    """Busca um lote de NPJs únicos com status 'Pendente'."""
    try:
        with sqlite3.connect(DB_NOME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = f"""
            SELECT NPJ, MAX(data_notificacao) as data_recente_notificacao
            FROM {TABELA_NOTIFICACOES}
            WHERE status = 'Pendente'
            GROUP BY NPJ
            LIMIT ? 
            """
            cursor.execute(query, (tamanho_lote,))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"ERRO ao obter lote de NPJs pendentes: {e}", exc_info=True)
        return []

def contar_pendentes() -> int:
    """Conta o total de NPJs únicos com status 'Pendente'."""
    try:
        with sqlite3.connect(DB_NOME) as conn:
            cursor = conn.cursor()
            query = f"SELECT COUNT(DISTINCT NPJ) FROM {TABELA_NOTIFICACOES} WHERE status = 'Pendente'"
            cursor.execute(query)
            total = cursor.fetchone()[0]
            return total
    except sqlite3.Error as e:
        logging.error(f"ERRO ao contar notificações pendentes: {e}", exc_info=True)
        return 0

def atualizar_notificacoes_de_npj_processado(npj: str, numero_processo: str, andamentos: list[dict], documentos: list[dict]):
    """Atualiza TODAS as notificações 'Pendente' de um NPJ para 'Processado'."""
    try:
        with sqlite3.connect(DB_NOME) as conn:
            cursor = conn.cursor()
            andamentos_json = json.dumps(andamentos, ensure_ascii=False)
            documentos_json = json.dumps(documentos, ensure_ascii=False)
            query = f"""
            UPDATE {TABELA_NOTIFICACOES} 
            SET numero_processo = ?, andamentos = ?, documentos = ?, status = 'Processado'
            WHERE NPJ = ? AND status = 'Pendente'
            """
            cursor.execute(query, (numero_processo, andamentos_json, documentos_json, npj))
    except sqlite3.Error as e:
        logging.error(f"ERRO ao atualizar NPJ {npj} para 'Processado': {e}", exc_info=True)

def marcar_npj_como_erro(npj: str):
    """Marca TODAS as notificações 'Pendente' de um NPJ como 'Erro'."""
    try:
        with sqlite3.connect(DB_NOME) as conn:
            cursor = conn.cursor()
            query = f"UPDATE {TABELA_NOTIFICACOES} SET status = 'Erro' WHERE NPJ = ? AND status = 'Pendente'"
            cursor.execute(query, (npj,))
    except sqlite3.Error as e:
        logging.error(f"ERRO ao marcar NPJ {npj} como erro: {e}", exc_info=True)

def salvar_log_execucao(log_data: dict):
    """Salva um registro de log no banco de dados."""
    try:
        with sqlite3.connect(DB_NOME) as conn:
            cursor = conn.cursor()
            colunas = ', '.join(log_data.keys())
            placeholders = ', '.join(['?'] * len(log_data))
            query = f"INSERT INTO {TABELA_LOGS} ({colunas}) VALUES ({placeholders})"
            cursor.execute(query, list(log_data.values()))
    except sqlite3.Error as e:
        logging.error(f"ERRO ao salvar log de execução: {e}", exc_info=True)

