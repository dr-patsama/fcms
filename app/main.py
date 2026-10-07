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
from app.dashboards.routes import router as dashboard_router

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
    ("module10.backend.api.timeline_routes",       ["router"]),
    ("journey.backend.api.journey_routes",         ["router"]),   # Journey layer: cycle spine · lab chain · cryo · KPIs
    ("journey.backend.api.portal_routes",          ["router"]),   # Patient App API (LINE Mini App + PWA)
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

    app.include_router(dashboard_router)
    app.mount("/static", StaticFiles(directory=root / "app" / "static"), name="app-static")

    @app.get("/board/opd", include_in_schema=False)
    def opd_board():
        return FileResponse(root / "app" / "static" / "opd.html")

    @app.get("/board/embryo", include_in_schema=False)
    def embryo_board():
        return FileResponse(root / "app" / "static" / "embryo.html")

    tl_dir = root / "module10" / "frontend" / "timeline"
    app.mount("/timeline/vendor", StaticFiles(directory=tl_dir / "vendor"), name="timeline-vendor")

    @app.get("/timeline", include_in_schema=False)
    def timeline_page():
        return FileResponse(tl_dir / "index.html")

    @app.get("/dashboard", include_in_schema=False)
    def dashboard_page():
        return FileResponse(root / "app" / "static" / "dashboard.html")

    # ── Journey layer pages (React in-browser, vendored libs, LIFE by Dr. Pat design system) ──
    j_dir = root / "journey" / "frontend"
    app.mount("/journey/vendor", StaticFiles(directory=j_dir / "vendor"), name="journey-vendor")
    app.mount("/brand", StaticFiles(directory=root / "module1" / "frontend" / "public"), name="brand")   # logo.png
    app.mount("/journey/static", StaticFiles(directory=j_dir / "pages"), name="journey-static")
    JOURNEY_PAGES = {
        "/cycles": "cycles.html",            # cycle list + create from package
        "/cycles/{cycle_id}": "cycle.html",  # cycle workspace (chart · monitoring · tasks · observation · cryo · outcome)
        "/lab/todo": "lab_todo.html",        # Lab To-Do list + labels
        "/lab/witness": "witness.html",      # tablet witnessing (camera / scanner)
        "/admin/packages": "packages.html",  # package & consent template admin
        "/insight": "insight.html",          # KPIs
        "/desk": "desk.html",                # front desk: today's queue, booking requests, cryo due
        "/portal": "portal.html",            # Patient App (LIFF + PWA)
    }
    for route, fname in JOURNEY_PAGES.items():
        def _make(fn=fname):
            def _page(cycle_id: str = None):
                return FileResponse(j_dir / "pages" / fn)
            return _page
        app.get(route, include_in_schema=False)(_make())

    @app.get("/portal/manifest.webmanifest", include_in_schema=False)
    def portal_manifest():
        return FileResponse(j_dir / "pages" / "manifest.webmanifest", media_type="application/manifest+json")

    @app.get("/portal/sw.js", include_in_schema=False)
    def portal_sw():
        return FileResponse(j_dir / "pages" / "sw.js", media_type="application/javascript")

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
