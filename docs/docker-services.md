# Servicos Docker do OneNotify

## Subir banco, API e frontend

```powershell
cd C:\OneNotify
docker compose up -d postgres api frontend
```

Por padrao:

- Frontend: `http://localhost:3000`
- API: `http://localhost:5000`
- Postgres: `localhost:5433`

Para evitar conflito com processos locais:

```powershell
$env:API_PORT=5001
$env:FRONTEND_PORT=3001
docker compose up -d postgres api frontend
```

## Rodar a RPA em container

A RPA fica em profile separado para nao executar junto com o painel:

```powershell
docker compose --profile rpa run --rm rpa
```

Ela usa:

- `DATABASE_URL` apontando para o Postgres do Compose.
- `BROWSER_START_COMMAND=/app/docker/start-chrome-cdp.sh`.
- `CHROME_CDP_ENDPOINT=http://127.0.0.1:9222`.
- Volume `./chrome-profile-onenotify:/app/chrome-profile`.
- noVNC em `http://localhost:6080/vnc.html`.
- VNC direto em `localhost:5900`.

Para testar somente a tela, sem executar a automacao:

```powershell
docker rm -f onenotify-rpa-vnc-test
docker run -d --name onenotify-rpa-vnc-test -p 6080:6080 -p 5900:5900 onenotify-rpa sleep infinity
docker exec -d onenotify-rpa-vnc-test /app/docker/start-chrome-cdp.sh
```

Depois abra `http://localhost:6080/vnc.html`.

## Integracao com Onelog/Chrome dockerizado

O arquivo `autologin.py` usa `ONELOG_LOGIN_MODE=profile` por padrao.
Nesse modo ele tenta primeiro o fluxo usado pelo OneCost: abrir a URL da extensao ja instalada no perfil persistente do Chrome.
No Docker, como o perfil Linux pode nascer vazio, o container tambem pode carregar `docker/onelog-extension` como fallback/bootstrap.

Variaveis principais:

- `CHROME_CDP_ENDPOINT`: endpoint CDP do Chrome/Chromium.
- `BROWSER_START_COMMAND`: comando usado para iniciar o navegador antes da conexao CDP.
- `ONELOG_API_URL`: API do OneLog usada pela extensao. Padrao: `https://api-onelog.mdradvocacia.com`.
- `ONELOG_LOAD_BUNDLED_EXTENSION`: carrega a extensao vendorizada no container quando `true`.
- `ONELOG_FORCE_LEGACY_PROFILE_FLOW=true`: tenta abrir a URL fixa da extensao legada mesmo se ela nao aparecer nos targets CDP.
- `ONELOG_USERNAME` e `ONELOG_PASSWORD`: opcionais. Se vazios, a RPA tenta reutilizar o usuario salvo no perfil do Chrome.
- `ONELOG_LOGIN_MODE=onelog`: forca o popup novo do OneLog.
- `ONELOG_LOGIN_MODE=legacy`: volta ao fluxo antigo da extensao por URL fixa, apenas para contingencia.

Para primeiro uso sem credenciais no `.env`, abra o noVNC, faca o login pelo popup do OneLog uma vez e mantenha o volume `./chrome-profile-onenotify`.

## Validar migracao

```powershell
.\.venv-migration\Scripts\python.exe scripts\migrate_sqlite_to_postgres.py --validate-only
```
