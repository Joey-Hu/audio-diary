#!/usr/bin/env bash
set -euo pipefail

PORT=${PORT:-8000}
LOG_DIR=${LOG_DIR:-logs}

if [ -f "$LOG_DIR/server.pid" ]; then
  PID=$(cat "$LOG_DIR/server.pid" || true)
  echo "PID file: $LOG_DIR/server.pid"
  echo "PID: ${PID:-<empty>}"
  if [ -n "${PID:-}" ] && ps -p "$PID" >/dev/null 2>&1; then
    echo "Process is running."
  else
    echo "Process not running (or PID invalid)."
  fi
else
  echo "No PID file found."
fi

echo "Port $PORT:" 
if lsof -i:"$PORT" >/dev/null 2>&1; then
  lsof -i:"$PORT" | tail -n +2
else
  echo "No process is listening on $PORT."
fi
