"""
FCMS — Unified application entry point (all modules, one process)
Run from repo root:  uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
import importlib
import logging

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from module1.backend.core.config import settings

log = logging.getLogger("fcms")

# (module path, attribute names to include as routers)
MODULE_ROUTERS = [
    ("module1.backend.api.emr_routes",             ["auth_router", "patient_router", "visit_router"]),
    ("module1.backend.api.user_management_routes", ["router"]),
    ("module2.backend.api.lab_routes",             ["router"]),
    ("module3.backend.api.ultrasound_routes",      ["router"]),
    ("module4.backend.api.pharmacy_routes",        ["router"]),
    ("module5.backend.api.supply_routes",          ["router"]),
    ("module6.backend.api.crm_routes",             ["router"]),
    ("module7.backend.api.accounting_routes",      ["router"]),
]


def create_app() -> FastAPI:
    app = FastAPI(
        title="FCMS — Life by Dr. Pat",
        version=settings.APP_VERSION,
        description="Fertility Clinic Management System — all modules",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    loaded, failed = [], {}
    for path, names in MODULE_ROUTERS:
        try:
            mod = importlib.import_module(path)
            for n in names:
                app.include_router(getattr(mod, n))
            loaded.append(path.split(".")[0])
        except Exception as e:  # keep the system up even if one module is broken
            failed[path] = f"{type(e).__name__}: {e}"
            log.exception("Failed to load %s", path)

    # ── Static: login page + design system (until the Next.js shell lands) ──
    root = Path(__file__).resolve().parent.parent
    app.mount("/design-system", StaticFiles(directory=root / "design-system"), name="design-system")

    @app.get("/login", include_in_schema=False)
    def login_page():
        return FileResponse(root / "module1" / "frontend" / "pages" / "login.html")

    @app.get("/", include_in_schema=False)
    def index():
        return RedirectResponse("/login")

    @app.get("/health", tags=["System"])
    def health():
        return {"status": "ok", "version": settings.APP_VERSION,
                "modules_loaded": sorted(set(loaded)), "modules_failed": failed}

    return app


app = create_app()
