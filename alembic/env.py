"""
FCMS Alembic environment
Wires SQLAlchemy Base + all module models to Alembic for migrations.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Path setup ────────────────────────────────────────────
# Add project root so modules can be imported as packages:
#   module1.backend.core.database, module1.backend.models.emr_models, etc.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ── Alembic config (must happen before env imports) ───────
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# DATABASE_URL env var overrides alembic.ini value (required in production)
db_url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
config.set_main_option("sqlalchemy.url", db_url)

# ── Import Base ───────────────────────────────────────────
from module1.backend.core.database import Base  # noqa: E402

# ── Import all models so their tables register on Base.metadata ──
# Module 1 — EMR
import module1.backend.models.user_models   # noqa: F401  (User, UserSession, AuditLog)
import module1.backend.models.emr_models    # noqa: F401  (Patient, MedicalHistory, ...)

# Module 2 — Lab
try:
    import module2.backend.models.lab_models  # noqa: F401
except ImportError:
    pass

# Module 4 — Pharmacy
try:
    import module4.backend.models.pharmacy_models  # noqa: F401
except ImportError:
    pass

for _mod in ("module5.backend.models.supply_models","module6.backend.models.crm_models","module7.backend.models.accounting_models",
             "module10.backend.models.timeline_models"):
    try:
        __import__(_mod)
    except ImportError:
        pass
# Module 3 — Ultrasound has no ORM model file; tables created via migration only.

target_metadata = Base.metadata


# ── Offline mode (generates SQL without a live DB) ────────
def run_migrations_offline() -> None:
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (applies migrations to a live DB) ─────────
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
