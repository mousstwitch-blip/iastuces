#!/usr/bin/env bash
# Installe les dépendances du studio. Usage : bash scripts/install.sh
set -euo pipefail
cd "$(dirname "$0")/.."
command -v ffmpeg >/dev/null || { echo "Installe d'abord ffmpeg : https://ffmpeg.org/download.html"; exit 1; }
python3 -m pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
python3 main.py --check
