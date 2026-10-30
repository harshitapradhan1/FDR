from datetime import date
from collections import defaultdict
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.models.deposafe_models import FDR, Institution, FDRStatus
from backend.app.services.demo_clock import get_simulated_today

def evaluate_lifecycle_and_workload(db: Session) -> Dict[str, Any]:
    """
    Evaluates deposit maturities against the active Demo Clock.
    Computes predictive workload forecasts and triggers reminder stages.
    """
    simulated_today = get_simulated_today(db)
    
    fdrs = db.query(FDR).filter(
        FDR.status.notin_([FDRStatus.RELEASED, FDRStatus.FORFEITED, FDRStatus.RENEWED_SUPERSEDED])
    ).all()

    buckets = {
        "MATURED_OVERDUE": [],       # <= 0 days
        "CRITICAL_ESCALATION": [],  # 1 to 15 days
        "WARNING_DUE_SOON": [],     # 16 to 30 days
        "UPCOMING_REMINDER": [],    # 31 to 60 days
        "EARLY_NOTICE": [],         # 61 to 90 days
        "ACTIVE_HEALTHY": []        # > 90 days
    }

    by_month = defaultdict(float)
    by_region = defaultdict(lambda: {"count": 0, "total_amount": 0.0})

    status_updates_count = 0

    for f in fdrs:
        inst = db.query(Institution).filter(Institution.id == f.institution_id).first()
        days_remaining = (f.maturity_date - simulated_today).days
        
        item = {
            "fdr_id": f.id,
            "fdr_number": f.fdr_number,
            "bank_name": f.bank_name,
            "amount": f.amount,
            "institution_name": inst.name if inst else "Unknown",
            "regional_office": inst.regional_office if inst else "General",
            "issue_date": f.issue_date.isoformat(),
            "maturity_date": f.maturity_date.isoformat(),
            "days_remaining": days_remaining,
            "current_status": f.status.value,
            "review_priority_score": f.review_priority_score
        }

        # Check if status should transition to RENEWAL_DUE
        if days_remaining <= 30 and f.status in [FDRStatus.COMPLIANT, FDRStatus.UNDER_VERIFICATION, FDRStatus.PENDING_REVIEW]:
            f.status = FDRStatus.RENEWAL_DUE
            status_updates_count += 1

        if days_remaining <= 0:
            buckets["MATURED_OVERDUE"].append(item)
        elif days_remaining <= 15:
            buckets["CRITICAL_ESCALATION"].append(item)
        elif days_remaining <= 30:
            buckets["WARNING_DUE_SOON"].append(item)
        elif days_remaining <= 60:
            buckets["UPCOMING_REMINDER"].append(item)
        elif days_remaining <= 90:
            buckets["EARLY_NOTICE"].append(item)
        else:
            buckets["ACTIVE_HEALTHY"].append(item)

        # Workload forecasting metrics
        if 0 <= days_remaining <= 365:
            month_key = f.maturity_date.strftime("%b %Y")
            by_month[month_key] += f.amount
        
        reg_name = inst.regional_office if inst else "Northern"
        by_region[reg_name]["count"] += 1
        by_region[reg_name]["total_amount"] += f.amount

    if status_updates_count > 0:
        db.commit()

    monthly_forecast = [{"month": k, "amount": v} for k, v in by_month.items()]
    regional_distribution = [{"region": k, "count": v["count"], "total_amount": v["total_amount"]} for k, v in by_region.items()]

    return {
        "simulated_today": simulated_today.isoformat(),
        "summary": {
            "matured_overdue": len(buckets["MATURED_OVERDUE"]),
            "critical_escalation_t15": len(buckets["CRITICAL_ESCALATION"]),
            "warning_due_soon_t30": len(buckets["WARNING_DUE_SOON"]),
            "upcoming_t60": len(buckets["UPCOMING_REMINDER"]),
            "early_notice_t90": len(buckets["EARLY_NOTICE"]),
            "active_healthy": len(buckets["ACTIVE_HEALTHY"]),
            "total_active_instruments": len(fdrs)
        },
        "buckets": buckets,
        "monthly_forecast": monthly_forecast,
        "regional_distribution": regional_distribution
    }

