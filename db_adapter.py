import os
import sqlite3
from contextlib import contextmanager


DEFAULT_SQLITE_DB = os.path.abspath(os.path.join(os.path.dirname(__file__), "rpa_refatorado.db"))
DEFAULT_LEGALONE_SQLITE_DB = os.path.abspath(os.path.join(os.path.dirname(__file__), "database.db"))


def database_url() -> str | None:
    return os.getenv("DATABASE_URL")


def is_postgres() -> bool:
    url = database_url()
    return bool(url and url.startswith(("postgres://", "postgresql://")))


def _translate_placeholders(query: str) -> str:
    if not is_postgres():
        return query
    return query.replace("?", "%s")


class DatabaseConnection:
    def __init__(self, conn, dialect: str):
        object.__setattr__(self, "_conn", conn)
        object.__setattr__(self, "dialect", dialect)

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __setattr__(self, name, value):
        if name in {"_conn", "dialect"}:
            object.__setattr__(self, name, value)
        elif hasattr(self._conn, name):
            setattr(self._conn, name, value)
        else:
            object.__setattr__(self, name, value)

    def __enter__(self):
        self._conn.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return self._conn.__exit__(exc_type, exc, tb)

    def cursor(self):
        return Cursor(self._conn.cursor(), self.dialect)

    def execute(self, query: str, params=None):
        cursor = self.cursor()
        cursor.execute(query, params)
        return cursor

    def executemany(self, query: str, params):
        cursor = self.cursor()
        cursor.executemany(query, params)
        return cursor

    def commit(self):
        return self._conn.commit()

    def close(self):
        return self._conn.close()


class Cursor:
    def __init__(self, cursor, dialect: str):
        self._cursor = cursor
        self.dialect = dialect

    def __getattr__(self, name):
        return getattr(self._cursor, name)

    def execute(self, query: str, params=None):
        if self.dialect == "postgres":
            query = _translate_placeholders(query)
        if params is None or params == () or params == []:
            return self._cursor.execute(query)
        return self._cursor.execute(query, params)

    def executemany(self, query: str, params):
        if self.dialect == "postgres":
            query = _translate_placeholders(query)
        return self._cursor.executemany(query, params)


def connect_main() -> DatabaseConnection:
    if is_postgres():
        import psycopg2
        from psycopg2.extras import DictCursor

        conn = psycopg2.connect(database_url(), cursor_factory=DictCursor)
        return DatabaseConnection(conn, "postgres")

    sqlite_path = os.getenv("SQLITE_DATABASE_PATH", DEFAULT_SQLITE_DB)
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    return DatabaseConnection(conn, "sqlite")


def connect_legalone() -> DatabaseConnection:
    if is_postgres():
        return connect_main()

    sqlite_path = os.getenv("LEGALONE_SQLITE_DATABASE_PATH", DEFAULT_LEGALONE_SQLITE_DB)
    conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return DatabaseConnection(conn, "sqlite")


def execute(conn: DatabaseConnection, query: str, params=None):
    return conn.execute(query, params or ())


def executemany(conn: DatabaseConnection, query: str, params):
    return conn.executemany(query, params)


def placeholders(count: int) -> str:
    token = "%s" if is_postgres() else "?"
    return ", ".join([token] * count)


def table_has_column(conn: DatabaseConnection, table_name: str, column_name: str) -> bool:
    if conn.dialect == "postgres":
        cur = conn.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = ?
              AND column_name = ?
            """,
            (table_name.lower(), column_name.lower()),
        )
        return cur.fetchone() is not None

    cur = conn.execute(f"PRAGMA table_info({table_name})")
    return column_name in [col["name"] for col in cur.fetchall()]


def distinct_npj_date_count_expr() -> str:
    if is_postgres():
        return "COUNT(DISTINCT (NPJ, data_notificacao))"
    return "COUNT(DISTINCT NPJ || data_notificacao)"


def grouped_notificacoes_select(gerou_tarefa_select: str) -> str:
    if is_postgres():
        gerou = "MAX(gerou_tarefa) as gerou_tarefa," if gerou_tarefa_select else ""
        return f"""
        SELECT
            NPJ, data_notificacao, MAX(adverso_principal) as adverso_principal,
            MAX(numero_processo) as numero_processo, MAX(polo) as polo,
            STRING_AGG(id::text, ';') as ids,
            STRING_AGG(tipo_notificacao, '; ') as tipos_notificacao, MAX(responsavel) as responsavel,
            MAX(data_processamento) as data_processamento, MAX(detalhes_erro) as detalhes_erro,
            MAX(rpa_status) as rpa_status, MAX(bb_ciencia_status) as bb_ciencia_status,
            MAX(human_status) as human_status, MAX(flow_status) as flow_status,
            {gerou}
            MAX(status) as status
        FROM notificacoes {{query_status}}
        """

    return f"""
        SELECT
            NPJ, data_notificacao, MAX(adverso_principal) as adverso_principal,
            MAX(numero_processo) as numero_processo, MAX(polo) as polo,
            GROUP_CONCAT(id, ';') as ids,
            GROUP_CONCAT(tipo_notificacao, '; ') as tipos_notificacao, MAX(responsavel) as responsavel,
            MAX(data_processamento) as data_processamento, MAX(detalhes_erro) as detalhes_erro,
            MAX(rpa_status) as rpa_status, MAX(bb_ciencia_status) as bb_ciencia_status,
            MAX(human_status) as human_status, MAX(flow_status) as flow_status,
            {gerou_tarefa_select}
            MAX(status) as status
        FROM notificacoes {{query_status}}
    """


DBError = sqlite3.Error
IntegrityError = sqlite3.IntegrityError


def postgres_errors():
    if not is_postgres():
        return DBError, IntegrityError
    import psycopg2

    return psycopg2.Error, psycopg2.IntegrityError
