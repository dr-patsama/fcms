"""
FCMS Module 1 - Application Entry Point
Run with: uvicorn module1.backend.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.emr_routes import auth_router, patient_router, visit_router
from .api.user_management_routes import router as user_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="FCMS — Fertility Clinic Management System",
        version="2.0.0",
        description="Module 1: EMR — Auth, RBAC, Patients, Visits, SOAP Notes, ICD-10",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────
    app.include_router(auth_router)     # POST /api/v1/auth/login, /register, /mfa/setup, /me
    app.include_router(patient_router)  # POST/GET /api/v1/patients/, GET/PATCH /{id}, history
    app.include_router(visit_router)    # POST /api/v1/visits/, SOAP notes, diagnoses
    app.include_router(user_router)     # GET/PATCH /api/v1/users/ (admin only)

    @app.get("/health", tags=["System"])
    def health():
        return {"status": "ok", "module": "emr", "version": "2.0.0"}

    return app


app = create_app()
