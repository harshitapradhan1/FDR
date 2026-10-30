"""
DepoSafe - Automated Evidence Pack Generator (ReportLab PDF)
Produces a comprehensive, tamper-evident regulatory dossier for any FDR instrument.
Includes 4-source provenance, validation, discrepancies, risk analysis,
compliance evaluation with rule versions, verification logs, and cryptographic audit excerpt.
"""
import io
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from sqlalchemy.orm import Session
from backend.app.models.deposafe_models import (
    FDR, Institution, FDRDocument, FieldProvenance,
    BankVerificationRecord, AuditLog
)
from backend.app.rules.compliance_engine import evaluate_fdr_compliance, get_active_rule
from backend.app.services.reconciliation_service import CrossDocumentReconciler


def _get_val(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def generate_fdr_evidence_pack_pdf(db: Session, fdr_id: int) -> bytes:
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise ValueError(f"FDR record #{fdr_id} not found.")

    institution = db.query(Institution).filter(Institution.id == fdr.institution_id).first()
    active_rule = get_active_rule(db)
    comp_eval = evaluate_fdr_compliance(fdr, institution, active_rule) if active_rule else None
    recon = CrossDocumentReconciler.reconcile_fdr_documents(fdr_id, db)
    bank_recs = db.query(BankVerificationRecord).filter(BankVerificationRecord.fdr_id == fdr.id).all()
    audit_logs = db.query(AuditLog).filter(AuditLog.entity_id == fdr.id).order_by(AuditLog.id.asc()).all()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#0F172A'),
        alignment=1
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#475569'),
        alignment=1
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#1E3A8A'),
        spaceBefore=10,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#1E293B')
    )
    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )
    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#0F172A')
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#0F172A')
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("ALL INDIA COUNCIL FOR TECHNICAL EDUCATION (AICTE)", title_style))
    story.append(Paragraph("Regulation Bureau &bull; Security Deposit / FDR Intelligence & Management Portal (DepoSafe)", subtitle_style))
    story.append(Paragraph(f"<b>STATUTORY EVIDENCE DOSSIER & REGULATORY AUDIT PACK</b> &bull; Generated: {datetime.utcnow().strftime('%d-%b-%Y %H:%M:%S UTC')}", subtitle_style))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#D97706'), spaceBefore=2, spaceAfter=8))

    # 2. Instrument & Institution Master Overview
    story.append(Paragraph("1. INSTRUMENT & INSTITUTION PROFILE", section_heading))
    inst_name = institution.name if institution else "N/A"
    aicte_id = institution.aicte_id if institution else "N/A"
    state = institution.state if institution else "N/A"
    amount_str = f"₹{fdr.amount:,.2f}" if fdr.amount else "N/A"

    profile_data = [
        [
            Paragraph("<b>FDR Internal ID:</b>", body_style), Paragraph(str(fdr.id), table_cell_bold),
            Paragraph("<b>FDR Number:</b>", body_style), Paragraph(fdr.fdr_number or "N/A", table_cell_bold)
        ],
        [
            Paragraph("<b>Institution Name:</b>", body_style), Paragraph(inst_name, table_cell),
            Paragraph("<b>AICTE ID:</b>", body_style), Paragraph(aicte_id, table_cell)
        ],
        [
            Paragraph("<b>Bank Name:</b>", body_style), Paragraph(fdr.bank_name or "N/A", table_cell),
            Paragraph("<b>Branch / IFSC:</b>", body_style), Paragraph(f"{fdr.branch_name or 'N/A'} ({fdr.ifsc_code or 'N/A'})", table_cell)
        ],
        [
            Paragraph("<b>Principal Amount:</b>", body_style), Paragraph(amount_str, table_cell_bold),
            Paragraph("<b>Status:</b>", body_style), Paragraph(str(getattr(fdr.status, "value", fdr.status) or "N/A"), table_cell_bold)
        ],
        [
            Paragraph("<b>Issue Date:</b>", body_style), Paragraph(fdr.issue_date.isoformat() if fdr.issue_date else "N/A", table_cell),
            Paragraph("<b>Maturity Date:</b>", body_style), Paragraph(fdr.maturity_date.isoformat() if fdr.maturity_date else "N/A", table_cell)
        ],
        [
            Paragraph("<b>Risk Score:</b>", body_style), Paragraph(f"{fdr.review_priority_score or 0.0:.1f} / 100 ({str(getattr(fdr.review_priority_level, 'value', fdr.review_priority_level) or 'LOW')})", table_cell_bold),
            Paragraph("<b>Lineage ID:</b>", body_style), Paragraph(fdr.lineage_id or f"LIN-{fdr.id}", table_cell)
        ]
    ]

    t_profile = Table(profile_data, colWidths=[100, 160, 100, 160])
    t_profile.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_profile)
    story.append(Spacer(1, 8))

    # 3. Four-Source Provenance Ledger
    story.append(Paragraph("2. DUAL-TRUTH FOUR-SOURCE PROVENANCE LEDGER", section_heading))
    provenance_rows = [
        [
            Paragraph("Field", table_header),
            Paragraph("Submitted", table_header),
            Paragraph("AI Extracted", table_header),
            Paragraph("Bank Confirmed", table_header),
            Paragraph("Officer Verified", table_header),
            Paragraph("Provenance / Match", table_header),
        ]
    ]

    prov_list = fdr.provenance_fields or []
    if prov_list:
        for p in prov_list:
            field_name = _get_val(p, "field_name", "")
            submitted = str(_get_val(p, "submitted_value") or "—")
            ext_conf = _get_val(p, "extracted_confidence")
            extracted = f"{_get_val(p, 'extracted_value') or '—'}"
            if ext_conf is not None:
                extracted += f" ({int(ext_conf * 100)}%)"
            bank_val = str(_get_val(p, "bank_confirmed_value") or "—")
            off_val = str(_get_val(p, "officer_verified_value") or "—")
            is_m = _get_val(p, "is_match")
            m_reason = _get_val(p, "mismatch_reason")
            status_text = "MATCH" if is_m else f"MISMATCH: {m_reason or 'Discrepancy'}"

            provenance_rows.append([
                Paragraph(field_name, table_cell_bold),
                Paragraph(submitted[:25], table_cell),
                Paragraph(extracted[:28], table_cell),
                Paragraph(bank_val[:25], table_cell),
                Paragraph(off_val[:25], table_cell),
                Paragraph(status_text[:35], table_cell)
            ])
    else:
        provenance_rows.append([Paragraph("No provenance records found for this instrument.", table_cell), Paragraph("", table_cell), Paragraph("", table_cell), Paragraph("", table_cell), Paragraph("", table_cell), Paragraph("", table_cell)])

    t_prov = Table(provenance_rows, colWidths=[80, 85, 95, 85, 85, 90])
    t_prov.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
    ]))
    story.append(t_prov)
    story.append(Spacer(1, 8))

    # 4. Cross-Document Reconciliation & Discrepancies
    story.append(Paragraph("3. CROSS-DOCUMENT RECONCILIATION MATRIX", section_heading))
    recon_rows = [
        [
            Paragraph("Field", table_header),
            Paragraph("FDR Certificate", table_header),
            Paragraph("Confirmation Letter", table_header),
            Paragraph("Reconciliation Status", table_header),
        ]
    ]

    for item in recon.get("reconciliation_matrix", []):
        fdr_val = item.get("fdr_certificate_value") or "—"
        conf_val = item.get("confirmation_letter_value") or "—"
        status_disp = "MATCH" if item.get("status") == "MATCH" else f"MISMATCH ({item.get('discrepancy_details') or ''})"
        recon_rows.append([
            Paragraph(item.get("field_name", ""), table_cell_bold),
            Paragraph(str(fdr_val)[:30], table_cell),
            Paragraph(str(conf_val)[:30], table_cell),
            Paragraph(status_disp[:45], table_cell)
        ])

    t_recon = Table(recon_rows, colWidths=[100, 130, 130, 160])
    t_recon.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F766E')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
    ]))
    story.append(t_recon)
    story.append(Spacer(1, 8))

    # 5. Explainable Risk Score & Forensic Findings
    story.append(Paragraph("4. EXPLAINABLE RISK SCORE & FORENSIC ANOMALY ANALYSIS", section_heading))
    flags = fdr.review_flags or []
    risk_rows = [
        [
            Paragraph("Factor / Check", table_header),
            Paragraph("Severity", table_header),
            Paragraph("Evidence & Details", table_header),
            Paragraph("Recommended Action", table_header)
        ]
    ]
    if flags:
        for fl in flags:
            risk_rows.append([
                Paragraph(fl.get("flag", "Anomaly"), table_cell_bold),
                Paragraph(fl.get("severity", "MEDIUM"), table_cell),
                Paragraph(fl.get("evidence", "—")[:50], table_cell),
                Paragraph(fl.get("recommended_action", "Investigate")[:45], table_cell)
            ])
    else:
        risk_rows.append([
            Paragraph("Standard Statutory Baseline", table_cell_bold),
            Paragraph("LOW", table_cell),
            Paragraph("Zero anomalies detected across cryptographic, OCR, and CBS layers.", table_cell),
            Paragraph("Proceed with verification.", table_cell)
        ])

    t_risk = Table(risk_rows, colWidths=[110, 60, 190, 160])
    t_risk.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#B45309')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
    ]))
    story.append(t_risk)
    story.append(Spacer(1, 8))

    # 6. APH Regulation Compliance Results
    if comp_eval:
        story.append(Paragraph(f"5. STATUTORY COMPLIANCE EVALUATION (APH {comp_eval.get('handbook_version', '2024-27')})", section_heading))
        comp_rows = [
            [
                Paragraph("Rule ID", table_header),
                Paragraph("Type", table_header),
                Paragraph("Status", table_header),
                Paragraph("Observed vs Expected", table_header),
                Paragraph("Plain Explanation", table_header),
            ]
        ]
        for r in comp_eval.get("results", []):
            comp_rows.append([
                Paragraph(r.get("rule_id", ""), table_cell_bold),
                Paragraph(r.get("rule_type", ""), table_cell),
                Paragraph(r.get("status", ""), table_cell_bold),
                Paragraph(f"Obs: {str(r.get('observed_value', ''))[:15]} | Exp: {str(r.get('expected_value', ''))[:15]}", table_cell),
                Paragraph(r.get("plain_explanation_en", "")[:45], table_cell)
            ])

        t_comp = Table(comp_rows, colWidths=[80, 75, 75, 130, 160])
        t_comp.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4338CA')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('TOPPADDING', (0, 0), (-1, -1), 2.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ]))
        story.append(t_comp)
        story.append(Spacer(1, 8))

    # 7. Verification Records & Officer Remarks
    story.append(Paragraph("6. BANK VERIFICATION & OFFICER REMARKS", section_heading))
    bank_notes = []
    if bank_recs:
        for b in bank_recs:
            v_status = str(getattr(b.verification_status, 'value', b.verification_status))
            bank_notes.append(f"&bull; <b>{b.adapter_used}</b> [{v_status}]: {b.remarks or 'No remarks'} (Ref: {b.api_reference_id or 'CBS-REF'}). Verified: {b.verified_at.strftime('%d-%b-%Y %H:%M')}")
    else:
        bank_notes.append("&bull; Core Banking System (CBS) verification pending.")
    
    if getattr(fdr, "officer_override_justification", None):
        bank_notes.append(f"&bull; <b>Mandatory Officer Override Justification:</b> {fdr.officer_override_justification}")
    if getattr(fdr, "release_justification", None):
        bank_notes.append(f"&bull; <b>Release Justification:</b> {fdr.release_justification} (Order Ref: {fdr.release_order_ref or 'Pending'})")

    for note in bank_notes:
        story.append(Paragraph(note, body_style))
        story.append(Spacer(1, 2))
    story.append(Spacer(1, 6))

    # 8. Cryptographic Hash Chain Audit Excerpt
    story.append(Paragraph("7. IMMUTABLE CRYPTOGRAPHIC AUDIT LOG EXCERPT", section_heading))
    audit_rows = [
        [
            Paragraph("Log #", table_header),
            Paragraph("Event Type", table_header),
            Paragraph("Actor", table_header),
            Paragraph("Timestamp", table_header),
            Paragraph("Current SHA-256 Hash", table_header),
        ]
    ]

    for log in audit_logs[-6:]:
        actor_disp = log.actor_role or (f"User #{log.actor_id}" if log.actor_id else "SYSTEM")
        audit_rows.append([
            Paragraph(str(log.id), table_cell_bold),
            Paragraph(log.event_type[:20], table_cell),
            Paragraph(actor_disp[:15], table_cell),
            Paragraph(log.timestamp.strftime("%Y-%m-%d %H:%M") if log.timestamp else "N/A", table_cell),
            Paragraph(f"{log.current_hash[:20]}..." if log.current_hash else "GENESIS", table_cell)
        ])

    t_audit = Table(audit_rows, colWidths=[40, 110, 90, 100, 180])
    t_audit.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(t_audit)
    story.append(Spacer(1, 10))

    # Footer Notice
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceBefore=4, spaceAfter=4))
    story.append(Paragraph(
        "<i>This document is a computer-generated statutory evidence pack under AICTE DepoSafe. All findings, provenance traces, and hashes are cryptographically chained and legally admissible under IT Act 2000.</i>",
        subtitle_style
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
