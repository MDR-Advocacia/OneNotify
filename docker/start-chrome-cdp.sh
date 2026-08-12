#!/usr/bin/env bash
set -euo pipefail

PROFILE_DIR="${CHROME_PROFILE_DIR:-/app/chrome-profile}"
mkdir -p "$PROFILE_DIR"

if [[ "${CHROME_KILL_EXISTING:-true}" != "false" ]]; then
  pkill -f "$PROFILE_DIR" 2>/dev/null || true
  pkill -f "remote-debugging-port=${CHROME_REMOTE_DEBUGGING_PORT:-9222}" 2>/dev/null || true
  sleep 1
fi

rm -f "$PROFILE_DIR"/SingletonCookie "$PROFILE_DIR"/SingletonLock "$PROFILE_DIR"/SingletonSocket
find "$PROFILE_DIR" -name LOCK -type f -delete 2>/dev/null || true

EXTENSION_ARGS=()
ONELOG_EXTENSION_SOURCE="${ONELOG_EXTENSION_DIR:-/app/docker/onelog-extension}"
ONELOG_LOAD_BUNDLED_EXTENSION="${ONELOG_LOAD_BUNDLED_EXTENSION:-true}"
if [[ "$ONELOG_LOAD_BUNDLED_EXTENSION" != "false" && -d "$ONELOG_EXTENSION_SOURCE" ]]; then
  ONELOG_EXTENSION_RUNTIME="${ONELOG_EXTENSION_RUNTIME_DIR:-/tmp/onelog-extension-runtime}"
  rm -rf "$ONELOG_EXTENSION_RUNTIME"
  mkdir -p "$ONELOG_EXTENSION_RUNTIME"
  cp -a "$ONELOG_EXTENSION_SOURCE"/. "$ONELOG_EXTENSION_RUNTIME"/

  if [[ -n "${ONELOG_API_URL:-}" && -f "$ONELOG_EXTENSION_RUNTIME/background.js" ]]; then
    sed -i "s#const API_URL = .*#const API_URL = \"${ONELOG_API_URL}\";#g" "$ONELOG_EXTENSION_RUNTIME/background.js"
  fi

  EXTENSION_ARGS+=(
    --disable-extensions-except="$ONELOG_EXTENSION_RUNTIME"
    --load-extension="$ONELOG_EXTENSION_RUNTIME"
  )
fi

CHROME_BIN="${CHROME_BIN:-}"
if [[ -z "$CHROME_BIN" ]]; then
  CHROME_BIN="$(find /ms-playwright -path '*/chrome-linux/chrome' -type f | head -n 1 || true)"
fi
if [[ -z "$CHROME_BIN" ]]; then
  CHROME_BIN="$(command -v chromium || command -v chromium-browser || command -v google-chrome || true)"
fi
if [[ -z "$CHROME_BIN" ]]; then
  echo "Chrome/Chromium executable not found" >&2
  exit 1
fi

CHROME_ARGS=(
  --remote-debugging-address=0.0.0.0 \
  --remote-debugging-port="${CHROME_REMOTE_DEBUGGING_PORT:-9222}" \
  --user-data-dir="$PROFILE_DIR" \
  --no-sandbox \
  --disable-dev-shm-usage \
  --disable-gpu \
  --start-maximized \
  --window-size="${CHROME_WINDOW_SIZE:-1920,1080}" \
  "${EXTENSION_ARGS[@]}"
)

if [[ -n "${DISPLAY:-}" ]]; then
  exec "$CHROME_BIN" "${CHROME_ARGS[@]}"
fi

exec xvfb-run -a "$CHROME_BIN" "${CHROME_ARGS[@]}"
