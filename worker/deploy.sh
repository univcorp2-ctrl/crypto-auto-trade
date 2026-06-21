#!/usr/bin/env bash
# Deploy the Crypto Auto Trade dashboard + engine to Cloudflare Workers
# (with static assets). The API token is NEVER hardcoded: wrangler reads it
# from the environment. Set these before running:
#
#   export CLOUDFLARE_API_TOKEN=...      # Pages/Workers edit permission
#   export CLOUDFLARE_ACCOUNT_ID=...     # Cloudflare account id
#
#   cd worker && npm install && ./deploy.sh
set -euo pipefail
cd "$(dirname "$0")"

if [[ -z "${CLOUDFLARE_API_TOKEN:-}" ]]; then
  echo "ERROR: CLOUDFLARE_API_TOKEN is not set in the environment." >&2
  echo "Set it as an environment secret (do not paste it into commands or commit it)." >&2
  exit 1
fi
if [[ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]]; then
  echo "ERROR: CLOUDFLARE_ACCOUNT_ID is not set in the environment." >&2
  exit 1
fi

npm run typecheck
npm test
npx wrangler deploy
