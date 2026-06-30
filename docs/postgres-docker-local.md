# Postgres local com Docker

Este passo sobe apenas o Postgres local e migra uma copia logica dos SQLite para ele. A API e a RPA continuam apontando para SQLite ate a proxima etapa.

## Pre-requisitos

- Docker Desktop instalado e aberto no Windows.
- Backup preservado em `C:\backup\onenotify_manual_20260625_153029`.
- Branch de trabalho: `postgres-docker-local`.

## Subir Postgres

Copie o exemplo de ambiente se ainda nao existir um `.env` local:

```powershell
cd C:\OneNotify
copy .env.example .env
```

Suba o banco:

```powershell
docker compose up -d postgres
docker compose ps
```

O Postgres ficara em `localhost:5433`, para nao conflitar com outras instalacoes locais.

## Preparar dependencias do migrador

Use um ambiente Python separado, ou o venv existente se preferir:

```powershell
cd C:\OneNotify
python -m venv .venv-migration
.\.venv-migration\Scripts\Activate.ps1
pip install -r requirements-migration.txt
```

## Migrar SQLite para Postgres

Este comando recria as tabelas no Postgres e copia os dados dos dois SQLite:

```powershell
python scripts\migrate_sqlite_to_postgres.py --drop
```

O script valida as contagens de linhas por tabela ao final. Ele abre os SQLite em modo somente leitura.

## Arquivos de origem padrao

- `C:\OneNotify\rpa_refatorado.db`
- `C:\OneNotify\database.db`

Para usar outros caminhos:

```powershell
$env:SOURCE_RPA_DB='C:\backup\onenotify_manual_20260625_153029\db\rpa_refatorado.db'
$env:SOURCE_LEGALONE_DB='C:\backup\onenotify_manual_20260625_153029\db\database.db'
python scripts\migrate_sqlite_to_postgres.py --drop
```

## Importante

Este e o primeiro passo tecnico. A API ainda nao foi refatorada para Postgres nesta etapa.
