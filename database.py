# arquivo: database.py
import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_NOME = "rpa.db"
TABELA_NOTIFICACOES = "notificacoes_processos"
TABELA_LOGS = "logs_execucao"
TABELA_USUARIOS = "usuarios"

def inicializar_banco():
    """
    Garante que o banco de dados e as tabelas necessárias existam,
    realizando migrações de schema se necessário para adicionar colunas faltantes.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_NOME)
        cursor = conn.cursor()
        
        # --- Tabela de Usuários ---
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABELA_USUARIOS} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE
        )
        """)
        
        # --- Tabela de Notificações ---
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABELA_NOTIFICACOES} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            NPJ TEXT NOT NULL,
            tipo_notificacao TEXT NOT NULL,
            data_notificacao TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pendente',
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        try:
            cursor.execute(f"""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_notificacao_unica
            ON {TABELA_NOTIFICACOES} (NPJ, tipo_notificacao, data_notificacao)
            """)
        except sqlite3.OperationalError as e:
            print(f"AVISO: Não foi possível criar o índice de unicidade. Isso pode ocorrer se dados duplicados já existem. Erro: {e}")

        # --- Migração de Schema para Notificações ---
        cursor.execute(f"PRAGMA table_info({TABELA_NOTIFICACOES})")
        colunas_existentes = [row[1] for row in cursor.fetchall()]
        
        colunas_desejadas = {
            "adverso_principal": "TEXT",
            "numero_processo": "TEXT",
            "andamentos": "TEXT",
            "documentos": "TEXT",
            "usuario_id": "INTEGER REFERENCES usuarios(id)"
        }

        for coluna, tipo in colunas_desejadas.items():
            if coluna not in colunas_existentes:
                print(f"INFO: Migrando schema. Adicionando coluna '{coluna}'...")
                cursor.execute(f"ALTER TABLE {TABELA_NOTIFICACOES} ADD COLUMN {coluna} {tipo}")
        
        # --- Tabela de Logs ---
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABELA_LOGS} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            duracao_total REAL,
            tempo_medio_npj REAL,
            notificacoes_salvas INTEGER,
            andamentos_capturados INTEGER,
            documentos_baixados INTEGER,
            npjs_sucesso INTEGER,
            npjs_falha TEXT
        )
        """)
        
        conn.commit()
        print(f"✅ Banco de dados '{DB_NOME}' e tabelas verificados/migrados com sucesso.")
    except sqlite3.Error as e:
        print(f"❌ ERRO ao inicializar o banco de dados: {e}")
    finally:
        if conn:
            conn.close()

# === FUNÇÕES DE USUÁRIOS ===

def listar_usuarios():
    conn = sqlite3.connect(DB_NOME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {TABELA_USUARIOS} ORDER BY nome")
    usuarios = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return usuarios

def adicionar_usuario(nome):
    conn = sqlite3.connect(DB_NOME)
    try:
        cursor = conn.cursor()
        cursor.execute(f"INSERT INTO {TABELA_USUARIOS} (nome) VALUES (?)", (nome,))
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"AVISO: Usuário '{nome}' já existe.")
        return False
    finally:
        conn.close()
    return True

def remover_usuario(usuario_id):
    conn = sqlite3.connect(DB_NOME)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE {TABELA_NOTIFICACOES} SET usuario_id = NULL WHERE usuario_id = ?", (usuario_id,))
    cursor.execute(f"DELETE FROM {TABELA_USUARIOS} WHERE id = ?", (usuario_id,))
    conn.commit()
    conn.close()

# === FUNÇÕES DE NOTIFICAÇÕES (ATUALIZADAS) ===

def criar_notificacoes_de_teste(npjs: list[str]):
    """Cria notificações com status 'Pendente' para fins de teste."""
    if not npjs:
        return 0
    
    conn = sqlite3.connect(DB_NOME)
    cursor = conn.cursor()
    
    data_hoje = datetime.now().strftime('%d/%m/%Y')
    registros_a_inserir = [
        (npj, 'TESTE MANUAL', 'Adverso de Teste', data_hoje) for npj in npjs
    ]
    
    query = f"""
    INSERT OR IGNORE INTO {TABELA_NOTIFICACOES}
    (NPJ, tipo_notificacao, adverso_principal, data_notificacao)
    VALUES (?, ?, ?, ?)
    """
    
    cursor.executemany(query, registros_a_inserir)
    registros_criados = cursor.rowcount
    conn.commit()
    conn.close()
    
    print(f"✅ {registros_criados} novas notificações de teste criadas. {len(npjs) - registros_criados} ignoradas (já existentes).")
    return registros_criados

def atribuir_notificacoes_em_lote(npjs, usuario_id):
    if not npjs: return 0
    conn = sqlite3.connect(DB_NOME)
    cursor = conn.cursor()
    placeholders = ', '.join(['?'] * len(npjs))
    query = f"UPDATE {TABELA_NOTIFICACOES} SET usuario_id = ? WHERE NPJ IN ({placeholders})"
    params = [usuario_id] + npjs
    cursor.execute(query, params)
    conn.commit()
    count = cursor.rowcount
    conn.close()
    return count

def desatribuir_notificacoes_em_lote(npjs):
    if not npjs: return 0
    return atribuir_notificacoes_em_lote(npjs, None)


def salvar_notificacoes(lista_notificacoes: list[dict]):
    """Salva uma lista de novas notificações, ignorando duplicatas."""
    if not lista_notificacoes:
        return 0
    
    conn = None
    registros_inseridos = 0
    try:
        conn = sqlite3.connect(DB_NOME)
        cursor = conn.cursor()
        
        query = f"""
        INSERT OR IGNORE INTO {TABELA_NOTIFICACOES} 
        (NPJ, tipo_notificacao, adverso_principal, data_notificacao) 
        VALUES (?, ?, ?, ?)
        """
        
        registros_a_inserir = [
            (item['NPJ'], item['tipo_notificacao'], item.get('adverso_principal'), item['data_notificacao'])
            for item in lista_notificacoes
        ]
        
        cursor.executemany(query, registros_a_inserir)
        registros_inseridos = cursor.rowcount
        conn.commit()
        
        total_tentado = len(registros_a_inserir)
        ignorados = total_tentado - registros_inseridos
        
        if ignorados > 0:
            print(f"✅ {registros_inseridos} novas notificações salvas. {ignorados} duplicatas foram ignoradas.")
        else:
            print(f"✅ {registros_inseridos} novas notificações salvas para processamento.")

    except sqlite3.Error as e:
        print(f"❌ ERRO ao salvar notificações: {e}")
    finally:
        if conn:
            conn.close()
    return registros_inseridos

def obter_npjs_pendentes_agrupados() -> list[dict]:
    """
    Busca NPJs únicos que tenham pelo menos uma notificação 'Pendente',
    retornando também a data da notificação mais recente para guiar a busca.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_NOME)
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        
        query = f"""
        SELECT 
            NPJ,
            MAX(data_notificacao) as data_recente_notificacao
        FROM {TABELA_NOTIFICACOES}
        WHERE status = 'Pendente'
        GROUP BY NPJ
        """
        cursor.execute(query)
        pendentes = [dict(row) for row in cursor.fetchall()]
        print(f"🔎 Encontrados {len(pendentes)} NPJs únicos para processamento.")
        return pendentes
    except sqlite3.Error as e:
        print(f"❌ ERRO ao obter NPJs pendentes agrupados: {e}")
        return []
    finally:
        if conn:
            conn.close()

def atualizar_notificacoes_de_npj_processado(npj: str, numero_processo: str, andamentos: list[dict], documentos: list[dict]):
    """
    Atualiza TODAS as notificações 'Pendente' de um NPJ específico para 'Processado',
    preenchendo os detalhes em todas elas.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_NOME)
        cursor = conn.cursor()

        andamentos_json = json.dumps(andamentos, ensure_ascii=False)
        documentos_json = json.dumps(documentos, ensure_ascii=False)
        
        query = f"""
        UPDATE {TABELA_NOTIFICACOES} 
        SET 
            numero_processo = ?,
            andamentos = ?, 
            documentos = ?, 
            status = 'Processado'
        WHERE NPJ = ? AND status = 'Pendente'
        """
        params = (numero_processo, andamentos_json, documentos_json, npj)
        
        cursor.execute(query, params)
        conn.commit()
        print(f"    - ✅ {cursor.rowcount} notificação(ões) do NPJ {npj} atualizadas para 'Processado'.")

    except sqlite3.Error as e:
        print(f"❌ ERRO ao atualizar em lote o NPJ {npj}: {e}")
    finally:
        if conn:
            conn.close()

def marcar_npj_como_erro(npj: str):
    """Marca TODAS as notificações 'Pendente' de um NPJ específico como 'Erro'."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NOME)
        cursor = conn.cursor()
        query = f"UPDATE {TABELA_NOTIFICACOES} SET status = 'Erro' WHERE NPJ = ? AND status = 'Pendente'"
        cursor.execute(query, (npj,))
        conn.commit()
        print(f"    - ⚠️ {cursor.rowcount} notificação(ões) do NPJ {npj} marcadas como 'Erro'.")
    except sqlite3.Error as e:
        print(f"❌ ERRO ao marcar NPJ {npj} como erro: {e}")
    finally:
        if conn:
            conn.close()

def salvar_log_execucao(log_data: dict):
    """Salva um registro de log no banco de dados."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NOME)
        cursor = conn.cursor()
        colunas = ', '.join(log_data.keys())
        placeholders = ', '.join(['?'] * len(log_data))
        query = f"INSERT INTO {TABELA_LOGS} ({colunas}) VALUES ({placeholders})"
        cursor.execute(query, list(log_data.values()))
        conn.commit()
        print("✅ Resumo da execução salvo no log.")
    except sqlite3.Error as e:
        print(f"❌ ERRO ao salvar log de execução: {e}")
    finally:
        if conn:
            conn.close()

def arquivar_notificacao_por_npj(npj: str):
    """Atualiza todas as notificações de um NPJ para 'Arquivado'."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NOME)
        cursor = conn.cursor()
        query = f"UPDATE {TABELA_NOTIFICACOES} SET status = 'Arquivado' WHERE NPJ = ? AND status IN ('Processado', 'Processado em Teste')"
        cursor.execute(query, (npj,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ ERRO ao arquivar notificações para o NPJ {npj}: {e}")
    finally:
        if conn:
            conn.close()

def desarquivar_notificacao_por_npj(npj: str):
    """Atualiza todas as notificações arquivadas de um NPJ de volta para 'Processado'."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NOME)
        cursor = conn.cursor()
        query = f"UPDATE {TABELA_NOTIFICACOES} SET status = 'Processado' WHERE NPJ = ? AND status = 'Arquivado'"
        cursor.execute(query, (npj,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ ERRO ao desarquivar notificações para o NPJ {npj}: {e}")
    finally:
        if conn:
            conn.close()

def arquivar_notificacoes_em_lote_por_npj(lista_npjs: list[str]):
    """Atualiza o status de uma lista de NPJs para 'Arquivado'."""
    if not lista_npjs:
        return 0
    conn = None
    try:
        conn = sqlite3.connect(DB_NOME)
        cursor = conn.cursor()
        placeholders = ', '.join(['?'] * len(lista_npjs))
        query = f"""
        UPDATE {TABELA_NOTIFICACOES}
        SET status = 'Arquivado'
        WHERE NPJ IN ({placeholders})
        AND status IN ('Processado', 'Processado em Teste')
        """
        cursor.execute(query, lista_npjs)
        conn.commit()
        registros_afetados = cursor.rowcount
        print(f"✅ {registros_afetados} notificações (de {len(lista_npjs)} NPJs) arquivadas em lote.")
        return registros_afetados
    except sqlite3.Error as e:
        print(f"❌ ERRO ao arquivar notificações em lote por NPJ: {e}")
        return 0
    finally:
        if conn:
            conn.close()
