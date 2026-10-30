"""Standalone FastAPI application for Simulated Core Banking Service (CBS / SFMS).
Can be deployed as a separate microservice container in docker-compose.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.mock_bank import router as mock_bank_router

app = FastAPI(
    title="DepoSafe Simulated Core Banking Gateway",
    version="1.0.0",
    description="Standalone simulated CBS/SFMS gateway for AICTE Security Deposit verification demos. All responses are simulated."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mock_bank_router, prefix="/api/v1")
app.include_router(mock_bank_router, prefix="")

@app.get("/")
def root():
    return {
        "service": "DepoSafe Simulated Core Banking Service",
        "status": "online",
        "disclaimer": "SIMULATED, not a real bank verification"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.mock_bank_app:app", host="0.0.0.0", port=8001, reload=True)
