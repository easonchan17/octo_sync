#!/bin/bash
#
# tools.sh - Data management tools for octo_sync
#
# Usage:
#   ./tools.sh
#
# Env: OCTO_PROJECT_DIR, OCTO_PYTHON_BIN

PROJECT_DIR="${OCTO_PROJECT_DIR:-$(cd "$(dirname "$0")" && pwd)}"
PYTHON_BIN="${OCTO_PYTHON_BIN:-.venv/bin/python}"

SERVERS=(
    "ubuntu@124.156.160.112|/home/ubuntu/workspace/octo_sync|Crawler Server"
    "root@122.51.0.210|/root/workspace/octo_sync|ML Server"
)

SYNC_DIRS=(
    "artifacts/dataset"
    "artifacts/models"
    "artifacts/reports"
)

_list_recent_local_files() {
    local dir="$1"
    if [[ "$(uname -s)" == "Darwin" ]]; then
        find "$dir" -type f -exec stat -f '%m %N' {} + | sort -rn | head -6 | awk '{print $2}'
    else
        find "$dir" -type f -printf '%T@ %p\n' | sort -rn | head -6 | awk '{print $2}'
    fi
}

_list_recent_remote_files() {
    local host="$1" dir="$2"
    ssh "$host" "find '$dir' -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -6 | awk '{print \$2}'"
}

tool_i18n() {
    "$PYTHON_BIN" scripts/translate_names.py
}

tool_sync() {
    echo "Target machine:"
    for i in "${!SERVERS[@]}"; do
        IFS='|' read -r host _ label <<< "${SERVERS[$i]}"
        printf "  %d) %s (%s)\n" $((i+1)) "$label" "$host"
    done
    echo ""
    read -rp "> " server_idx
    IFS='|' read -r TARGET_HOST TARGET_PROJECT TARGET_LABEL <<< "${SERVERS[$((server_idx-1))]}"
    if [[ -z "$TARGET_HOST" ]]; then
        echo "Invalid selection."
        return 1
    fi

    LOCAL_LABEL="$(hostname -s)"
    echo ""
    echo "Action:"
    echo "  1) push  ($LOCAL_LABEL → $TARGET_LABEL)"
    echo "  2) pull  ($TARGET_LABEL → $LOCAL_LABEL)"
    echo ""
    read -rp "> " action_idx
    case "$action_idx" in
        1) ACTION="push" ;;
        2) ACTION="pull" ;;
        *) echo "Invalid selection." ; return 1 ;;
    esac

    echo ""
    if [[ "$ACTION" == "push" ]]; then
        echo "Local source directory:"
    else
        echo "Remote source directory:"
    fi
    for i in "${!SYNC_DIRS[@]}"; do
        printf "  %d) %s\n" $((i+1)) "${SYNC_DIRS[$i]}"
    done
    echo ""
    read -rp "> " dir_idx
    SUBDIR="${SYNC_DIRS[$((dir_idx-1))]}"
    if [[ -z "$SUBDIR" ]]; then
        echo "Invalid selection."
        return 1
    fi

    echo ""
    FILES=()
    if [[ "$ACTION" == "push" ]]; then
        SOURCE_ABS="$PROJECT_DIR/$SUBDIR"
        if [[ ! -d "$SOURCE_ABS" ]]; then
            echo "Directory not found: $SOURCE_ABS"
            return 1
        fi
        while IFS= read -r line; do FILES+=("$line"); done < <(_list_recent_local_files "$SOURCE_ABS")
        ROOT_PREFIX="$PROJECT_DIR"
    else
        while IFS= read -r line; do FILES+=("$line"); done < <(_list_recent_remote_files "$TARGET_HOST" "$TARGET_PROJECT/$SUBDIR")
        ROOT_PREFIX="$TARGET_PROJECT"
    fi

    if [[ ${#FILES[@]} -eq 0 ]]; then
        echo "No files found in $SUBDIR"
        return 1
    fi

    echo "Latest files in $SUBDIR:"
    for i in "${!FILES[@]}"; do
        printf "  %d) %s\n" $((i+1)) "${FILES[$i]#$ROOT_PREFIX/}"
    done

    echo ""
    read -rp "Select files (e.g. 1 3 5): " selections

    SELECTED=()
    for num in $selections; do
        index=$((num-1))
        if [[ -n "${FILES[$index]}" ]]; then
            SELECTED+=("${FILES[$index]}")
        fi
    done

    if [[ ${#SELECTED[@]} -eq 0 ]]; then
        echo "No valid selection."
        return 1
    fi

    echo ""
    if [[ "$ACTION" == "push" ]]; then
        echo "Push to $TARGET_LABEL ($TARGET_HOST):"
        for file in "${SELECTED[@]}"; do
            printf "  → %s\n" "${file#$PROJECT_DIR/}"
        done
    else
        echo "Pull from $TARGET_LABEL ($TARGET_HOST):"
        for file in "${SELECTED[@]}"; do
            printf "  ← %s\n" "${file#$TARGET_PROJECT/}"
        done
    fi

    echo ""
    read -rp "Confirm? [y/N] " confirm
    [[ "$confirm" != "y" && "$confirm" != "Y" ]] && echo "Cancelled." && return 0

    echo ""
    if [[ "$ACTION" == "push" ]]; then
        for file in "${SELECTED[@]}"; do
            rel="${file#$PROJECT_DIR/}"
            ssh "$TARGET_HOST" "mkdir -p '$TARGET_PROJECT/$(dirname "$rel")'" && \
            rsync -avz "$file" "$TARGET_HOST:$TARGET_PROJECT/$rel"
        done
    else
        for file in "${SELECTED[@]}"; do
            rel="${file#$TARGET_PROJECT/}"
            mkdir -p "$PROJECT_DIR/$(dirname "$rel")" && \
            rsync -avz "$TARGET_HOST:$file" "$PROJECT_DIR/$rel"
        done
    fi

    echo ""
    echo "Done."
}

TOOLS=(
    "i18n|Football team / league i18n translation (zh)"
    "sync|ML dataset & model file sync between machines"
)

cd "$PROJECT_DIR" || exit 1

echo "Available tools:"
for i in "${!TOOLS[@]}"; do
    IFS='|' read -r key desc <<< "${TOOLS[$i]}"
    printf "  %d) %-10s %s\n" $((i+1)) "$key" "$desc"
done

echo ""
read -rp "> " selection

index=$((selection-1))
entry="${TOOLS[$index]}"

if [[ -z "$entry" ]]; then
    echo "Invalid selection."
    exit 1
fi

IFS='|' read -r key _ <<< "$entry"
"tool_${key}"
