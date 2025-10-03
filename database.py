# arquivo: database.py
import sqlite3
import json
import logging
from datetime import datetime
import os
from typing import List, Dict

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
diretorio_base = os.path.abspath(os.path.join(os.path.dirname(__file__)))
DB_NOME = os.path.join(diretorio_base, "rpa_refatorado.db")

TABELA_NOTIFICACOES = "notificacoes"
TABELA_LOGS = "logs_execucao"
TABELA_USUARIOS = "usuarios" # Adicionado para o futuro painel

def _executar_migracoes(conn):
    """Aplica migrações de schema no banco de dados para garantir compatibilidade."""
    cursor = conn.cursor()
    
    try:
        colunas_notificacoes = [desc[1] for desc in cursor.execute(f"PRAGMA table_info({TABELA_NOTIFICACOES})").fetchall()]

        if 'id_processo_portal' not in colunas_notificacoes:
            logging.info(f"Aplicando migração: Adicionando 'id_processo_portal' à tabela '{TABELA_NOTIFICACOES}'...")
            cursor.execute(f"ALTER TABLE {TABELA_NOTIFICACOES} ADD COLUMN id_processo_portal TEXT")
        
        # --- NOVAS MIGRAÇÕES PARA AUDITORIA ---
        if 'data_processamento' not in colunas_notificacoes:
            logging.info(f"Aplicando migração: Adicionando 'data_processamento' à tabela '{TABELA_NOTIFICACOES}'...")
            cursor.execute(f"ALTER TABLE {TABELA_NOTIFICACOES} ADD COLUMN data_processamento TEXT")

        if 'detalhes_erro' not in colunas_notificacoes:
            logging.info(f"Aplicando migração: Adicionando 'detalhes_erro' à tabela '{TABELA_NOTIFICACOES}'...")
            cursor.execute(f"ALTER TABLE {TABELA_NOTIFICACOES} ADD COLUMN detalhes_erro TEXT")

    except sqlite3.Error as e:
        if "no such table" not in str(e):
            logging.error(f"Falha ao verificar/aplicar migração na tabela de notificações: {e}")

def inicializar_banco():
    """Garante que o banco de dados e as tabelas necessárias existam e estejam atualizados."""
    try:
        with sqlite3.connect(DB_NOME) as conn:
            cursor = conn.cursor()
            
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
                documentos TEXT,
                id_processo_portal TEXT,
                data_processamento TEXT,
                detalhes_erro TEXT
            )
            """)
            cursor.execute(f"""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_notificacao_unica
            ON {TABELA_NOTIFICACOES} (NPJ, tipo_notificacao, data_notificacao)
            """)
            
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABELA_LOGS} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                duracao_total REAL,
                notificacoes_salvas INTEGER,
                ciencias_registradas INTEGER,
                andamentos INTEGER,
                documentos INTEGER,
                npjs_sucesso INTEGER,
                npjs_falha INTEGER
            )
            """)
            
            _executar_migracoes(conn)

            print(f"[OK] Banco de dados '{DB_NOME}' verificado com sucesso.")
    except sqlite3.Error as e:
        logging.error(f"ERRO ao inicializar o banco de dados: {e}", exc_info=True)
        raise

def resetar_notificacoes_em_processamento_ou_erro():
    """Reseta o status de notificações que falharam ou foram interrompidas em uma execução anterior."""
    try:
        with sqlite3.connect(DB_NOME) as conn:
            cursor = conn.cursor()
            # Limpa os detalhes de erro antigos ao resetar
            cursor.execute(
                f"""UPDATE {TABELA_NOTIFICACOES} 
                   SET status = 'Pendente', detalhes_erro = NULL, data_processamento = NULL
                   WHERE status IN ('Em Processamento', 'Erro', 'Erro - Data Inválida')"""
            )
            if cursor.rowcount > 0:
                logging.info(f"{cursor.rowcount} notificações com status de erro ou em processamento foram resetadas para 'Pendente'.")
    except sqlite3.Error as e:
        logging.error(f"ERRO ao resetar status de notificações: {e}", exc_info=True)

def validar_e_marcar_notificacoes_sem_data():
    """Identifica notificações pendentes sem data e as marca com um erro específico."""
    try:
        with sqlite3.connect(DB_NOME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""UPDATE {TABELA_NOTIFICACOES} 
                   SET status = 'Erro - Data Inválida', detalhes_erro = 'A notificação foi capturada sem uma data válida.'
                   WHERE status = 'Pendente' AND (data_notificacao IS NULL OR data_notificacao = '')"""
            )
            if cursor.rowcount > 0:
                logging.warning(f"{cursor.rowcount} notificações pendentes sem data foram marcadas como 'Erro - Data Inválida'.")
    except sqlite3.Error as e:
        logging.error(f"ERRO ao validar notificações sem data: {e}", exc_info=True)


def salvar_notificacoes(lista_notificacoes: list[dict]) -> int:
    """Salva uma lista de notificações no banco, ignorando duplicatas."""
    salvas_com_sucesso = 0
    for notificacao in lista_notificacoes:
        try:
            with sqlite3.connect(DB_NOME) as conn:
                cursor = conn.cursor()
                colunas = ', '.join(notificacao.keys())
                placeholders = ', '.join(['?'] * len(notificacao))
                query = f"INSERT OR IGNORE INTO {TABELA_NOTIFICACOES} ({colunas}) VALUES ({placeholders})"
                cursor.execute(query, list(notificacao.values()))
                if cursor.rowcount > 0:
                    salvas_com_sucesso += 1
        except sqlite3.Error as e:
            logging.error(f"ERRO ao salvar notificação para o NPJ {notificacao.get('NPJ')}: {e}")
    return salvas_com_sucesso

def obter_npjs_pendentes_por_lote(tamanho_lote: int) -> List[Dict]:
    """Obtém um lote de grupos (NPJ, data) pendentes e os marca como 'Em Processamento'."""
    try:
        with sqlite3.connect(DB_NOME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Busca grupos únicos de (NPJ, data) que tenham pelo menos uma notificação pendente
            query_grupos = f"""
                SELECT DISTINCT NPJ, data_notificacao 
                FROM {TABELA_NOTIFICACOES} 
                WHERE status = 'Pendente'
                LIMIT {tamanho_lote}
            """
            cursor.execute(query_grupos)
            grupos_pendentes = [dict(row) for row in cursor.fetchall()]

            if not grupos_pendentes:
                return []
            
            # Marca todos os itens desses grupos como 'Em Processamento'
            for grupo in grupos_pendentes:
                cursor.execute(
                    f"UPDATE {TABELA_NOTIFICACOES} SET status = 'Em Processamento' WHERE NPJ = ? AND data_notificacao = ? AND status = 'Pendente'",
                    (grupo['NPJ'], grupo['data_notificacao'])
                )
            
            return grupos_pendentes
            
    except sqlite3.Error as e:
        logging.error(f"ERRO ao obter lote de NPJs pendentes: {e}", exc_info=True)
        return []

def contar_pendentes() -> int:
    """Conta quantos grupos únicos de (NPJ, data) ainda estão pendentes."""
    try:
        with sqlite3.connect(DB_NOME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(DISTINCT NPJ || '-' || data_notificacao) FROM {TABELA_NOTIFICACOES} WHERE status = 'Pendente'")
            return cursor.fetchone()[0]
    except sqlite3.Error as e:
        logging.error(f"ERRO ao contar NPJs pendentes: {e}", exc_info=True)
        return 0

def atualizar_notificacoes_de_npj_processado(npj: str, data_notificacao: str, numero_processo: str, andamentos: list[dict], documentos: list[dict]):
    """Atualiza as notificações de um grupo (NPJ, data) como 'Processado', salvando os dados extraídos."""
    try:
        with sqlite3.connect(DB_NOME) as conn:
            cursor = conn.cursor()
            timestamp_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            cursor.execute(
                f"""
                UPDATE {TABELA_NOTIFICACOES}
                SET status = 'Processado',
                    numero_processo = ?,
                    andamentos = ?,
                    documentos = ?,
                    data_processamento = ?,
                    detalhes_erro = NULL
                WHERE NPJ = ? AND data_notificacao = ? AND status = 'Em Processamento'
                """,
                (numero_processo, json.dumps(andamentos), json.dumps(documentos), timestamp_atual, npj, data_notificacao)
            )
    except sqlite3.Error as e:
        logging.error(f"ERRO ao atualizar NPJ {npj} ({data_notificacao}) como processado: {e}", exc_info=True)

def marcar_npj_como_erro(npj: str, data_notificacao: str, detalhes_erro: str):
    """Marca as notificações de um grupo (NPJ, data) como 'Erro', salvando o motivo."""
    try:
        with sqlite3.connect(DB_NOME) as conn:
            cursor = conn.cursor()
            timestamp_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            cursor.execute(
                f"""UPDATE {TABELA_NOTIFICACOES} 
                   SET status = 'Erro', detalhes_erro = ?, data_processamento = ?
                   WHERE NPJ = ? AND data_notificacao = ? AND status = 'Em Processamento'""",
                (detalhes_erro, timestamp_atual, npj, data_notificacao)
            )
    except sqlite3.Error as e:
        logging.error(f"ERRO ao marcar NPJ {npj} ({data_notificacao}) como erro: {e}", exc_info=True)

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

