#!/usr/bin/env bash
set -euo pipefail

PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}
ENV_NAME=${ENV_NAME:-audio-diary}
LOG_DIR=${LOG_DIR:-logs}

mkdir -p "$LOG_DIR"

# Stop existing server on the same port if any
if lsof -ti:"$PORT" >/dev/null 2>&1; then
  echo "Killing process(es) on port $PORT..."
  lsof -ti:"$PORT" | xargs -r kill -9 || true
fi

echo "Starting server on http://${HOST}:${PORT} ..."
nohup conda run -n "$ENV_NAME" uvicorn app.main:app --host "$HOST" --port "$PORT" \
  >"$LOG_DIR/server.out" 2>"$LOG_DIR/server.err" &

echo $! > "$LOG_DIR/server.pid"

echo "Started. PID=$(cat $LOG_DIR/server.pid)"
echo "Logs: $LOG_DIR/server.out  $LOG_DIR/server.err"
