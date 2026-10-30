import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.app.core.config import settings
from backend.app.core.database import Base, engine, SessionLocal
from backend.app.api import auth, fdrs, institutions, compliance, democlock, graph, workload, audit, evaluation, mock_bank
from backend.app.services.seed_service import seed_database_if_empty

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="DepoSafe - AI-Assisted Security Deposit / FDR Intelligence & Management Portal for AICTE Regulation Bureau",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount storage directory for document viewing
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
app.mount("/storage", StaticFiles(directory=settings.STORAGE_DIR), name="storage")

# Include Routers under standard API_V1_STR (/api/v1)
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(institutions.router, prefix=settings.API_V1_STR)
app.include_router(fdrs.router, prefix=f"{settings.API_V1_STR}/fdrs")
app.include_router(fdrs.router, prefix=f"{settings.API_V1_STR}/fdr")
app.include_router(compliance.router, prefix=settings.API_V1_STR)
app.include_router(democlock.router, prefix=settings.API_V1_STR)
app.include_router(graph.router, prefix=settings.API_V1_STR)
app.include_router(workload.router, prefix=settings.API_V1_STR)
app.include_router(audit.router, prefix=settings.API_V1_STR)
app.include_router(evaluation.router, prefix=settings.API_V1_STR)
app.include_router(mock_bank.router, prefix=settings.API_V1_STR)

# Direct root-level route aliases for SIH prompt specifications:
# POST /auth/login, /institutions, GET /institutions, POST /fdr/upload, GET /fdr/{id}, GET /fdr
app.include_router(auth.router, prefix="")
app.include_router(institutions.router, prefix="")
app.include_router(fdrs.router, prefix="/fdrs")
app.include_router(fdrs.router, prefix="/fdr")
app.include_router(mock_bank.router, prefix="")

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        seed_database_if_empty(db)
    finally:
        db.close()

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "disclaimer": "AI is advisory. Versioned rules dictate compliance.",
        "storage": os.path.abspath(settings.STORAGE_DIR)
    }
