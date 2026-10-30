import pytest
from backend.app.models.deposafe_models import FDRStatus, ReleaseStatus
from backend.app.state_machines.fdr_state_machine import (
    FDRStateMachine, ReleaseWorkflowStateMachine, InvalidStateTransitionError
)

def test_fdr_lifecycle_valid_path():
    sm = FDRStateMachine(FDRStatus.DRAFT)
    assert sm.state == FDRStatus.DRAFT

    # 1. Draft -> Submit -> Submitted
    sm.trigger("SUBMIT")
    assert sm.state == FDRStatus.SUBMITTED

    # 2. Submitted -> Begin Scrutiny -> Under Scrutiny
    sm.trigger("BEGIN_SCRUTINY")
    assert sm.state == FDRStatus.UNDER_SCRUTINY

    # 3. Under Scrutiny -> Request Clarification -> Clarification Required
    sm.trigger("REQUEST_CLARIFICATION")
    assert sm.state == FDRStatus.CLARIFICATION_REQUIRED

    # 4. Clarification Required -> Resubmit -> Under Scrutiny
    sm.trigger("RESUBMIT")
    assert sm.state == FDRStatus.UNDER_SCRUTINY

    # 5. Under Scrutiny -> Approve Compliance -> Active
    sm.trigger("APPROVE_COMPLIANCE")
    assert sm.state == FDRStatus.ACTIVE

    # 6. Active -> Trigger Expiring (T-30 / T-15) -> Expiring
    sm.trigger("TRIGGER_EXPIRING")
    assert sm.state == FDRStatus.EXPIRING

    # 7. Expiring -> Initiate Renewal -> Renewal Pending
    sm.trigger("INITIATE_RENEWAL")
    assert sm.state == FDRStatus.RENEWAL_PENDING

    # 8. Renewal Pending -> Complete Renewal -> Superseded (Terminal)
    sm.trigger("COMPLETE_RENEWAL")
    assert sm.state == FDRStatus.SUPERSEDED

def test_fdr_release_path_and_role_guards():
    sm = FDRStateMachine(FDRStatus.ACTIVE)

    # Active -> Request Release
    sm.trigger("REQUEST_RELEASE")
    assert sm.state == FDRStatus.RELEASE_REQUESTED

    # Attempting release authorization without Competent Authority role MUST fail
    with pytest.raises(PermissionError) as exc_info:
        sm.trigger("AUTHORIZE_RELEASE", actor_role="INSTITUTION_USER")
    assert "Statutory Safeguard Violation" in str(exc_info.value)

    # Authorizing with Competent Authority succeeds
    sm.trigger("AUTHORIZE_RELEASE", actor_role="COMPETENT_AUTHORITY")
    assert sm.state == FDRStatus.RELEASED

    # Released -> Close -> Closed
    sm.trigger("CLOSE")
    assert sm.state == FDRStatus.CLOSED

def test_fdr_lifecycle_illegal_transitions_raise_error():
    # Attempting to jump directly from DRAFT to ACTIVE
    sm = FDRStateMachine(FDRStatus.DRAFT)
    with pytest.raises(InvalidStateTransitionError) as exc:
        sm.trigger("APPROVE_COMPLIANCE")
    assert "cannot execute event 'APPROVE_COMPLIANCE' from state 'DRAFT'" in str(exc.value)

    # Attempting to resurrect terminal SUPERSEDED instrument
    term_sm = FDRStateMachine(FDRStatus.SUPERSEDED)
    with pytest.raises(InvalidStateTransitionError) as exc2:
        term_sm.trigger("SUBMIT")
    assert "None (Terminal state)" in str(exc2.value)

def test_release_workflow_valid_path():
    sm = ReleaseWorkflowStateMachine(ReleaseStatus.DRAFT)
    assert sm.state == ReleaseStatus.DRAFT

    sm.trigger("SUBMIT")
    assert sm.state == ReleaseStatus.SUBMITTED

    sm.trigger("BEGIN_SCRUTINY")
    assert sm.state == ReleaseStatus.UNDER_SCRUTINY

    sm.trigger("RECOMMEND")
    assert sm.state == ReleaseStatus.RECOMMENDED_FOR_APPROVAL

    # Competent Authority approval
    sm.trigger("APPROVE", actor_role="COMPETENT_AUTHORITY")
    assert sm.state == ReleaseStatus.APPROVED

    sm.trigger("DISBURSE_RELEASE")
    assert sm.state == ReleaseStatus.RELEASED

    sm.trigger("FINALIZE_CLOSURE")
    assert sm.state == ReleaseStatus.CLOSED

def test_release_workflow_illegal_transitions():
    sm = ReleaseWorkflowStateMachine(ReleaseStatus.DRAFT)
    with pytest.raises(InvalidStateTransitionError):
        sm.trigger("DISBURSE_RELEASE")

    rec_sm = ReleaseWorkflowStateMachine(ReleaseStatus.RECOMMENDED_FOR_APPROVAL)
    with pytest.raises(PermissionError):
        rec_sm.trigger("APPROVE", actor_role="VERIFICATION_OFFICER")

