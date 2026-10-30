import os
from celery import Celery
from celery.schedules import crontab
from datetime import date
from backend.app.core.database import SessionLocal
from backend.app.services.workload_service import evaluate_lifecycle_and_workload
from backend.app.services.audit_service import record_audit_event

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("deposafe_scheduler", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    beat_schedule={
        "evaluate-maturities-every-hour": {
            "task": "backend.app.services.celery_worker.evaluate_maturities_job",
            "schedule": 3600.0, # Every 1 hour
        },
    }
)

@celery_app.task
def evaluate_maturities_job():
    """
    Automated background worker job evaluated independently of whether frontend is open.
    Escalates overdue and T-15 deposits.
    """
    db = SessionLocal()
    try:
        workload = evaluate_lifecycle_and_workload(db)
        summary = workload["summary"]
        
        record_audit_event(
            db=db,
            event_type="CELERY_BEAT_MATURITY_ESCALATION_CHECK",
            entity_type="SCHEDULER",
            entity_id="CELERY_BEAT",
            actor_id=None,
            actor_role="SYSTEM_SCHEDULER",
            payload={
                "matured_overdue": summary["matured_overdue"],
                "critical_escalation_t15": summary["critical_escalation_t15"],
                "warning_due_soon_t30": summary["warning_due_soon_t30"]
            }
        )
        return summary
    finally:
        db.close()

