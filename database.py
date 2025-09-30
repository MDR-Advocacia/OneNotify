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

def _executar_migracoes(conn):
    """Aplica migrações de schema no banco de dados para garantir compatibilidade."""
    cursor = conn.cursor()
    
    # --- Migração para a tabela de logs ---
    try:
        colunas_logs = [desc[1] for desc in cursor.execute(f"PRAGMA table_info({TABELA_LOGS})").fetchall()]

        if 'andamentos_capturados' in colunas_logs:
            logging.info(f"Aplicando migração: Renomeando coluna 'andamentos_capturados' para 'andamentos'...")
            cursor.execute(f"ALTER TABLE {TABELA_LOGS} RENAME COLUMN andamentos_capturados TO andamentos")
        
        if 'documentos_baixados' in colunas_logs:
            logging.info(f"Aplicando migração: Renomeando coluna 'documentos_baixados' para 'documentos'...")
            cursor.execute(f"ALTER TABLE {TABELA_LOGS} RENAME COLUMN documentos_baixados TO documentos")

    except sqlite3.Error as e:
        if "no such table" not in str(e):
            logging.error(f"Falha ao verificar/aplicar migração na tabela de logs: {e}")

    # --- Migração para a tabela de notificações ---
    try:
        colunas_notificacoes = [desc[1] for desc in cursor.execute(f"PRAGMA table_info({TABELA_NOTIFICACOES})").fetchall()]
        if 'id_processo_portal' not in colunas_notificacoes:
            logging.info(f"Aplicando migração: Adicionando 'id_processo_portal' à tabela '{TABELA_NOTIFICACOES}'...")
            cursor.execute(f"ALTER TABLE {TABELA_NOTIFICACOES} ADD COLUMN id_processo_portal TEXT")

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
                id_processo_portal TEXT
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
                tempo_medio_npj REAL,
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

# ... (outras funções do database.py permanecem iguais) ...

def resetar_notificacoes_em_processamento_ou_erro():
    """Reseta o status de notificações que falharam em uma execução anterior."""
    try:
        with sqlite3.connect(DB_NOME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE {TABELA_NOTIFICACOES} SET status = 'Pendente' WHERE status IN ('Em Processamento', 'Erro')"
            )
            if cursor.rowcount > 0:
                logging.info(f"{cursor.rowcount} notificações com status 'Erro' ou 'Em Processamento' foram resetadas para 'Pendente'.")
    except sqlite3.Error as e:
        logging.error(f"ERRO ao resetar status de notificações: {e}", exc_info=True)

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
    """Obtém um lote de NPJs únicos com status 'Pendente' e os marca como 'Em Processamento'."""
    try:
        with sqlite3.connect(DB_NOME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(f"SELECT DISTINCT NPJ FROM {TABELA_NOTIFICACOES} WHERE status = 'Pendente' LIMIT {tamanho_lote}")
            npjs_pendentes = [row['NPJ'] for row in cursor.fetchall()]

            if not npjs_pendentes:
                return []

            placeholders = ', '.join(['?'] * len(npjs_pendentes))
            cursor.execute(f"UPDATE {TABELA_NOTIFICACOES} SET status = 'Em Processamento' WHERE NPJ IN ({placeholders})", npjs_pendentes)
            
            query = f"""
                SELECT
                    NPJ,
                    MAX(data_notificacao) as data_recente_notificacao
                FROM {TABELA_NOTIFICACOES}
                WHERE NPJ IN ({placeholders})
                GROUP BY NPJ
            """
            cursor.execute(query, npjs_pendentes)
            lote_para_processar = [dict(row) for row in cursor.fetchall()]
            return lote_para_processar
            
    except sqlite3.Error as e:
        logging.error(f"ERRO ao obter lote de NPJs pendentes: {e}", exc_info=True)
        return []

def contar_pendentes() -> int:
    """Conta quantos NPJs únicos ainda estão pendentes."""
    try:
        with sqlite3.connect(DB_NOME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(DISTINCT NPJ) FROM {TABELA_NOTIFICACOES} WHERE status = 'Pendente'")
            return cursor.fetchone()[0]
    except sqlite3.Error as e:
        logging.error(f"ERRO ao contar NPJs pendentes: {e}", exc_info=True)
        return 0

def atualizar_notificacoes_de_npj_processado(npj: str, numero_processo: str, andamentos: list[dict], documentos: list[dict]):
    """Atualiza todas as notificações de um NPJ como 'Processado', salvando os dados extraídos."""
    try:
        with sqlite3.connect(DB_NOME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                UPDATE {TABELA_NOTIFICACOES}
                SET status = 'Processado',
                    numero_processo = ?,
                    andamentos = ?,
                    documentos = ?
                WHERE NPJ = ? AND status = 'Em Processamento'
                """,
                (numero_processo, json.dumps(andamentos), json.dumps(documentos), npj)
            )
    except sqlite3.Error as e:
        logging.error(f"ERRO ao atualizar NPJ {npj} como processado: {e}", exc_info=True)

def marcar_npj_como_erro(npj: str):
    """Marca todas as notificações de um NPJ como 'Erro'."""
    try:
        with sqlite3.connect(DB_NOME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE {TABELA_NOTIFICACOES} SET status = 'Erro' WHERE NPJ = ? AND status = 'Em Processamento'",
                (npj,)
            )
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

def atualizar_status_de_notificacoes_por_ids(ids: list[int], novo_status: str) -> int:
    """Atualiza o status de uma lista de notificações com base em seus IDs."""
    if not ids:
        return 0
    try:
        with sqlite3.connect(DB_NOME) as conn:
            cursor = conn.cursor()
            placeholders = ', '.join(['?'] * len(ids))
            query = f"UPDATE {TABELA_NOTIFICACOES} SET status = ? WHERE id IN ({placeholders})"
            
            params = [novo_status] + ids
            cursor.execute(query, params)
            return cursor.rowcount
    except sqlite3.Error as e:
        logging.error(f"ERRO ao atualizar status em massa para os IDs {ids}: {e}", exc_info=True)
        raise e

def corrigir_e_consolidar_datas_por_ids(ids: list[int], nova_data: str) -> dict:
    """
    Corrige a data de notificações selecionadas e remove duplicatas que possam surgir.
    Retorna um dicionário com o número de registros atualizados e deletados.
    """
    if not ids:
        return {'updated': 0, 'deleted': 0}

    conn = None # Garante que a variável conn exista fora do try
    try:
        conn = sqlite3.connect(DB_NOME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("BEGIN TRANSACTION;")

        placeholders = ', '.join(['?'] * len(ids))
        
        # 1. Busca todas as notificações selecionadas para processá-las em memória.
        query_select = f"SELECT id, NPJ, tipo_notificacao FROM {TABELA_NOTIFICACOES} WHERE id IN ({placeholders})"
        cursor.execute(query_select, ids)
        notificacoes_para_processar = [dict(row) for row in cursor.fetchall()]

        # 2. Agrupa as notificações pela chave única (NPJ, tipo_notificacao).
        grupos_para_consolidar = {}
        for n in notificacoes_para_processar:
            chave = (n['NPJ'], n['tipo_notificacao'])
            if chave not in grupos_para_consolidar:
                grupos_para_consolidar[chave] = []
            grupos_para_consolidar[chave].append(n['id'])

        # 3. Para cada grupo, decide quem vive e quem é excluído.
        ids_para_deletar = []
        ids_para_atualizar = []

        for grupo_ids in grupos_para_consolidar.values():
            if not grupo_ids:
                continue
            
            # Mantém o primeiro ID da lista, e marca os outros para exclusão.
            id_para_manter = grupo_ids[0]
            ids_para_atualizar.append(id_para_manter)
            
            if len(grupo_ids) > 1:
                ids_para_deletar.extend(grupo_ids[1:])
        
        # 4. Executa a atualização da data nos registros que serão mantidos.
        updated_count = 0
        if ids_para_atualizar:
            placeholders_update = ', '.join(['?'] * len(ids_para_atualizar))
            query_update = f"UPDATE {TABELA_NOTIFICACOES} SET data_notificacao = ? WHERE id IN ({placeholders_update})"
            cursor.execute(query_update, [nova_data] + ids_para_atualizar)
            updated_count = cursor.rowcount

        # 5. Executa a exclusão dos registros redundantes.
        deleted_count = 0
        if ids_para_deletar:
            placeholders_delete = ', '.join(['?'] * len(ids_para_deletar))
            query_delete = f"DELETE FROM {TABELA_NOTIFICACOES} WHERE id IN ({placeholders_delete})"
            cursor.execute(query_delete, ids_para_deletar)
            deleted_count = cursor.rowcount

        conn.commit()

        return {'updated': updated_count, 'deleted': deleted_count}

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logging.error(f"ERRO ao consolidar datas para os IDs {ids}: {e}", exc_info=True)
        raise e
    finally:
        if conn:
            conn.close()

