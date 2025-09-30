# arquivo: database.py
import sqlite3
import json
import logging
from datetime import datetime
import os
from typing import List, Dict, Any

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
diretorio_base = os.path.abspath(os.path.join(os.path.dirname(__file__)))
DB_NOME = os.path.join(diretorio_base, "rpa_refatorado.db")

TABELA_NOTIFICACOES = "notificacoes"
TABELA_LOGS = "logs_execucao"
TABELA_USUARIOS = "usuarios"


def _coluna_existe(cursor, tabela: str, coluna: str) -> bool:
    """Verifica se uma coluna já existe em uma tabela."""
    try:
        cursor.execute(f"PRAGMA table_info({tabela})")
        colunas_existentes = [desc[1] for desc in cursor.fetchall()]
        return coluna in colunas_existentes
    except sqlite3.Error:
        return False

def _executar_migracoes(conn):
    """Aplica migrações de schema no banco de dados para garantir compatibilidade."""
    cursor = conn.cursor()
    
    try:
        if _coluna_existe(cursor, TABELA_LOGS, 'andamentos_capturados'):
            logging.info(f"Aplicando migração: Renomeando coluna 'andamentos_capturados' para 'andamentos'...")
            cursor.execute(f"ALTER TABLE {TABELA_LOGS} RENAME COLUMN andamentos_capturados TO andamentos")
        
        if _coluna_existe(cursor, TABELA_LOGS, 'documentos_baixados'):
            logging.info(f"Aplicando migração: Renomeando coluna 'documentos_baixados' para 'documentos'...")
            cursor.execute(f"ALTER TABLE {TABELA_LOGS} RENAME COLUMN documentos_baixados TO documentos")

    except sqlite3.Error as e:
        if "no such table" not in str(e):
            logging.error(f"Falha ao verificar/aplicar migração na tabela de logs: {e}")

    try:
        if not _coluna_existe(cursor, TABELA_NOTIFICACOES, 'id_processo_portal'):
            logging.info(f"Aplicando migração: Adicionando 'id_processo_portal' à tabela '{TABELA_NOTIFICACOES}'...")
            cursor.execute(f"ALTER TABLE {TABELA_NOTIFICACOES} ADD COLUMN id_processo_portal TEXT")
        
        if not _coluna_existe(cursor, TABELA_NOTIFICACOES, 'usuario_responsavel_id'):
            logging.info(f"Aplicando migração: Adicionando 'usuario_responsavel_id' à tabela '{TABELA_NOTIFICACOES}'...")
            cursor.execute(f"ALTER TABLE {TABELA_NOTIFICACOES} ADD COLUMN usuario_responsavel_id INTEGER REFERENCES {TABELA_USUARIOS}(id)")

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

            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABELA_USUARIOS} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_completo TEXT NOT NULL,
                login TEXT NOT NULL UNIQUE,
                senha TEXT NOT NULL,
                perfil TEXT NOT NULL CHECK(perfil IN ('admin', 'usuario')) DEFAULT 'usuario',
                ativo INTEGER NOT NULL CHECK(ativo IN (0, 1)) DEFAULT 1
            )
            """)
            
            _executar_migracoes(conn)

            print(f"[OK] Banco de dados '{DB_NOME}' verificado com sucesso.")
    except sqlite3.Error as e:
        logging.error(f"ERRO ao inicializar o banco de dados: {e}", exc_info=True)
        raise

def resetar_notificacoes_em_processamento_ou_erro():
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
    try:
        with sqlite3.connect(DB_NOME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(DISTINCT NPJ) FROM {TABELA_NOTIFICACOES} WHERE status = 'Pendente'")
            return cursor.fetchone()[0]
    except sqlite3.Error as e:
        logging.error(f"ERRO ao contar NPJs pendentes: {e}", exc_info=True)
        return 0

def atualizar_notificacoes_de_npj_processado(npj: str, numero_processo: str, andamentos: list[dict], documentos: list[dict]):
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
    if not ids:
        return {'updated': 0, 'deleted': 0}

    conn = None 
    try:
        conn = sqlite3.connect(DB_NOME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("BEGIN TRANSACTION;")

        placeholders = ', '.join(['?'] * len(ids))
        
        query_select = f"SELECT id, NPJ, tipo_notificacao FROM {TABELA_NOTIFICACOES} WHERE id IN ({placeholders})"
        cursor.execute(query_select, ids)
        notificacoes_para_processar = [dict(row) for row in cursor.fetchall()]

        grupos_para_consolidar = {}
        for n in notificacoes_para_processar:
            chave = (n['NPJ'], n['tipo_notificacao'])
            if chave not in grupos_para_consolidar:
                grupos_para_consolidar[chave] = []
            grupos_para_consolidar[chave].append(n['id'])

        ids_para_deletar = []
        ids_para_atualizar = []

        for grupo_ids in grupos_para_consolidar.values():
            if not grupo_ids:
                continue
            
            id_para_manter = grupo_ids[0]
            ids_para_atualizar.append(id_para_manter)
            
            if len(grupo_ids) > 1:
                ids_para_deletar.extend(grupo_ids[1:])
        
        updated_count = 0
        if ids_para_atualizar:
            placeholders_update = ', '.join(['?'] * len(ids_para_atualizar))
            query_update = f"UPDATE {TABELA_NOTIFICACOES} SET data_notificacao = ? WHERE id IN ({placeholders_update})"
            cursor.execute(query_update, [nova_data] + ids_para_atualizar)
            updated_count = cursor.rowcount

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

def criar_usuario(nome_completo: str, login: str, hash_senha: str, perfil: str = 'usuario'):
    sql = f"INSERT INTO {TABELA_USUARIOS} (nome_completo, login, senha, perfil) VALUES (?, ?, ?, ?)"
    try:
        with sqlite3.connect(DB_NOME) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (nome_completo, login, hash_senha, perfil))
            conn.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        logging.error(f"Erro: O login '{login}' já existe.")
        return None
    except sqlite3.Error as e:
        logging.error(f"Erro ao criar usuário: {e}")
        return None

def listar_usuarios():
    sql = f"SELECT id, nome_completo, login, perfil, ativo FROM {TABELA_USUARIOS} ORDER BY nome_completo"
    try:
        with sqlite3.connect(DB_NOME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql)
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Erro ao listar usuários: {e}")
        return []

def obter_notificacoes_para_distribuir() -> List[Dict[str, Any]]:
    sql = f"SELECT id, NPJ FROM {TABELA_NOTIFICACOES} WHERE status = 'Processado' AND usuario_responsavel_id IS NULL"
    try:
        with sqlite3.connect(DB_NOME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql)
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Erro ao obter notificações para distribuir: {e}")
        return []

def obter_usuarios_ativos_para_distribuicao() -> List[Dict[str, Any]]:
    sql = f"SELECT id, nome_completo FROM {TABELA_USUARIOS} WHERE perfil = 'usuario' AND ativo = 1 ORDER BY id"
    try:
        with sqlite3.connect(DB_NOME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql)
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Erro ao obter usuários ativos: {e}")
        return []

def atribuir_notificacao_a_usuario(id_notificacao: int, id_usuario: int):
    sql = f"UPDATE {TABELA_NOTIFICACOES} SET usuario_responsavel_id = ? WHERE id = ?"
    try:
        with sqlite3.connect(DB_NOME) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (id_usuario, id_notificacao))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Erro ao atribuir notificação {id_notificacao} ao usuário {id_usuario}: {e}")

# --- NOVAS FUNÇÕES PARA O SERVIDOR WEB ---
def validar_usuario(login: str, hash_senha: str) -> Dict[str, Any] or None:
    """Busca um usuário ativo pelo login e hash da senha."""
    sql = f"SELECT id, nome_completo, login, perfil FROM {TABELA_USUARIOS} WHERE login = ? AND senha = ? AND ativo = 1"
    try:
        with sqlite3.connect(DB_NOME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql, (login, hash_senha))
            user_data = cursor.fetchone()
            return dict(user_data) if user_data else None
    except sqlite3.Error as e:
        logging.error(f"Erro ao validar usuário: {e}")
        return None

def obter_notificacoes_por_usuario(id_usuario: int) -> List[Dict[str, Any]]:
    """Obtém todas as notificações atribuídas a um usuário específico."""
    sql = f"SELECT * FROM {TABELA_NOTIFICACOES} WHERE usuario_responsavel_id = ? ORDER BY data_criacao DESC"
    try:
        with sqlite3.connect(DB_NOME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql, (id_usuario,))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Erro ao obter notificações para o usuário {id_usuario}: {e}")
        return []

