from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.services.workload_service import evaluate_lifecycle_and_workload

router = APIRouter(prefix="/workload", tags=["Predictive Workload & Lifecycle"])

@router.get("")
def get_workload_forecast(db: Session = Depends(get_db)):
    """
    Returns maturity buckets, escalation queues (T-15, T-30, T-60, T-90, Matured),
    and predictive monthly/regional verification workload forecasts.
    """
    return evaluate_lifecycle_and_workload(db)

