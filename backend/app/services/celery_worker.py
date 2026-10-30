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


@celery_app.task
def process_document_pipeline_task(fdr_id: int, doc_id: int, file_path: str, declared_details: dict = None):
    """
    Async Celery task executing the complete AI document pipeline:
    OCR/text -> type classification -> layout extraction -> validation -> database persistence.
    """
    from backend.app.services.document_pipeline import run_document_ai_pipeline, persist_pipeline_results_to_db
    
    db = SessionLocal()
    try:
        pipeline_result = run_document_ai_pipeline(file_path, declared_details)
        persist_pipeline_results_to_db(db, fdr_id, doc_id, pipeline_result)

        record_audit_event(
            db=db,
            event_type="ASYNC_CELERY_AI_PIPELINE_COMPLETED",
            entity_type="FDR_DOCUMENT",
            entity_id=str(doc_id),
            actor_id=None,
            actor_role="CELERY_WORKER",
            payload={
                "fdr_id": fdr_id,
                "doc_type": pipeline_result["document_classification"]["doc_type"],
                "layout_id": pipeline_result["layout_classification"]["layout_id"],
                "validation_status": pipeline_result["field_validation"]["overall_status"],
                "low_confidence_fields": pipeline_result["low_confidence_fields"]
            }
        )
        return {
            "status": "COMPLETED",
            "doc_id": doc_id,
            "validation_status": pipeline_result["field_validation"]["overall_status"],
            "ui_wording": pipeline_result["field_validation"]["ui_wording"]
        }
    finally:
        db.close()


