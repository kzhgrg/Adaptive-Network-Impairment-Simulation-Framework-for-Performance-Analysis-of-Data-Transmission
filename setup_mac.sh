#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo 'Python 3 required. Install Python from python.org or Homebrew.'; exit 1; }
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
printf '\nSetup complete! Run: ./start_mac.sh\n'
