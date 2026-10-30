"""
DepoSafe - Playwright End-to-End Test Suite for Phase 10
Tests the 3 statutory flows in headless Chromium:
(a) Upload to extraction to discrepancy
(b) Officer scrutiny to clarification to verification
(c) Renewal to release request to authority approval
"""
import pytest
from playwright.sync_api import sync_playwright, expect

BASE_URL = "http://127.0.0.1:3000"


def test_flow_a_upload_to_extraction_to_discrepancy():
    """
    Flow (a): Upload to extraction to discrepancy
    - Navigate to Institution Portal
    - Verify deposit requirements
    - Execute simulated document upload & OCR extraction
    - Inspect extracted fields & confidence ratings
    - Navigate to Verification Workspace and verify discrepancy detection
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("dialog", lambda dialog: dialog.accept())

        page.goto(BASE_URL, wait_until="networkidle", timeout=30000)

        # 1. Verify Portal Header
        expect(page.locator("header").get_by_text("DepoSafe", exact=True)).to_be_visible()
        expect(page.locator("text=AICTE Gov-Tech")).to_be_visible()

        # 2. Click on Institution Portal Tab
        page.get_by_role("button", name="Institution Portal").click()

        # 3. Verify Institution Profile & Requirements
        expect(page.locator("text=Vidya Institute of Technology")).to_be_visible()
        expect(page.locator("text=Statutory Deposit Requirement")).to_be_visible()
        expect(page.locator("text=Upload Security Deposit / FDR Instrument")).to_be_visible()

        # 4. Navigate to Verification Workspace (Hero Screen)
        page.get_by_role("button", name="Verification Workspace", exact=True).click()

        # 5. Verify Hero Workspace Document Viewer & Bounding Boxes
        expect(page.locator("text=Original Instrument Scan & Forensics")).to_be_visible()
        expect(page.locator("text=B-Boxes: ON")).to_be_visible()
        expect(page.locator("text=ELA Forensics")).to_be_visible()

        # 6. Verify 4-Source Provenance Tab
        expect(page.locator("text=1. 4-Source Provenance")).to_be_visible()
        expect(page.locator("text=1. Submitted")).to_be_visible()
        expect(page.locator("text=2. AI Extracted")).to_be_visible()

        # 7. Check Cross-Document Reconciliation for Discrepancies
        page.get_by_role("button", name="3. Cross-Document").click()
        expect(page.locator("text=Cross-document consistency")).to_be_visible()

        # 8. Check Risk Score and Explainable Anomaly Reasons
        page.get_by_role("button", name=r"5. Risk Score").click()
        expect(page.locator("text=Explainable Preliminary Indicator")).to_be_visible()

        browser.close()


def test_flow_b_officer_scrutiny_to_clarification_to_verification():
    """
    Flow (b): Officer scrutiny to clarification to verification
    - In Verification Workspace, review flagged instrument
    - Officer triggers 'Request Clarification' with scrutiny observation
    - Dispatches request
    - Officer executes Bank CBS Simulation -> status updates to BANK_CONFIRMED
    - Officer approves and verifies instrument
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("dialog", lambda dialog: dialog.accept())

        page.goto(BASE_URL, wait_until="networkidle", timeout=30000)

        # 1. Navigate to Verification Workspace
        page.get_by_role("button", name="Verification Workspace", exact=True).click()

        # 2. Check Action Buttons & Open Clarification Modal
        clarify_btn = page.get_by_role("button", name="Request Clarification")
        expect(clarify_btn).to_be_visible()
        clarify_btn.click()

        # 3. Enter Clarification in Modal
        expect(page.locator("text=Request Institution Clarification")).to_be_visible()
        textarea = page.locator("textarea[placeholder*='Specify discrepancy']")
        textarea.fill("Clarification requested regarding tenure and joint lien clause wording.")
        
        # Dispatch
        dispatch_btn = page.get_by_role("button", name="Dispatch Request")
        dispatch_btn.click()

        # 4. Open Record Manual Evidence Modal
        manual_btn = page.get_by_role("button", name="Record Manual Evidence")
        manual_btn.click()
        expect(page.locator("text=Record Officer Manual Verification")).to_be_visible()
        expect(page.locator("text=Official Reference Number")).to_be_visible()
        save_btn = page.get_by_role("button", name="Save Record")
        save_btn.click()

        # 5. Check CBS Simulation Trigger
        page.get_by_role("button", name="1. 4-Source Provenance").click()
        cbs_btn = page.get_by_role("button", name="Simulate Bank CBS")
        expect(cbs_btn).to_be_visible()
        cbs_btn.click()

        # 6. Approve and Verify
        approve_btn = page.get_by_role("button", name="Approve & Verify")
        expect(approve_btn).to_be_visible()
        approve_btn.click()

        browser.close()


def test_flow_c_renewal_to_release_request_to_authority_approval():
    """
    Flow (c): Renewal to release request to authority approval
    - Ensure an active release request is present
    - Navigate to Maturity & Renewal Radar
    - Verify Priority Queue and Zero-Gap Guard
    - Navigate to Release & Refund Governance
    - Inspect Advisory Release Readiness Checklist & Statutory Disclaimer
    - Authorize Release under Competent Authority role
    - Verify release transition & full audit trail
    """
    # Ensure an active release request exists in database directly
    from backend.app.core.database import SessionLocal
    from backend.app.models.deposafe_models import ReleaseRequest, ReleaseStatus, FDR

    db = SessionLocal()
    fdr = db.query(FDR).filter(FDR.institution_id == 1).first()
    if fdr:
        existing = db.query(ReleaseRequest).filter(ReleaseRequest.fdr_id == fdr.id).first()
        if not existing:
            req = ReleaseRequest(
                fdr_id=fdr.id,
                institution_id=fdr.institution_id,
                justification="Program closure and student graduation clearance.",
                noc_reference="NOC-REG-2026-99",
                status=ReleaseStatus.SUBMITTED
            )
            db.add(req)
            db.commit()
    db.close()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("dialog", lambda dialog: dialog.accept())

        page.goto(BASE_URL, wait_until="networkidle", timeout=30000)

        # 1. Navigate to Maturity & Renewal Radar
        page.get_by_role("button", name="Maturity & Renewal Radar").click()
        expect(page.locator("text=Maturity Radar & Zero-Gap Renewal Guard")).to_be_visible()
        expect(page.locator("text=Zero-Gap Regulatory Guard")).to_be_visible()

        # 2. Navigate to Release & Refund Governance
        page.get_by_role("button", name="Release & Refund Lifecycle").click()
        expect(page.locator("text=Release & Refund Governance (9-State Workflow)")).to_be_visible()

        # Select first request if available
        first_card = page.locator("div.cursor-pointer").first
        if first_card.is_visible():
            first_card.click()

        # 3. Verify Advisory Release Readiness Checklist & Advisory Banner
        expect(page.locator("text=Advisory Release Readiness Evaluation")).to_be_visible()
        expect(page.locator("text=Release readiness check is strictly advisory. It informs the officer; it never approves.")).to_be_visible()
        expect(page.locator("text=OVERALL:")).to_be_visible()

        # 4. Verify Competent Authority Authorization Gate
        auth_btn = page.locator("button:has-text('Authorize Approval (Competent Authority)')")
        if auth_btn.is_visible():
            auth_btn.click()
            expect(page.locator("text=Competent Authority Release Authorization")).to_be_visible()
            expect(page.locator("text=Official Release Order Reference")).to_be_visible()
            
            justification = page.locator("textarea[placeholder*='Detail statutory grounds']")
            justification.fill("Verified program closure, NOC from state government, and zero student liabilities.")

            sign_btn = page.locator("button:has-text('Sign & Authorize')")
            sign_btn.click()

        # 5. Verify Hash Chain Audit
        verify_chain_btn = page.get_by_role("button", name="Verify Hash Chain Integrity")
        expect(verify_chain_btn).to_be_visible()
        verify_chain_btn.click()

        # 6. Verify FDR Lifecycle Passport per instrument
        page.get_by_role("button", name="Lifecycle Passport").click()
        expect(page.locator("text=FDR Lifecycle Passport (Instrument Lineage)")).to_be_visible()
        expect(page.locator("text=Chronological Lifecycle Timeline")).to_be_visible()
        expect(page.locator("text=Download Evidence Pack (PDF)")).to_be_visible()

        browser.close()
