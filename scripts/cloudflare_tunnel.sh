#!/usr/bin/env bash
# Expose the local Crypto Auto Trade dashboard through a Cloudflare Tunnel.
#
# This starts the FastAPI app on 127.0.0.1:PORT and runs `cloudflared` against
# it. By default it uses a Cloudflare "quick tunnel", which prints a public
# https://<random>.trycloudflare.com URL with no Cloudflare account required.
#
# Usage:
#   scripts/cloudflare_tunnel.sh                 # quick tunnel (ephemeral URL)
#   PORT=8001 scripts/cloudflare_tunnel.sh       # custom local port
#   TUNNEL_NAME=mytunnel scripts/cloudflare_tunnel.sh   # named tunnel (needs login)
#
# Requirements:
#   - pip install -e '.[web]'
#   - cloudflared installed: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
set -euo pipefail

PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"
APP_URL="http://${HOST}:${PORT}"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "ERROR: cloudflared not found. Install it first:" >&2
  echo "  https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/" >&2
  exit 1
fi

cleanup() {
  [[ -n "${APP_PID:-}" ]] && kill "${APP_PID}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting Crypto Auto Trade on ${APP_URL} ..."
CRYPTO_AUTO_TRADE_HOST="${HOST}" CRYPTO_AUTO_TRADE_PORT="${PORT}" \
  python -m crypto_auto_trade.web &
APP_PID=$!

# Wait for the app to accept connections before opening the tunnel.
for _ in $(seq 1 30); do
  if python - "$APP_URL" <<'PY' >/dev/null 2>&1; then
import sys, urllib.request
urllib.request.urlopen(sys.argv[1] + "/api/health", timeout=1).read()
PY
    break
  fi
  sleep 1
done

echo "Opening Cloudflare Tunnel to ${APP_URL} ..."
if [[ -n "${TUNNEL_NAME:-}" ]]; then
  # Named tunnel: requires `cloudflared tunnel login` and a configured route.
  exec cloudflared tunnel run --url "${APP_URL}" "${TUNNEL_NAME}"
else
  # Quick tunnel: ephemeral public URL, no account needed.
  exec cloudflared tunnel --url "${APP_URL}"
fi
