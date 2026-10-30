from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from typing import Dict, Any
from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_role
from backend.app.models.deposafe_models import User, UserRole, ComplianceRule
from backend.app.rules.compliance_engine import get_active_rule
from backend.app.services.audit_service import record_audit_event

router = APIRouter(prefix="/compliance", tags=["Compliance & Regulations"])

@router.get("/rules/active")
def get_active_compliance_rules(db: Session = Depends(get_db)):
    rule = get_active_rule(db)
    return {
        "version_tag": rule.version_tag,
        "effective_from": rule.effective_from.isoformat(),
        "disclaimer": rule.rules_json.get("disclaimer", "ILLUSTRATIVE PLACEHOLDERS - configurable by AICTE Admin"),
        "rules": rule.rules_json
    }

@router.post("/rules/update")
def update_compliance_rules(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SYSTEM_ADMIN]))
):
    version_tag = payload.get("version_tag", f"APH-2024-27.v{date.today().strftime('%Y%m%d')}")
    description = payload.get("description", "Updated AICTE APH Security Deposit Norms")
    rules_json = payload.get("rules", {})

    # Deactivate older rules
    db.query(ComplianceRule).update({ComplianceRule.is_active: False})

    new_rule = ComplianceRule(
        version_tag=version_tag,
        effective_from=date.today(),
        is_active=True,
        description=description,
        rules_json=rules_json,
        created_by=current_user.id
    )
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)

    record_audit_event(
        db=db,
        event_type="COMPLIANCE_RULES_UPDATED",
        entity_type="COMPLIANCE_RULE",
        entity_id=str(new_rule.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={"version_tag": version_tag, "description": description}
    )

    return {
        "message": f"Compliance rules updated to version {version_tag}",
        "rule_id": new_rule.id,
        "version_tag": version_tag
    }

