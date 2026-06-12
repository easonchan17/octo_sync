#!/bin/bash
#
# team_venues.sh - Team home venue mapping assistant for octo_sync
#
# Usage:
#   ./team_venues.sh
#
# Env: OCTO_PROJECT_DIR, OCTO_PYTHON_BIN

PROJECT_DIR="${OCTO_PROJECT_DIR:-./}"
PYTHON_BIN="${OCTO_PYTHON_BIN:-.venv/bin/python}"

cd "$PROJECT_DIR" || exit 1
"$PYTHON_BIN" scripts/init_team_venues.py
