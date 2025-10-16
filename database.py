import os
import sqlite3
import json
import logging
from typing import List, Dict
from datetime import datetime, timedelta

# --- Configuração ---
DATABASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'rpa_refatorado.db'))
MAX_TENTATIVAS_PORTAL = 3 # Define o limite de tentativas para erros de portal

# --- Funções Auxiliares de Migração ---
def _executar_migracoes(conn):
    """Aplica migrações de schema no banco de dados de forma segura."""
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(notificacoes)")
    tabela_notificacoes_cols = [desc[1] for desc in cursor.fetchall()]
    colunas_para_adicionar = {
        'responsavel': 'TEXT',
        'data_processamento': 'TEXT',
        'detalhes_erro': 'TEXT',
        'origem': 'TEXT DEFAULT "onenotify"',
        'gerou_tarefa': 'INTEGER DEFAULT 0',
        'tentativas': 'INTEGER DEFAULT 0',
        'polo': 'TEXT' # NOVA COLUNA ADICIONADA
    }
    for col, tipo in colunas_para_adicionar.items():
        if col not in tabela_notificacoes_cols:
            logging.info(f"Aplicando migração: Adicionando coluna '{col}' à tabela 'notificacoes'...")
            cursor.execute(f"ALTER TABLE notificacoes ADD COLUMN {col} {tipo}")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE
        )
    """)
    conn.commit()

# --- Funções Principais do Banco de Dados ---
def inicializar_banco():
    """Garante que o banco de dados e as tabelas necessárias existam e estejam atualizados."""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS notificacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, NPJ TEXT NOT NULL, tipo_notificacao TEXT NOT NULL,
                data_notificacao TEXT NOT NULL, adverso_principal TEXT, status TEXT NOT NULL DEFAULT 'Pendente',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP, numero_processo TEXT, andamentos TEXT,
                documentos TEXT, id_processo_portal TEXT
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS logs_execucao (
                id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, duracao_total REAL, 
                notificacoes_salvas INTEGER, ciencias_registradas INTEGER, andamentos INTEGER, 
                documentos INTEGER, npjs_sucesso INTEGER, npjs_falha INTEGER
            )
            """)
            _executar_migracoes(conn)
            logging.info(f"Banco de dados '{DATABASE_PATH}' verificado e atualizado com sucesso.")
    except sqlite3.Error as e:
        logging.error(f"ERRO CRÍTICO ao inicializar o banco de dados: {e}", exc_info=True)
        raise

def resetar_notificacoes_em_processamento():
    """Reseta o status de notificações que foram interrompidas durante o processamento."""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE notificacoes SET status = 'Pendente' WHERE status = 'Em Processamento'")
            if cursor.rowcount > 0:
                logging.info(f"{cursor.rowcount} notificações 'Em Processamento' foram resetadas para 'Pendente'.")
    except sqlite3.Error as e:
        logging.error(f"ERRO ao resetar status de notificações: {e}", exc_info=True)

def resetar_erros_de_portal_antigos():
    """Verifica notificações com 'Erro_Portal' e as libera para nova tentativa se tiverem mais de 24 horas."""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, data_processamento FROM notificacoes WHERE status = 'Erro_Portal'")
            tarefas_com_erro = cursor.fetchall()

            if not tarefas_com_erro:
                return

            logging.info(f"Verificando {len(tarefas_com_erro)} tarefa(s) com 'Erro_Portal' para possível reprocessamento...")
            limite_tempo = datetime.now() - timedelta(hours=24)
            ids_para_resetar = []

            for tarefa in tarefas_com_erro:
                try:
                    data_proc = datetime.strptime(tarefa['data_processamento'], '%d/%m/%Y %H:%M:%S')
                    if data_proc < limite_tempo:
                        ids_para_resetar.append((tarefa['id'],))
                except (ValueError, TypeError):
                    ids_para_resetar.append((tarefa['id'],))

            if ids_para_resetar:
                cursor.executemany("UPDATE notificacoes SET status = 'Pendente' WHERE id = ?", ids_para_resetar)
                conn.commit()
                logging.info(f"{len(ids_para_resetar)} tarefa(s) com erro de portal foram liberadas para nova tentativa.")

    except sqlite3.Error as e:
        logging.error(f"ERRO ao reprocessar erros de portal antigos: {e}", exc_info=True)

def salvar_notificacoes(lista_notificacoes: list[dict]) -> int:
    """Salva uma lista de notificações no banco, ignorando duplicatas."""
    salvas = 0
    for n in lista_notificacoes:
        if not n.get('data_notificacao'):
            logging.warning(f"Notificação para o NPJ {n.get('NPJ')} ignorada por não ter data.")
            continue
        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cols = ', '.join(n.keys())
                placeholders = ', '.join(['?'] * len(n))
                query = f"INSERT OR IGNORE INTO notificacoes ({cols}) VALUES ({placeholders})"
                cursor.execute(query, list(n.values()))
                if cursor.rowcount > 0:
                    salvas += 1
        except sqlite3.Error as e:
            logging.error(f"ERRO ao salvar notificação para o NPJ {n.get('NPJ')}: {e}")
    return salvas

def buscar_lote_para_processamento(tamanho_lote: int) -> List[Dict]:
    """Obtém um lote de tarefas (NPJ + data) únicas e marca-as como 'Em Processamento'."""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT NPJ, data_notificacao, MAX(origem) as origem
                FROM notificacoes 
                WHERE status = 'Pendente' AND data_notificacao IS NOT NULL
                GROUP BY NPJ, data_notificacao
                ORDER BY data_notificacao, NPJ 
                LIMIT ?
            """, (tamanho_lote,))
            tarefas = [dict(row) for row in cursor.fetchall()]
            if not tarefas:
                return []
            for tarefa in tarefas:
                conn.execute(
                    "UPDATE notificacoes SET status = 'Em Processamento' WHERE NPJ = ? AND data_notificacao = ? AND status = 'Pendente'",
                    (tarefa['NPJ'], tarefa['data_notificacao'])
                )
            conn.commit()
            return tarefas
    except sqlite3.Error as e:
        logging.error(f"ERRO ao obter lote de tarefas pendentes: {e}", exc_info=True)
        return []

def contar_pendentes() -> int:
    """Conta quantas tarefas (grupos NPJ + data) únicas ainda estão pendentes."""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(DISTINCT NPJ || data_notificacao) FROM notificacoes WHERE status = 'Pendente' AND data_notificacao IS NOT NULL")
            return cursor.fetchone()[0]
    except sqlite3.Error as e:
        logging.error(f"ERRO ao contar tarefas pendentes: {e}", exc_info=True)
        return 0

def get_next_user() -> str | None:
    """Busca o próximo usuário para atribuição de tarefa (round-robin)."""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            last_assigned = conn.execute("SELECT responsavel FROM notificacoes WHERE responsavel IS NOT NULL ORDER BY data_processamento DESC LIMIT 1").fetchone()
            all_users = conn.execute("SELECT nome FROM usuarios ORDER BY nome").fetchall()
            if not all_users:
                return None
            user_list = [user[0] for user in all_users]
            if not last_assigned or last_assigned[0] not in user_list:
                return user_list[0]
            try:
                last_index = user_list.index(last_assigned[0])
                next_index = (last_index + 1) % len(user_list)
                return user_list[next_index]
            except ValueError:
                return user_list[0]
    except sqlite3.Error as e:
        logging.error(f"ERRO ao buscar próximo usuário: {e}")
        return None

def atualizar_notificacoes_processadas(npj, data, numero_processo, andamentos, documentos, data_processamento, responsavel, status='Processado', polo=None):
    """Atualiza as notificações de uma tarefa como 'Processado' ou 'Migrado' e adiciona o polo."""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.execute("""
                UPDATE notificacoes
                SET status = ?, numero_processo = ?, andamentos = ?, documentos = ?,
                    data_processamento = ?, responsavel = ?, detalhes_erro = NULL, tentativas = 0,
                    polo = ?
                WHERE NPJ = ? AND data_notificacao = ? AND status = 'Em Processamento'
            """, (status, numero_processo, json.dumps(andamentos), json.dumps(documentos), data_processamento, responsavel, polo, npj, data))
    except sqlite3.Error as e:
        logging.error(f"ERRO ao atualizar tarefa {npj}-{data} como processada: {e}")

def marcar_tarefa_como_erro(npj, data, motivo, data_processamento, tipo_erro: str):
    """Marca as notificações de uma tarefa com um status de erro específico e controla as tentativas."""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT tentativas FROM notificacoes WHERE NPJ = ? AND data_notificacao = ? LIMIT 1", (npj, data))
            resultado = cursor.fetchone()
            tentativas_atuais = resultado[0] if resultado and resultado[0] is not None else 0

            novo_status = "Erro" # Default
            
            if tipo_erro == 'permanente':
                novo_status = 'Erro_Permanente'
                tentativas_atuais += 1
            
            elif tipo_erro == 'portal':
                tentativas_atuais += 1
                if tentativas_atuais >= MAX_TENTATIVAS_PORTAL:
                    novo_status = 'Requer_Atencao'
                    logging.warning(f"Tarefa {npj} atingiu o limite de {MAX_TENTATIVAS_PORTAL} tentativas. Status alterado para 'Requer_Atencao'.")
                else:
                    novo_status = 'Erro_Portal'
            
            cursor.execute("""
                UPDATE notificacoes SET status = ?, detalhes_erro = ?, data_processamento = ?, tentativas = ?
                WHERE NPJ = ? AND data_notificacao = ? AND status = 'Em Processamento'
            """, (novo_status, motivo, data_processamento, tentativas_atuais, npj, data))
    except sqlite3.Error as e:
        logging.error(f"ERRO ao marcar tarefa {npj}-{data} como erro: {e}")

def salvar_log_execucao(log_data: dict):
    """Salva um registro de log no banco de dados."""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cols = ', '.join(log_data.keys())
            placeholders = ', '.join(['?'] * len(log_data))
            conn.execute(f"INSERT INTO logs_execucao ({cols}) VALUES ({placeholders})", list(log_data.values()))
    except sqlite3.Error as e:
        logging.error(f"ERRO ao salvar log de execução: {e}", exc_info=True)

