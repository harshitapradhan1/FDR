from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_role
from backend.app.models.deposafe_models import User, UserRole
from backend.app.schemas.deposafe_schemas import DemoClockAdvance, DemoClockSet
from backend.app.services.demo_clock import get_simulated_today, advance_demo_clock, set_demo_clock_date
from backend.app.services.workload_service import evaluate_lifecycle_and_workload
from backend.app.services.maturity_radar import run_maturity_radar_scan

router = APIRouter(prefix="/demo-clock", tags=["Demo Simulation Clock"])

@router.get("")
def get_clock(db: Session = Depends(get_db)):
    today = get_simulated_today(db)
    return {
        "current_simulated_date": today.isoformat(),
        "is_simulated": True,
        "note": "Controllable DEMO CLOCK allows real-time evaluation of maturity & reminder workflows."
    }

@router.post("/advance")
def advance_clock(
    req: DemoClockAdvance,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SYSTEM_ADMIN, UserRole.REGIONAL_OFFICER, UserRole.VERIFICATION_OFFICER]))
):
    new_date = advance_demo_clock(
        db=db,
        days=req.days,
        actor_id=current_user.id,
        actor_role=current_user.role.value
    )
    # Immediately evaluate workload and status transitions
    workload = evaluate_lifecycle_and_workload(db)
    # Trigger automated maturity radar scan and escalations
    radar_res = run_maturity_radar_scan(db)
    return {
        "message": f"Demo clock successfully advanced by {req.days} days.",
        "new_simulated_date": new_date.isoformat(),
        "workload_summary": workload["summary"],
        "radar_scan": {
            "notifications_generated": radar_res["notifications_generated_count"],
            "escalations_count": radar_res["escalations_count"]
        }
    }

@router.post("/set")
def set_clock(
    req: DemoClockSet,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SYSTEM_ADMIN, UserRole.REGIONAL_OFFICER, UserRole.VERIFICATION_OFFICER]))
):
    new_date = set_demo_clock_date(
        db=db,
        target_date=req.target_date,
        actor_id=current_user.id,
        actor_role=current_user.role.value
    )
    workload = evaluate_lifecycle_and_workload(db)
    return {
        "message": f"Demo clock set to {new_date.isoformat()}.",
        "new_simulated_date": new_date.isoformat(),
        "workload_summary": workload["summary"]
    }

