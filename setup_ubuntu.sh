#!/usr/bin/env bash
set -euo pipefail
sudo apt update
sudo apt install -y ns2 python3 python3-venv python3-pip
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
printf '\nSetup complete. Run: source .venv/bin/activate && python3 -m web.app\n'
