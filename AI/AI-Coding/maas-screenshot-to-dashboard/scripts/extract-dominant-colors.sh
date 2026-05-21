#!/bin/bash
# Extract dominant colors from a screenshot using anydesign's extract_colors.py
#
# Usage:
#   ./extract-dominant-colors.sh <screenshot_path> [--top N]
#
# Example:
#   ./extract-dominant-colors.sh dashboard.jpeg --top 8

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ANYDESIGN_SCRIPT="${SCRIPT_DIR}/../.claude/skills/anydesign/scripts/extract_colors.py"

if [ ! -f "$ANYDESIGN_SCRIPT" ]; then
    # Try alternative location
    ANYDESIGN_SCRIPT=".claude/skills/anydesign/scripts/extract_colors.py"
fi

if [ ! -f "$ANYDESIGN_SCRIPT" ]; then
    echo "Error: anydesign extract_colors.py not found"
    echo "Install: git clone https://github.com/uxKero/anydesign.git && cp -r anydesign .claude/skills/anydesign"
    exit 1
fi

python3 "$ANYDESIGN_SCRIPT" "$@"
