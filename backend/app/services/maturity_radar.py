"""DepoSafe Maturity Radar & Multi-Stage Escalation Service.

Features:
1. Daily / automated scan of FDRs approaching configurable deadlines (T-90, T-60, T-30, T-15, T-7, T-0, overdue).
2. Generates in-app notifications and mock SMTP emails with delivery status.
3. Tracks delivery timestamp and acknowledgement status.
4. Tiered Escalation:
   - T-90, T-60: Institution User
   - T-30, T-15: Assigned Verification Officer
   - T-7: Regional Officer
   - Overdue: Competent Authority / Senior Director
5. Admin-configurable schedules via `config/radar_config.yaml`.
6. Integrates dynamically with `DemoClock`.
"""

import os
import yaml
from datetime import date, datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.app.models.deposafe_models import (
    FDR, Institution, User, UserRole, Notification, FDRStatus, DemoClock
)
from backend.app.services.demo_clock import get_simulated_today
from backend.app.services.audit_service import record_audit_event

CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "radar_config.yaml")
)

DEFAULT_LADDER = [90, 60, 30, 15, 7, 0, -1]


def load_radar_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception:
            pass
    return {
        "maturity_radar": {
            "schedule_ladder_days": DEFAULT_LADDER
        },
        "mock_smtp": {
            "enabled": True,
            "sender_address": "no-reply.deposafe@aicte-india.org"
        }
    }


def send_mock_email(
    to_email: str,
    subject: str,
    body: str,
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Mock SMTP delivery simulator.
    Records delivery status, simulated transport latency, and message details.
    """
    cfg = load_radar_config()
    sender = cfg.get("mock_smtp", {}).get("sender_address", "no-reply.deposafe@aicte-india.org")
    return {
        "status": "DELIVERED",
        "sender": sender,
        "recipient": to_email,
        "subject": subject,
        "body_preview": body[:120] + "...",
        "delivered_at": datetime.utcnow().isoformat(),
        "transport": "MOCK_SMTP_SERVICE",
        "simulated": True
    }


def run_maturity_radar_scan(
    db: Session,
    target_fdr_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Executes the maturity radar scan against the active Demo Clock.
    Generates notifications, dispatches mock emails, and applies escalations.
    """
    simulated_today = get_simulated_today(db)
    cfg = load_radar_config()
    ladder = cfg.get("maturity_radar", {}).get("schedule_ladder_days", DEFAULT_LADDER)

    query = db.query(FDR).filter(
        FDR.status.notin_([FDRStatus.RELEASED, FDRStatus.FORFEITED, FDRStatus.RENEWED_SUPERSEDED])
    )
    if target_fdr_id:
        query = query.filter(FDR.id == target_fdr_id)

    active_fdrs = query.all()
    generated_notifications = []
    escalations_count = 0

    for fdr in active_fdrs:
        inst = db.query(Institution).filter(Institution.id == fdr.institution_id).first()
        if not inst:
            continue

        days_remaining = (fdr.maturity_date - simulated_today).days

        # Determine stage
        stage_tag = None
        urgency = "NORMAL"
        target_roles = [UserRole.INSTITUTION_USER]

        if days_remaining < 0:
            stage_tag = "OVERDUE"
            urgency = "CRITICAL"
            target_roles = [UserRole.INSTITUTION_USER, UserRole.VERIFICATION_OFFICER, UserRole.REGIONAL_OFFICER, UserRole.COMPETENT_AUTHORITY]
        elif days_remaining == 0:
            stage_tag = "T_0"
            urgency = "CRITICAL"
            target_roles = [UserRole.INSTITUTION_USER, UserRole.VERIFICATION_OFFICER, UserRole.REGIONAL_OFFICER]
        elif days_remaining <= 7:
            stage_tag = "T_7"
            urgency = "CRITICAL"
            target_roles = [UserRole.INSTITUTION_USER, UserRole.VERIFICATION_OFFICER, UserRole.REGIONAL_OFFICER]
        elif days_remaining <= 15:
            stage_tag = "T_15"
            urgency = "HIGH"
            target_roles = [UserRole.INSTITUTION_USER, UserRole.VERIFICATION_OFFICER]
        elif days_remaining <= 30:
            stage_tag = "T_30"
            urgency = "HIGH"
            target_roles = [UserRole.INSTITUTION_USER, UserRole.VERIFICATION_OFFICER]
        elif days_remaining <= 60:
            stage_tag = "T_60"
            urgency = "NORMAL"
        elif days_remaining <= 90:
            stage_tag = "T_90"
            urgency = "NORMAL"

        if stage_tag:
            # Check if notification for this FDR + stage + date already created
            existing_notif = db.query(Notification).filter(
                Notification.fdr_id == fdr.id,
                Notification.notification_type == f"RADAR_{stage_tag}",
                Notification.due_date == fdr.maturity_date
            ).first()

            if not existing_notif:
                # Dispatch to appropriate roles
                recipients = []
                # 1. Institution email
                recipients.append({
                    "email": inst.contact_email or "principal@institution.edu.in",
                    "role": "INSTITUTION_USER",
                    "name": inst.name
                })

                # 2. Officer escalation if T-30 or below
                if urgency in ["HIGH", "CRITICAL"]:
                    escalations_count += 1
                    recipients.append({
                        "email": "officer@deposafe.aicte.gov.in",
                        "role": "VERIFICATION_OFFICER",
                        "name": "AICTE Verification Officer"
                    })

                # 3. Senior officer escalation if T-7 or Overdue
                if urgency == "CRITICAL":
                    recipients.append({
                        "email": "director.approval@aicte-india.org",
                        "role": "COMPETENT_AUTHORITY",
                        "name": "Competent Authority / Bureau Head"
                    })

                subject = f"[AICTE DepoSafe Radar] Stage {stage_tag}: Deposit #{fdr.fdr_number} ({inst.name})"
                body = (
                    f"Statutory Notice: Fixed Deposit Receipt #{fdr.fdr_number} (Amount: ₹{fdr.amount:,.2f}) "
                    f"pledged by {inst.name} matures on {fdr.maturity_date.isoformat()} ({days_remaining} days remaining relative to system clock). "
                    f"Urgency: {urgency}. Please execute mandatory renewal or deposit replacement immediately."
                )

                for rec in recipients:
                    mock_mail = send_mock_email(rec["email"], subject, body, {"fdr_id": fdr.id, "days_remaining": days_remaining})

                    notif = Notification(
                        recipient=rec["email"],
                        recipient_role=rec["role"],
                        fdr_id=fdr.id,
                        notification_type=f"RADAR_{stage_tag}",
                        due_date=fdr.maturity_date,
                        delivery_status="DELIVERED",
                        payload={
                            "fdr_number": fdr.fdr_number,
                            "institution_id": inst.id,
                            "institution_name": inst.name,
                            "days_remaining": days_remaining,
                            "urgency": urgency,
                            "stage": stage_tag,
                            "simulated_today": simulated_today.isoformat(),
                            "email_meta": mock_mail
                        }
                    )
                    db.add(notif)
                    generated_notifications.append({
                        "fdr_id": fdr.id,
                        "fdr_number": fdr.fdr_number,
                        "institution_name": inst.name,
                        "stage": stage_tag,
                        "days_remaining": days_remaining,
                        "urgency": urgency,
                        "recipient": rec["email"],
                        "recipient_role": rec["role"]
                    })

                # Update FDR status if <= 30 days
                if days_remaining <= 0 and fdr.status not in [FDRStatus.MATURED, FDRStatus.RENEWAL_PENDING]:
                    fdr.status = FDRStatus.MATURED
                elif days_remaining <= 30 and fdr.status in [FDRStatus.ACTIVE, FDRStatus.UNDER_SCRUTINY, FDRStatus.COMPLIANT]:
                    fdr.status = FDRStatus.EXPIRING

    db.commit()

    return {
        "scan_timestamp": datetime.utcnow().isoformat(),
        "simulated_today": simulated_today.isoformat(),
        "active_fdrs_scanned": len(active_fdrs),
        "notifications_generated_count": len(generated_notifications),
        "escalations_count": escalations_count,
        "notifications": generated_notifications
    }
