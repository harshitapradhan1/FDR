from typing import Set, Dict, Optional
from backend.app.models.deposafe_models import FDRStatus, ReleaseStatus

class InvalidStateTransitionError(ValueError):
    """Raised when an illegal state machine transition is attempted."""
    def __init__(self, entity_name: str, current_state: str, event: str, allowed_events: Set[str]):
        self.entity_name = entity_name
        self.current_state = current_state
        self.event = event
        self.allowed_events = allowed_events
        super().__init__(
            f"Illegal state transition for {entity_name}: cannot execute event '{event}' from state '{current_state}'. "
            f"Allowed events from this state: {sorted(list(allowed_events)) or 'None (Terminal state)'}"
        )

class FDRStateMachine:
    """
    Explicit Finite State Machine governing the AICTE Security Deposit / FDR Instrument Lifecycle.
    Enforces statutory governance, renewal supersession, and release workflows.
    """
    TRANSITIONS: Dict[FDRStatus, Dict[str, FDRStatus]] = {
        FDRStatus.DRAFT: {
            "SUBMIT": FDRStatus.SUBMITTED,
        },
        FDRStatus.SUBMITTED: {
            "BEGIN_SCRUTINY": FDRStatus.UNDER_SCRUTINY,
            "REJECT": FDRStatus.REJECTED,
        },
        FDRStatus.UNDER_SCRUTINY: {
            "REQUEST_CLARIFICATION": FDRStatus.CLARIFICATION_REQUIRED,
            "APPROVE_COMPLIANCE": FDRStatus.ACTIVE,
            "REJECT": FDRStatus.REJECTED,
        },
        FDRStatus.CLARIFICATION_REQUIRED: {
            "RESUBMIT": FDRStatus.UNDER_SCRUTINY,
            "REJECT": FDRStatus.REJECTED,
        },
        FDRStatus.ACTIVE: {
            "TRIGGER_EXPIRING": FDRStatus.EXPIRING,
            "MATURE": FDRStatus.MATURED,
            "REQUEST_RELEASE": FDRStatus.RELEASE_REQUESTED,
        },
        FDRStatus.EXPIRING: {
            "INITIATE_RENEWAL": FDRStatus.RENEWAL_PENDING,
            "MATURE": FDRStatus.MATURED,
            "REQUEST_RELEASE": FDRStatus.RELEASE_REQUESTED,
        },
        FDRStatus.MATURED: {
            "INITIATE_RENEWAL": FDRStatus.RENEWAL_PENDING,
            "REQUEST_RELEASE": FDRStatus.RELEASE_REQUESTED,
            "FORFEIT_CLOSE": FDRStatus.CLOSED,
        },
        FDRStatus.RENEWAL_PENDING: {
            "COMPLETE_RENEWAL": FDRStatus.SUPERSEDED,
            "CANCEL_RENEWAL": FDRStatus.ACTIVE,
        },
        FDRStatus.RELEASE_REQUESTED: {
            "AUTHORIZE_RELEASE": FDRStatus.RELEASED,
            "REJECT_RELEASE": FDRStatus.ACTIVE,
        },
        FDRStatus.RELEASED: {
            "CLOSE": FDRStatus.CLOSED,
        },
        FDRStatus.SUPERSEDED: {},  # Terminal: immutable predecessor
        FDRStatus.CLOSED: {},      # Terminal: finalized
        FDRStatus.REJECTED: {},    # Terminal: rejected
    }

    NORMALIZE = {
        "PENDING_REVIEW": FDRStatus.DRAFT,
        "UNDER_VERIFICATION": FDRStatus.UNDER_SCRUTINY,
        "COMPLIANT": FDRStatus.ACTIVE,
        "NON_COMPLIANT": FDRStatus.CLARIFICATION_REQUIRED,
        "RENEWAL_DUE": FDRStatus.EXPIRING,
        "RENEWED_SUPERSEDED": FDRStatus.SUPERSEDED,
        "FORFEITED": FDRStatus.CLOSED,
    }

    def __init__(self, current_state: FDRStatus):
        self.state = self.NORMALIZE.get(current_state.value, current_state)

    def trigger(self, event: str, actor_role: Optional[str] = None) -> FDRStatus:
        allowed_map = self.TRANSITIONS.get(self.state, {})
        if event not in allowed_map:
            raise InvalidStateTransitionError(
                entity_name="FDR Instrument",
                current_state=self.state.value,
                event=event,
                allowed_events=set(allowed_map.keys())
            )

        # Statutory Role Guard for Release Authorization
        if event == "AUTHORIZE_RELEASE" and actor_role not in ["COMPETENT_AUTHORITY", "SYSTEM_ADMIN"]:
            raise PermissionError(
                f"Statutory Safeguard Violation: Event 'AUTHORIZE_RELEASE' requires COMPETENT_AUTHORITY role. "
                f"Supplied role: '{actor_role}'."
            )

        new_state = allowed_map[event]
        self.state = new_state
        return new_state

class ReleaseWorkflowStateMachine:
    """
    Explicit Finite State Machine for Security Deposit Release / Refund Workflow.
    Requires dual-verification: Officer scrutiny -> Recommendation -> Competent Authority final order.
    """
    TRANSITIONS: Dict[ReleaseStatus, Dict[str, ReleaseStatus]] = {
        ReleaseStatus.DRAFT: {
            "SUBMIT": ReleaseStatus.SUBMITTED,
        },
        ReleaseStatus.SUBMITTED: {
            "BEGIN_SCRUTINY": ReleaseStatus.UNDER_SCRUTINY,
            "REJECT": ReleaseStatus.REJECTED,
        },
        ReleaseStatus.UNDER_SCRUTINY: {
            "REQUEST_CLARIFICATION": ReleaseStatus.CLARIFICATION_REQUIRED,
            "RECOMMEND": ReleaseStatus.RECOMMENDED_FOR_APPROVAL,
            "REJECT": ReleaseStatus.REJECTED,
        },
        ReleaseStatus.CLARIFICATION_REQUIRED: {
            "RESUBMIT": ReleaseStatus.UNDER_SCRUTINY,
            "REJECT": ReleaseStatus.REJECTED,
        },
        ReleaseStatus.RECOMMENDED_FOR_APPROVAL: {
            "APPROVE": ReleaseStatus.APPROVED,
            "REJECT": ReleaseStatus.REJECTED,
            "SEND_BACK": ReleaseStatus.UNDER_SCRUTINY,
        },
        ReleaseStatus.APPROVED: {
            "DISBURSE_RELEASE": ReleaseStatus.RELEASED,
        },
        ReleaseStatus.RELEASED: {
            "FINALIZE_CLOSURE": ReleaseStatus.CLOSED,
        },
        ReleaseStatus.REJECTED: {},
        ReleaseStatus.CLOSED: {},
    }

    def __init__(self, current_state: ReleaseStatus):
        self.state = current_state

    def trigger(self, event: str, actor_role: Optional[str] = None) -> ReleaseStatus:
        allowed_map = self.TRANSITIONS.get(self.state, {})
        if event not in allowed_map:
            raise InvalidStateTransitionError(
                entity_name="Release Request Workflow",
                current_state=self.state.value,
                event=event,
                allowed_events=set(allowed_map.keys())
            )

        if event == "APPROVE" and actor_role not in ["COMPETENT_AUTHORITY", "SYSTEM_ADMIN"]:
            raise PermissionError(
                f"Statutory Safeguard Violation: Release approval requires COMPETENT_AUTHORITY role. "
                f"Supplied role: '{actor_role}'."
            )

        new_state = allowed_map[event]
        self.state = new_state
        return new_state
