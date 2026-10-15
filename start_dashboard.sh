#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -d .venv ]]; then echo 'Run bash setup_ubuntu.sh first.'; exit 1; fi
source .venv/bin/activate
python3 -m web.app
