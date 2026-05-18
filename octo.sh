#!/bin/bash

XVFB_SCREEN="${OCTO_XVFB_SCREEN:-1920x1080x24}"
CHECK_INTERVAL="${OCTO_CHECK_INTERVAL:-10}"

PROJECT_DIR="${OCTO_PROJECT_DIR:-/home/ubuntu/workspace/octo_sync}"
PYTHON_BIN=".venv/bin/python"

ROLE="${1:-unified}"
PROCESS_NAME="python launcher.py $ROLE"
LOG_FILE="octo-${ROLE}.log"

cd "$PROJECT_DIR" || exit 1

echo "[MONITOR] Process monitor started for: $PROCESS_NAME"

while true; do
    if ! pgrep -f "$PROCESS_NAME" > /dev/null; then
        echo "[MONITOR] ($(date)) Process is NOT running! Attempting to restart..."

        if [ "$ROLE" = "crawler" ] || [ "$ROLE" = "unified" ]; then
            pkill -f "camoufox-bin" 2>/dev/null
            nohup xvfb-run -a --server-args="-screen 0 $XVFB_SCREEN" "$PYTHON_BIN" launcher.py "$ROLE" > "$LOG_FILE" 2>&1 &
        else
            nohup "$PYTHON_BIN" launcher.py "$ROLE" > "$LOG_FILE" 2>&1 &
        fi

        NEW_PID=$!
        echo "[MONITOR] ($(date)) Process restarted successfully with PID: $NEW_PID"
    fi

    sleep "$CHECK_INTERVAL"
done
