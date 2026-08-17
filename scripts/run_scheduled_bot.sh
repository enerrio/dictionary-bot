#!/bin/zsh

set -euo pipefail

SCRIPT_DIR=${0:A:h}
REPO_ROOT=${SCRIPT_DIR:h}

cd "$REPO_ROOT"

LOG_DIR="$REPO_ROOT/logs"
mkdir -p "$LOG_DIR"
find "$LOG_DIR" -type f -name "dictionary-*.log" -mtime +7 -delete

LOG_DATE=$(date +%F)
exec >>"$LOG_DIR/dictionary-${LOG_DATE}.log" 2>>"$LOG_DIR/dictionary-${LOG_DATE}.log"

PYTHON_BIN="$REPO_ROOT/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  print -u2 "expected virtualenv python at $PYTHON_BIN"
  exit 127
fi

exec "$PYTHON_BIN" scripts/run_bot.py --timeout-seconds 180
