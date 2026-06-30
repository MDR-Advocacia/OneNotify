#!/usr/bin/env bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:99}"
SCREEN_GEOMETRY="${SCREEN_GEOMETRY:-1920x1080x24}"
VNC_PORT="${VNC_PORT:-5900}"
NOVNC_PORT="${NOVNC_PORT:-6080}"

mkdir -p /tmp/onenotify-rpa

if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
  Xvfb "$DISPLAY" -screen 0 "$SCREEN_GEOMETRY" -ac +extension RANDR \
    >/tmp/onenotify-rpa/xvfb.log 2>&1 &
  sleep 1
fi

if command -v fluxbox >/dev/null 2>&1; then
  fluxbox >/tmp/onenotify-rpa/fluxbox.log 2>&1 &
fi

x11vnc \
  -display "$DISPLAY" \
  -forever \
  -shared \
  -nopw \
  -listen 0.0.0.0 \
  -rfbport "$VNC_PORT" \
  >/tmp/onenotify-rpa/x11vnc.log 2>&1 &

if command -v websockify >/dev/null 2>&1 && [[ -d /usr/share/novnc ]]; then
  websockify \
    --web=/usr/share/novnc \
    "0.0.0.0:${NOVNC_PORT}" \
    "localhost:${VNC_PORT}" \
    >/tmp/onenotify-rpa/novnc.log 2>&1 &
else
  echo "noVNC/websockify not available; continuing without browser-based VNC" >&2
fi

echo "RPA display ready on DISPLAY=${DISPLAY}; noVNC port=${NOVNC_PORT}; VNC port=${VNC_PORT}"

exec "$@"
