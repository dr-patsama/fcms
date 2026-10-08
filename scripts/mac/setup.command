#!/bin/bash
# FCMS — one-time setup on a Mac (Apple Silicon or Intel). Safe to run again.
# Double-click this file in Finder, or:  bash "scripts/mac/setup.command"
#
# Installs Homebrew (if missing), PostgreSQL 16 and Python 3.13, creates the fcms_db database,
# builds the Python environment, writes .env, runs the migrations, seeds the admin + demo logins
# and the default treatment packages. Then start the system with scripts/mac/start.command.
set -euo pipefail
cd "$(dirname "$0")/../.."
REPO="$(pwd)"
log() { printf '\n\033[1;35m▶ %s\033[0m\n' "$*"; }
fail() { printf '\n\033[1;31m✖ %s\033[0m\n' "$*"; read -r -p "Press Enter to close…" _; exit 1; }
trap 'fail "Setup stopped at line $LINENO — scroll up for the error, then run this file again."' ERR

log "FCMS setup in $REPO"

# ── 1. Homebrew ───────────────────────────────────────────────────────────────
for p in /opt/homebrew/bin/brew /usr/local/bin/brew; do [ -x "$p" ] && eval "$("$p" shellenv)" && break; done
if ! command -v brew >/dev/null 2>&1; then
  log "Installing Homebrew (it will ask for your Mac login password)"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  for p in /opt/homebrew/bin/brew /usr/local/bin/brew; do [ -x "$p" ] && eval "$("$p" shellenv)" && break; done
fi
command -v brew >/dev/null 2>&1 || fail "Homebrew is not available — install it from https://brew.sh and run this again."

# ── 2. PostgreSQL 16 + Python 3.13 ────────────────────────────────────────────
log "Installing PostgreSQL 16 and Python 3.13 (first time takes a few minutes)"
brew list postgresql@16 >/dev/null 2>&1 || brew install postgresql@16
brew list python@3.13   >/dev/null 2>&1 || brew install python@3.13
PG="$(brew --prefix postgresql@16)/bin"
PY="$(brew --prefix python@3.13)/bin/python3.13"
export PATH="$PG:$PATH"

log "Starting PostgreSQL (launches automatically at login from now on)"
brew services start postgresql@16 >/dev/null 2>&1 || true
for i in $(seq 1 40); do "$PG/pg_isready" -q >/dev/null 2>&1 && break; sleep 1; done
"$PG/pg_isready" -q || fail "PostgreSQL did not start. Try: brew services restart postgresql@16"

# ── 3. Database and user ──────────────────────────────────────────────────────
log "Creating database fcms_db and user fcms_user"
"$PG/psql" -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='fcms_user'" | grep -q 1 \
  || "$PG/psql" -d postgres -qc "CREATE ROLE fcms_user LOGIN PASSWORD 'fcms_pass' CREATEDB"
"$PG/psql" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='fcms_db'" | grep -q 1 \
  || "$PG/createdb" -O fcms_user fcms_db
"$PG/psql" -d fcms_db -qc "CREATE EXTENSION IF NOT EXISTS pgcrypto" || true

# ── 4. Python environment ─────────────────────────────────────────────────────
log "Python packages (.venv)"
[ -x .venv/bin/python ] || "$PY" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

# ── 5. .env ───────────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
  log "Writing .env (local settings — never commit this file)"
  SECRET="$(python -c 'import secrets;print(secrets.token_hex(32))')"
  cat > .env <<EOF
# FCMS local settings (created by scripts/mac/setup.command)
DATABASE_URL=postgresql://fcms_user:fcms_pass@localhost:5432/fcms_db
SECRET_KEY=$SECRET
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
CLINIC_NAME_EN=LIFE by Dr. Pat
CLINIC_NAME_TH=ไลฟ์ บาย ดอกเตอร์พัฒน์
CLINIC_PHONE=083-432-4664
PORTAL_BASE_URL=http://localhost:8000/portal
# Patient-app sign-in codes are shown on screen until an SMS/LINE channel is configured
OTP_DEV_ECHO=true
# External channels (LINE, SMS, SMTP, WhatsApp, Google Calendar, PromptPay): see journey/README.md
EOF
else
  log ".env already exists — keeping it"
fi

# ── 6. Migrations + seed ──────────────────────────────────────────────────────
export PYTHONPATH=.
log "Database migrations (alembic upgrade head)"
alembic upgrade head
log "Seeding admin + one demo login per role"
python seed_admin.py --all
log "Seeding default treatment packages"
python - <<'EOF'
from module1.backend.core.database import SessionLocal
from journey.backend.services import packages as pk
db = SessionLocal()
try:
    r = pk.seed_defaults(db); db.commit(); print("   packages:", r)
finally:
    db.close()
EOF

log "Setup complete."
echo "   Start:   double-click  scripts/mac/start.command   (opens http://localhost:8000/login)"
echo "   Admin:   admin@lifeclinic.com / LifeByDrPat2026!   (demo staff: <role>@lifeclinic.com / Fcms2026!)"
echo "   Demo KPI history (optional, test data only):  scripts/mac/seed-demo-data.command"
read -r -p "Press Enter to close…" _
