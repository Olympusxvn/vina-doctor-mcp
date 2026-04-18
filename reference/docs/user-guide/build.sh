#!/usr/bin/env bash
# Build user-guide.tex using lualatex and place outputs in this directory
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Run lualatex twice to resolve references and TOC
echo "Compiling user-guide.tex into ${SCRIPT_DIR}/user-guide.pdf"
lualatex -interaction=nonstopmode -output-directory="$SCRIPT_DIR" user-guide.tex
lualatex -interaction=nonstopmode -output-directory="$SCRIPT_DIR" user-guide.tex

echo "Build finished: ${SCRIPT_DIR}/user-guide.pdf"

# Note: auxiliary files (*.aux, *.log, *.out, *.toc, *.bak*) are gitignored by project
