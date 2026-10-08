#!/bin/bash
# FCMS — start the system on this Mac and open the login page.
# Double-click in Finder, or:  bash "scripts/mac/start.command"     (Ctrl-C in this window stops it)
cd "$(dirname "$0")/../.."
# run Homebrew without questions or auto-updates (a HOMEBREW_ASK setting in the shell profile would otherwise stop the script)
unset HOMEBREW_ASK; export HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_CLEANUP=1 HOMEBREW_NO_ENV_HINTS=1 NONINTERACTIVE=1
for p in /opt/homebrew/bin/brew /usr/local/bin/brew; do [ -x "$p" ] && eval "$("$p" shellenv)" && break; done
[ -x .venv/bin/python ] || { echo "Run scripts/mac/setup.command first."; read -r -p "Press Enter to close…" _; exit 1; }
PG="$(brew --prefix postgresql@16)/bin"
brew services start postgresql@16 >/dev/null 2>&1 || true
for i in $(seq 1 30); do "$PG/pg_isready" -q >/dev/null 2>&1 && break; sleep 1; done
# shellcheck disable=SC1091
source .venv/bin/activate
export PYTHONPATH=.
alembic upgrade head >/dev/null 2>&1 || alembic upgrade head      # picks up new migrations after a git pull
IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
echo "FCMS running:  http://localhost:8000/login${IP:+   ·   on this network: http://$IP:8000/login}"
echo "Patient app:   http://localhost:8000/portal     API docs: http://localhost:8000/docs"
( sleep 2; open "http://localhost:8000/login" ) &
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
