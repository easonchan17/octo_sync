#!/bin/bash
#
# ml.sh - ML operations runner for octo_sync
#
# Usage:
#   ./ml.sh dataset start [-d]
#   ./ml.sh dataset stop
#   ./ml.sh model [-f <file>] [-b] start [-d]
#   ./ml.sh model stop [pid]
#   ./ml.sh model list
#
# Env: OCTO_PROJECT_DIR, OCTO_PYTHON_BIN
#      OCTO_SAMPLE_LEAGUE_IDS, OCTO_SAMPLE_MIN_SEASON, OCTO_SAMPLE_MAX_SEASON, OCTO_SAMPLE_FORMAT

PROJECT_DIR="${OCTO_PROJECT_DIR:-./}"
PYTHON_BIN="${OCTO_PYTHON_BIN:-.venv/bin/python}"

SAMPLE_LEAGUE_IDS="${OCTO_SAMPLE_LEAGUE_IDS:-101 102 103 104 105 100}"
SAMPLE_MIN_SEASON="${OCTO_SAMPLE_MIN_SEASON:-2019}"
SAMPLE_MAX_SEASON="${OCTO_SAMPLE_MAX_SEASON:-2025}"
SAMPLE_FORMAT="${OCTO_SAMPLE_FORMAT:-csv}"

DATASET_PATTERN="python scripts/build_sample.py"
MODEL_PATTERN="python scripts/train.py"
LOG_DIR="output/logs"

USAGE="Usage:
  $0 dataset start [-d]
  $0 dataset stop
  $0 model [-f <file>] [-b] start [-d]
  $0 model stop [pid]
  $0 model list"

die() { echo "$USAGE" >&2; exit 1; }

COMMAND="${1:-}"
[ -z "$COMMAND" ] && die
shift

case "$COMMAND" in
    dataset|model) ;;
    *) echo "Unknown command: $COMMAND" >&2; die ;;
esac

TRAIN_FILE=""
BALANCED=false
DAEMON=false
ACTION=""
TARGET_PID=""

while [ $# -gt 0 ]; do
    case "$1" in
        -f) [ -z "$2" ] && { echo "Error: -f requires a filename" >&2; die; }
            TRAIN_FILE="$2"; shift 2 ;;
        -b|--balanced) BALANCED=true; shift ;;
        -d|--daemon)   DAEMON=true;   shift ;;
        start|list)    ACTION="$1";   shift ;;
        stop)          ACTION="$1";   shift
                       case "${1:-}" in [0-9]*) TARGET_PID="$1"; shift ;; esac ;;
        *) echo "Unknown option: $1" >&2; die ;;
    esac
done

[ -z "$ACTION" ] && die
[ "$COMMAND" = model ] && [ "$ACTION" = start ] && [ -z "$TRAIN_FILE" ] && \
    { echo "Error: -f <file> is required for model start" >&2; die; }

cd "$PROJECT_DIR" || exit 1

dataset_start() {
    local cmd=(
        "$PYTHON_BIN" scripts/build_sample.py
        --league_ids    $SAMPLE_LEAGUE_IDS
        --min_season    "$SAMPLE_MIN_SEASON"
        --max_season    "$SAMPLE_MAX_SEASON"
        --sample_format "$SAMPLE_FORMAT"
    )
    if [ "$DAEMON" = true ]; then
        mkdir -p "$LOG_DIR"
        nohup "${cmd[@]}" > "${LOG_DIR}/octo-dataset.log" 2>&1 &
        echo "[DATASET] Started (PID: $!) -> ${LOG_DIR}/octo-dataset.log"
    else
        "${cmd[@]}"
    fi
}

dataset_stop() {
    pkill -f "$DATASET_PATTERN" \
        && echo "[DATASET] Stopped" \
        || echo "[DATASET] No dataset build running"
}

model_start() {
    local cmd=("$PYTHON_BIN" scripts/train.py --dataset_name "$TRAIN_FILE")
    [ "$BALANCED" = true ] && cmd+=(--balanced)

    if [ "$DAEMON" = true ]; then
        mkdir -p "$LOG_DIR"
        local log="${LOG_DIR}/octo-model-$(basename "$TRAIN_FILE" .csv).log"
        nohup "${cmd[@]}" > "$log" 2>&1 &
        echo "[MODEL] Started job $! -> $log"
    else
        "${cmd[@]}"
    fi
}

model_stop() {
    if [ -n "$TARGET_PID" ]; then
        kill "$TARGET_PID" 2>/dev/null \
            && echo "[MODEL] Stopped job $TARGET_PID" \
            || echo "[MODEL] No process found with PID $TARGET_PID"
    else
        pkill -f "$MODEL_PATTERN" \
            && echo "[MODEL] Stopped all training jobs" \
            || echo "[MODEL] No training jobs running"
    fi
}

model_list() {
    if ! pgrep -f "$MODEL_PATTERN" > /dev/null; then
        echo "[MODEL] No training jobs running"
        return
    fi
    echo "[MODEL] Running jobs:"
    pgrep -f "$MODEL_PATTERN" | while read -r pid; do
        echo "  PID $pid: $(ps -p "$pid" -o args= 2>/dev/null)"
    done
}

case "$COMMAND" in
    dataset)
        case "$ACTION" in
            start) dataset_start ;;
            stop)  dataset_stop  ;;
            *) echo "dataset does not support action: $ACTION" >&2; die ;;
        esac
        ;;
    model)
        case "$ACTION" in
            start) model_start ;;
            stop)  model_stop  ;;
            list)  model_list  ;;
        esac
        ;;
esac
