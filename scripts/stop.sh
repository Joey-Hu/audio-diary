#!/usr/bin/env bash
set -euo pipefail

PORT=${PORT:-8000}
LOG_DIR=${LOG_DIR:-logs}

if [ -f "$LOG_DIR/server.pid" ]; then
  PID=$(cat "$LOG_DIR/server.pid" || true)
  if [ -n "${PID:-}" ] && ps -p "$PID" >/dev/null 2>&1; then
    echo "Stopping PID $PID ..."
    kill -9 "$PID" || true
  fi
  rm -f "$LOG_DIR/server.pid" || true
fi

if lsof -ti:"$PORT" >/dev/null 2>&1; then
  echo "Killing process(es) on port $PORT..."
  lsof -ti:"$PORT" | xargs -r kill -9 || true
fi

echo "Stopped."
