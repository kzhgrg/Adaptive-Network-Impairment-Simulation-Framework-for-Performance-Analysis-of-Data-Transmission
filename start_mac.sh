#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -f .venv/bin/activate ]]; then echo 'First run: bash setup_mac.sh'; exit 1; fi
source .venv/bin/activate
printf 'Open http://127.0.0.1:5000 in your browser\n'
python -m web.app
