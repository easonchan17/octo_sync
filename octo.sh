#!/bin/bash
#
# octo.sh - lifecycle controller for octo_sync
#
# Usage: ./octo.sh [api|crawler|unified] [monitor] [start|stop] [-d]
#   monitor   target the watchdog (default: target launcher process)
#   -d        background mode for 'start' (default: foreground)
#
# Examples:
#   ./octo.sh api start                 launcher (foreground)
#   ./octo.sh api start -d              launcher (background)
#   ./octo.sh api stop                  launcher stop
#   ./octo.sh api monitor start         watchdog (foreground)
#   ./octo.sh api monitor start -d      watchdog (background daemon)
#   ./octo.sh api monitor stop          watchdog stop
#
# Env: OCTO_PROJECT_DIR, OCTO_PYTHON_BIN, OCTO_ENABLE_XVFB, OCTO_CHECK_INTERVAL
# Log: octo-<role>.log, monitor-<role>.log
#

ENABLE_XVFB="${OCTO_ENABLE_XVFB:-0}"
CHECK_INTERVAL="${OCTO_CHECK_INTERVAL:-10}"
PROJECT_DIR="${OCTO_PROJECT_DIR:-./}"
PYTHON_BIN="${OCTO_PYTHON_BIN:-.venv/bin/python}"


USAGE="Usage: $0 <role> [monitor] <start|stop> [-d]
  role:    api | crawler | unified
  monitor: optional, target the watchdog instead of the process
  action:  start | stop
  -d:      background mode for 'start' (default: foreground)"

die() { echo "$USAGE" >&2; exit 1; }

[ -z "$1" ] && die
ROLE="$1"

if [ "$2" = "monitor" ]; then
    TARGET="monitor"
    [ -z "$3" ] && die
    ACTION="$3"
    FLAG="${4:-}"
else
    TARGET="process"
    [ -z "$2" ] && die
    ACTION="$2"
    FLAG="${3:-}"
fi

case "$ROLE" in
    api|crawler|unified) ;;
    *) echo "Invalid role: $ROLE"; echo "$USAGE"; exit 1 ;;
esac

case "$ACTION" in
    start|stop) ;;
    *) echo "Invalid action: $ACTION"; echo "$USAGE"; exit 1 ;;
esac

DAEMON=false
case "$FLAG" in
    "") ;;
    -d|--daemon) DAEMON=true ;;
    *) echo "Unknown flag: $FLAG"; echo "$USAGE"; exit 1 ;;
esac

PROCESS_PATTERN="python launcher.py $ROLE"
MONITOR_PATTERN="octo.sh $ROLE monitor start"
PROCESS_LOG="octo-${ROLE}.log"
MONITOR_LOG="monitor-${ROLE}.log"

cd "$PROJECT_DIR" || exit 1

start_process() {
    if pgrep -f "$PROCESS_PATTERN" > /dev/null; then
        echo "[OCTO] Process already running: $PROCESS_PATTERN"
        return 0
    fi

    local cmd=()
    if [ "$ROLE" = "crawler" ] || [ "$ROLE" = "unified" ]; then
        pkill -f "camoufox-bin" 2>/dev/null
        local prefix=()
        [ "$ENABLE_XVFB" = "1" ] && prefix=(xvfb-run -a --server-args="-screen 0 1920x1080x24")
        cmd=("${prefix[@]}" "$PYTHON_BIN" launcher.py "$ROLE")
    else
        cmd=("$PYTHON_BIN" launcher.py "$ROLE")
    fi

    if [ "$DAEMON" = "true" ]; then
        nohup "${cmd[@]}" > "$PROCESS_LOG" 2>&1 &
        echo "[OCTO] Started daemon: $PROCESS_PATTERN (PID: $!) -> $PROCESS_LOG"
    else
        "${cmd[@]}"
    fi
}

stop_process() {
    if pkill -f "$PROCESS_PATTERN"; then
        echo "[OCTO] Stopped: $PROCESS_PATTERN"
    else
        echo "[OCTO] No process to stop: $PROCESS_PATTERN"
    fi
}

monitor_loop() {
    echo "[MONITOR] Process monitor started for: $PROCESS_PATTERN"
    while true; do
        if ! pgrep -f "$PROCESS_PATTERN" > /dev/null; then
            echo "[MONITOR] ($(date)) Process is NOT running. Restarting..."
            DAEMON=true start_process
        fi
        sleep "$CHECK_INTERVAL"
    done
}

start_monitor() {
    if [ "$DAEMON" = "true" ]; then
        if pgrep -f "$MONITOR_PATTERN" | grep -vw $$ > /dev/null; then
            echo "[OCTO] Monitor already running for: $ROLE"
            return 0
        fi
        nohup "$0" "$ROLE" monitor start > "$MONITOR_LOG" 2>&1 &
        echo "[OCTO] Started monitor daemon for: $ROLE (PID: $!) -> $MONITOR_LOG"
    else
        monitor_loop
    fi
}

stop_monitor() {
    if pkill -f "$MONITOR_PATTERN"; then
        echo "[OCTO] Stopped monitor for: $ROLE"
    else
        echo "[OCTO] No monitor running for: $ROLE"
    fi
}

if [ "$TARGET" = "process" ]; then
    case "$ACTION" in
        start) start_process ;;
        stop) stop_process ;;
    esac
else
    case "$ACTION" in
        start) start_monitor ;;
        stop) stop_monitor ;;
    esac
fi