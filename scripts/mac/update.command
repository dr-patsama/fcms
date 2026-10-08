#!/bin/bash
# FCMS — pull the latest code from GitHub, update packages and migrations. Run start.command afterwards.
cd "$(dirname "$0")/../.."
for p in /opt/homebrew/bin/brew /usr/local/bin/brew; do [ -x "$p" ] && eval "$("$p" shellenv)" && break; done
git pull --ff-only origin main
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
PYTHONPATH=. alembic upgrade head
echo "Updated to $(git log -1 --format='%h %s' | cut -c1-80)"
read -r -p "Press Enter to close…" _
