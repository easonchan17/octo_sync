#!/bin/bash
#
# sync.sh - File sync tool between octo_sync machines
#
# Usage:
#   ./sync.sh
#
# Env: OCTO_PROJECT_DIR

PROJECT_DIR="${OCTO_PROJECT_DIR:-$(pwd)}"

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
    exit 1
fi

echo ""
mapfile -t FILES < <(find "$SOURCE_ABS" -type f -printf '%T@ %p\n' | sort -rn | head -6 | awk '{print $2}')

if [[ ${#FILES[@]} -eq 0 ]]; then
    echo "No files found in $SOURCE_SUBDIR"
    exit 1
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
    exit 1
fi

echo ""
echo "Sync to $TARGET_HOST:$TARGET_PROJECT"
for file in "${SELECTED[@]}"; do
    printf "  → %s\n" "${file#$PROJECT_DIR/}"
done

echo ""
read -rp "Confirm? [y/N] " confirm
[[ "$confirm" != "y" && "$confirm" != "Y" ]] && echo "Cancelled." && exit 0

echo ""
for file in "${SELECTED[@]}"; do
    rel="${file#$PROJECT_DIR/}"
    target_dir="$TARGET_PROJECT/$(dirname "$rel")"
    ssh "$TARGET_HOST" "mkdir -p '$target_dir'" && \
    rsync -avz "$file" "$TARGET_HOST:$TARGET_PROJECT/$rel"
done

echo ""
echo "Done."
