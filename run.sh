#!/usr/bin/env bash
set -euo pipefail

KEY_FILE="${SOIDIED_MASTER_KEY_FILE:-startup/.soidied_master_key}"
PYTHON_BIN="${SOIDIED_PYTHON:-python3}"

mkdir -p "$(dirname "$KEY_FILE")"
umask 077

if [[ ! -s "$KEY_FILE" ]]; then
  if [[ -n "${SOIDIED_MASTER_KEY:-}" ]]; then
    printf '%s\n' "$SOIDIED_MASTER_KEY" > "$KEY_FILE"
  else
    "$PYTHON_BIN" - <<'PY' > "$KEY_FILE"
import secrets

print(secrets.token_urlsafe(32))
PY
  fi
fi

chmod 600 "$KEY_FILE"
export SOIDIED_MASTER_KEY="$(tr -d '\r\n' < "$KEY_FILE")"

if [[ -z "$SOIDIED_MASTER_KEY" ]]; then
  echo "SOIDIED_MASTER_KEY is empty; refusing to start." >&2
  exit 1
fi

exec "$PYTHON_BIN" api.py "$@"
