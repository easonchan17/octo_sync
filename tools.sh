#!/bin/bash
#
# tools.sh - Data management tools for octo_sync
#
# Usage:
#   ./tools.sh
#
# Env: OCTO_PROJECT_DIR, OCTO_PYTHON_BIN

PROJECT_DIR="${OCTO_PROJECT_DIR:-./}"
PYTHON_BIN="${OCTO_PYTHON_BIN:-.venv/bin/python}"

tool_i18n() {
    "$PYTHON_BIN" scripts/translate_names.py
}


tool_sync() {
    if [[ "$(whoami)" == "root" ]]; then
        TARGET_HOST="ubuntu@124.156.160.112"
        TARGET_PROJECT="/home/ubuntu/workspace/octo_sync"
    else
        TARGET_HOST="root@122.51.0.210"
        TARGET_PROJECT="/root/workspace/octo_sync"
    fi

    SOURCE_DIRS=(
        "artifacts/dataset"
        "artifacts/models"
        "artifacts/reports"
    )

    echo "Source directory:"
    for i in "${!SOURCE_DIRS[@]}"; do
        printf "  %d) %s\n" $((i+1)) "${SOURCE_DIRS[$i]}"
    done
    read -rp "> " dir_idx
    SOURCE_SUBDIR="${SOURCE_DIRS[$((dir_idx-1))]}"
    SOURCE_ABS="$PROJECT_DIR/$SOURCE_SUBDIR"

    if [[ ! -d "$SOURCE_ABS" ]]; then
        echo "Directory not found: $SOURCE_ABS"
        return 1
    fi

    echo ""
    mapfile -t FILES < <(find "$SOURCE_ABS" -type f -printf '%T@ %p\n' | sort -rn | head -6 | awk '{print $2}')

    if [[ ${#FILES[@]} -eq 0 ]]; then
        echo "No files found in $SOURCE_SUBDIR"
        return 1
    fi

    echo "Latest files in $SOURCE_SUBDIR:"
    for i in "${!FILES[@]}"; do
        printf "  %d) %s\n" $((i+1)) "${FILES[$i]#$PROJECT_DIR/}"
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
    echo "Sync to $TARGET_HOST:$TARGET_PROJECT"
    for file in "${SELECTED[@]}"; do
        printf "  → %s\n" "${file#$PROJECT_DIR/}"
    done

    echo ""
    read -rp "Confirm? [y/N] " confirm
    [[ "$confirm" != "y" && "$confirm" != "Y" ]] && echo "Cancelled." && return 0

    echo ""
    for file in "${SELECTED[@]}"; do
        rel="${file#$PROJECT_DIR/}"
        target_dir="$TARGET_PROJECT/$(dirname "$rel")"
        ssh "$TARGET_HOST" "mkdir -p '$target_dir'" && \
        rsync -avz "$file" "$TARGET_HOST:$TARGET_PROJECT/$rel"
    done

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
