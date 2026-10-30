# DepoSafe - State Machine Architecture & Transitions

This document defines the formal state machines governing the AICTE Security Deposit lifecycle and release approval workflow.

---

## 1. FDR Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> DRAFT : Created by Institution
    DRAFT --> SUBMITTED : SUBMIT
    SUBMITTED --> UNDER_SCRUTINY : BEGIN_SCRUTINY
    SUBMITTED --> REJECTED : REJECT

    UNDER_SCRUTINY --> CLARIFICATION_REQUIRED : REQUEST_CLARIFICATION
    CLARIFICATION_REQUIRED --> UNDER_SCRUTINY : RESUBMIT
    CLARIFICATION_REQUIRED --> REJECTED : REJECT

    UNDER_SCRUTINY --> ACTIVE : APPROVE_COMPLIANCE
    UNDER_SCRUTINY --> REJECTED : REJECT

    ACTIVE --> EXPIRING : TRIGGER_EXPIRING (T-30 / T-15 Days)
    ACTIVE --> MATURED : MATURE (Maturity Date Reached)
    ACTIVE --> RELEASE_REQUESTED : REQUEST_RELEASE

    EXPIRING --> RENEWAL_PENDING : INITIATE_RENEWAL
    EXPIRING --> MATURED : MATURE
    EXPIRING --> RELEASE_REQUESTED : REQUEST_RELEASE

    MATURED --> RENEWAL_PENDING : INITIATE_RENEWAL
    MATURED --> RELEASE_REQUESTED : REQUEST_RELEASE
    MATURED --> CLOSED : FORFEIT_CLOSE

    RENEWAL_PENDING --> SUPERSEDED : COMPLETE_RENEWAL (New Instrument Linked)
    RENEWAL_PENDING --> ACTIVE : CANCEL_RENEWAL

    RELEASE_REQUESTED --> RELEASED : AUTHORIZE_RELEASE [Competent Authority Only]
    RELEASE_REQUESTED --> ACTIVE : REJECT_RELEASE

    RELEASED --> CLOSED : CLOSE
    CLOSED --> [*]
    SUPERSEDED --> [*] : Immutable Historical Instrument
    REJECTED --> [*]
```

### Transition Guards & Invariants
1. **SUPERSEDED State**: An instrument that is superseded by a renewal becomes immutable. It can never be edited, deleted, or resurrected.
2. **Release Authorization Guard**: The `AUTHORIZE_RELEASE` transition can **only** be triggered by the `COMPETENT_AUTHORITY` role.
3. **Invalid Transitions**: Any transition not defined above raises `InvalidStateTransitionError`.

---

## 2. Release & Refund Workflow State Machine

```mermaid
stateDiagram-v2
    [*] --> Draft : Institution Prepares Request
    Draft --> Submitted : SUBMIT (NOC & Closure Proof)
    Submitted --> Under_Scrutiny : BEGIN_SCRUTINY
    Submitted --> Rejected : REJECT

    Under_Scrutiny --> Clarification_Required : REQUEST_CLARIFICATION
    Clarification_Required --> Under_Scrutiny : RESUBMIT
    Clarification_Required --> Rejected : REJECT

    Under_Scrutiny --> Recommended_For_Approval : RECOMMEND (Regional Officer)
    Under_Scrutiny --> Rejected : REJECT

    Recommended_For_Approval --> Approved : APPROVE [Competent Authority Only]
    Recommended_For_Approval --> Rejected : REJECT
    Recommended_For_Approval --> Under_Scrutiny : SEND_BACK

    Approved --> Released : DISBURSE_RELEASE (Official Order Ref)
    Released --> Closed : FINALIZE_CLOSURE
    Closed --> [*]
    Rejected --> [*]
```

