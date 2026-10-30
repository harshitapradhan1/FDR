from datetime import date, timedelta
from sqlalchemy.orm import Session
from backend.app.models.deposafe_models import DemoClock
from backend.app.services.audit_service import record_audit_event

def get_simulated_today(db: Session) -> date:
    clock = db.query(DemoClock).filter(DemoClock.id == 1).first()
    if not clock:
        today = date.today()
        clock = DemoClock(id=1, current_simulated_date=today, offset_days=0)
        db.add(clock)
        db.commit()
        db.refresh(clock)
    return clock.current_simulated_date

def advance_demo_clock(db: Session, days: int, actor_id: int = None, actor_role: str = None) -> date:
    clock = db.query(DemoClock).filter(DemoClock.id == 1).first()
    if not clock:
        current_date = date.today()
        clock = DemoClock(id=1, current_simulated_date=current_date, offset_days=0)
        db.add(clock)
    
    clock.offset_days += days
    clock.current_simulated_date = clock.current_simulated_date + timedelta(days=days)
    db.commit()
    db.refresh(clock)

    record_audit_event(
        db=db,
        event_type="DEMO_CLOCK_ADVANCED",
        entity_type="SYSTEM",
        entity_id="DEMO_CLOCK",
        actor_id=actor_id,
        actor_role=actor_role,
        payload={
            "advanced_by_days": days,
            "new_simulated_date": clock.current_simulated_date.isoformat(),
            "total_offset_days": clock.offset_days
        }
    )
    return clock.current_simulated_date

def set_demo_clock_date(db: Session, target_date: date, actor_id: int = None, actor_role: str = None) -> date:
    clock = db.query(DemoClock).filter(DemoClock.id == 1).first()
    if not clock:
        clock = DemoClock(id=1, current_simulated_date=target_date, offset_days=0)
        db.add(clock)
    
    old_date = clock.current_simulated_date
    delta_days = (target_date - date.today()).days
    clock.current_simulated_date = target_date
    clock.offset_days = delta_days
    db.commit()
    db.refresh(clock)

    record_audit_event(
        db=db,
        event_type="DEMO_CLOCK_SET",
        entity_type="SYSTEM",
        entity_id="DEMO_CLOCK",
        actor_id=actor_id,
        actor_role=actor_role,
        payload={
            "old_date": old_date.isoformat(),
            "new_simulated_date": target_date.isoformat(),
            "offset_days": delta_days
        }
    )
    return clock.current_simulated_date

