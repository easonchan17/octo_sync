#!/bin/bash

# Define variables with explicit absolute paths
PROJECT_DIR="/home/ubuntu/workspace/octo_sync"
PROCESS_NAME="python main.py"
CHECK_INTERVAL=10

# Force navigate to the correct working directory immediately
cd $PROJECT_DIR || exit 1

echo "🏁 [MONITOR] Process monitor started for: $PROCESS_NAME"

while true; do
    # Check if the process is running using pgrep
    if ! pgrep -f "$PROCESS_NAME" > /dev/null; then
        echo "⚠️ [MONITOR] ($(date)) Process is NOT running! Attempting to restart..."

        # Clear out any stuck zombie browser processes to free up memory
        pkill -f "camoufox-bin" 2>/dev/null

        # Launch the application using the absolute path of the virtual environment python
        nohup xvfb-run -a --server-args="-screen 0 1920x1080x24" $PROJECT_DIR/.venv/bin/python main.py > octo.log 2>&1 &

        NEW_PID=$!
        echo "✅ [MONITOR] ($(date)) Process restarted successfully with PID: $NEW_PID"
    fi

    sleep $CHECK_INTERVAL
done