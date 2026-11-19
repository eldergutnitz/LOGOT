#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="${1:-/srv/logs_ot}"
SCRIPT_PATH="/opt/logot/importer/import_logs.py"
ENV_FILE="/opt/logot/importer/.env"
LOCK_FILE="/tmp/import_logs.lock"
LOG_FILE="/var/log/logot/import_logs.log"

if [[ ! -f "$SCRIPT_PATH" ]]; then
  echo "ERROR: no existe $SCRIPT_PATH" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: no existe $ENV_FILE" >&2
  exit 1
fi

mkdir -p "$(dirname "$LOG_FILE")"

# shellcheck disable=SC1090
source "$ENV_FILE"

/usr/bin/flock -n "$LOCK_FILE" \
  /usr/bin/python3 "$SCRIPT_PATH" "$BASE_DIR" \
  --db-host "${PGHOST:-127.0.0.1}" \
  --db-port "${PGPORT:-5432}" \
  --db-name "${PGDATABASE:-syslogdb}" \
  --db-user "${PGUSER:?PGUSER requerido}" \
  --db-password "${PGPASSWORD:-}" \
  >> "$LOG_FILE" 2>&1
