#!/usr/bin/env bash
# FCMS backend entrypoint: wait for DB → migrate → seed → serve
set -e
DB_HOST="${DB_HOST:-db}"; DB_PORT="${DB_PORT:-5432}"
echo "⏳ waiting for PostgreSQL at $DB_HOST:$DB_PORT ..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -q; do sleep 2; done
echo "▶ alembic upgrade head"
alembic upgrade head
echo "▶ seeding admin ($SEED_MODE)"
if [ "${SEED_MODE:-admin}" = "all" ]; then python seed_admin.py --all; else python seed_admin.py; fi
echo "🚀 starting FCMS on :8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${WORKERS:-2}"
