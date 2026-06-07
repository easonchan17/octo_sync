#!/bin/bash
#
# i18n.sh - Name i18n translation assistant for octo_sync
#
# Usage:
#   ./i18n.sh
#
# Env: OCTO_PROJECT_DIR, OCTO_PYTHON_BIN

PROJECT_DIR="${OCTO_PROJECT_DIR:-./}"
PYTHON_BIN="${OCTO_PYTHON_BIN:-.venv/bin/python}"

cd "$PROJECT_DIR" || exit 1
"$PYTHON_BIN" scripts/translate_names.py
