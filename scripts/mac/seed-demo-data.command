#!/bin/bash
# FCMS — load DEMO data only (never on the clinic's real database):
# 12 months of invented embryology history so /insight shows KPI curves, plus one demo lab day.
cd "$(dirname "$0")/../.."
# run Homebrew without questions or auto-updates (a HOMEBREW_ASK setting in the shell profile would otherwise stop the script)
unset HOMEBREW_ASK; export HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_CLEANUP=1 HOMEBREW_NO_ENV_HINTS=1 NONINTERACTIVE=1
for p in /opt/homebrew/bin/brew /usr/local/bin/brew; do [ -x "$p" ] && eval "$("$p" shellenv)" && break; done
# shellcheck disable=SC1091
source .venv/bin/activate
export PYTHONPATH=.
python scripts/seed_kpi_demo.py "$@"
echo "Demo KPI history loaded. Remove it later with:  python scripts/seed_kpi_demo.py --reset"
read -r -p "Press Enter to close…" _
