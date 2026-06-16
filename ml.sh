#!/bin/bash
#
# ml.sh - ML operations runner for octo_sync
#
# Usage:
#   ./ml.sh dataset [-t club|national] start [-d]
#   ./ml.sh dataset stop
#   ./ml.sh model [-f <file>] [-b] start [-d]
#   ./ml.sh model stop [pid]
#   ./ml.sh model list
#
# Env: OCTO_PROJECT_DIR, OCTO_PYTHON_BIN
#      OCTO_SAMPLE_LEAGUE_IDS, OCTO_SAMPLE_MIN_SEASON, OCTO_SAMPLE_MAX_SEASON, OCTO_SAMPLE_FORMAT
#      OCTO_NATIONAL_LEAGUE_IDS

PROJECT_DIR="${OCTO_PROJECT_DIR:-./}"
PYTHON_BIN="${OCTO_PYTHON_BIN:-.venv/bin/python}"

SAMPLE_LEAGUE_IDS="${OCTO_SAMPLE_LEAGUE_IDS:-101 102 103 104 105 100}"
NATIONAL_LEAGUE_IDS="${OCTO_NATIONAL_LEAGUE_IDS:-301 311 312 313 314 315 316 317 401 411 501 601 611 701 711 801 802 901 1001 1002 1003 1004}"
SAMPLE_MIN_SEASON="${OCTO_SAMPLE_MIN_SEASON:-2019}"
SAMPLE_MAX_SEASON="${OCTO_SAMPLE_MAX_SEASON:-2025}"
SAMPLE_FORMAT="${OCTO_SAMPLE_FORMAT:-csv}"

DATASET_PATTERN="python scripts/build_sample.py"
MODEL_PATTERN="python scripts/train.py"
LOG_DIR="output/logs"

USAGE="Usage:
  $0 dataset [-t club|national] start [-d]
  $0 dataset stop
  $0 model [-t club|national] [-f <file>] [-b] start [-d]
  $0 model stop [pid]
  $0 model list
  $0 model [-t club|national] -v <version> eval"

die() { echo "$USAGE" >&2; exit 1; }

COMMAND="${1:-}"
[ -z "$COMMAND" ] && die
shift

case "$COMMAND" in
    dataset|model) ;;
    *) echo "Unknown command: $COMMAND" >&2; die ;;
esac

TRAIN_FILE=""
MODEL_VERSION=""
BALANCED=false
DAEMON=false
ACTION=""
TARGET_PID=""
SAMPLE_TYPE="club"

while [ $# -gt 0 ]; do
    case "$1" in
        -t) [ -z "$2" ] && { echo "Error: -t requires club|national" >&2; die; }
            case "$2" in
                club|national) SAMPLE_TYPE="$2"; shift 2 ;;
                *) echo "Error: -t must be club or national" >&2; die ;;
            esac ;;
        -f) [ -z "$2" ] && { echo "Error: -f requires a filename" >&2; die; }
            TRAIN_FILE="$2"; shift 2 ;;
        -v) [ -z "$2" ] && { echo "Error: -v requires a model version" >&2; die; }
            MODEL_VERSION="$2"; shift 2 ;;
        -b|--balanced) BALANCED=true; shift ;;
        -d|--daemon)   DAEMON=true;   shift ;;
        start|list|eval) ACTION="$1"; shift ;;
        stop)          ACTION="$1";   shift
                       case "${1:-}" in [0-9]*) TARGET_PID="$1"; shift ;; esac ;;
        *) echo "Unknown option: $1" >&2; die ;;
    esac
done

[ -z "$ACTION" ] && die
[ "$COMMAND" = model ] && [ "$ACTION" = start ] && [ -z "$TRAIN_FILE" ] && \
    { echo "Error: -f <file> is required for model start" >&2; die; }
[ "$COMMAND" = model ] && [ "$ACTION" = eval ] && [ -z "$MODEL_VERSION" ] && \
    { echo "Error: -v <version> is required for model eval" >&2; die; }

cd "$PROJECT_DIR" || exit 1

dataset_start() {
    local league_ids="$SAMPLE_LEAGUE_IDS"
    [ "$SAMPLE_TYPE" = "national" ] && league_ids="$NATIONAL_LEAGUE_IDS"

    local cmd=(
        "$PYTHON_BIN" scripts/build_sample.py
        --league_ids    $league_ids
        --min_season    "$SAMPLE_MIN_SEASON"
        --max_season    "$SAMPLE_MAX_SEASON"
        --sample_format "$SAMPLE_FORMAT"
        --model_type    "$SAMPLE_TYPE"
    )
    [ "$SAMPLE_TYPE" = "national" ] && cmd+=(--no_lineup_features)

    if [ "$DAEMON" = true ]; then
        mkdir -p "$LOG_DIR"
        nohup "${cmd[@]}" > "${LOG_DIR}/octo-dataset-${SAMPLE_TYPE}.log" 2>&1 &
        echo "[DATASET] Started $SAMPLE_TYPE (PID: $!) -> ${LOG_DIR}/octo-dataset-${SAMPLE_TYPE}.log"
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
    local model_family="winball_club"
    [ "$SAMPLE_TYPE" = "national" ] && model_family="winball_national"

    local cmd=("$PYTHON_BIN" scripts/train.py --dataset_name "$TRAIN_FILE" --model_family "$model_family")
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

model_eval() {
    local model_family="winball_club"
    [ "$SAMPLE_TYPE" = "national" ] && model_family="winball_national"
    "$PYTHON_BIN" scripts/eval.py --model_version "$MODEL_VERSION" --model_family "$model_family"
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
            eval)  model_eval  ;;
        esac
        ;;
esac
