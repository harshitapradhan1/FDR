"""Phase 1 Foundation Database Schema Migration

Revision ID: 0001_phase1_foundation
Revises: 
Create Date: 2026-10-30 09:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0001_phase1_foundation'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Institutions
    op.create_table(
        'institutions',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('aicte_id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('society_or_trust_name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('program_level', sa.String(length=50), nullable=False),
        sa.Column('institution_type', sa.String(length=50), server_default='Normal', nullable=False),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('regional_office', sa.String(length=100), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=False),
        sa.Column('contact_phone', sa.String(length=50), nullable=False),
        sa.Column('authorized_signatory_name', sa.String(length=255), nullable=False),
        sa.Column('signatory_pan_or_id', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_institutions_id', 'institutions', ['id'])
    op.create_index('ix_institutions_aicte_id', 'institutions', ['aicte_id'], unique=True)

    # 2. Users & Roles
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('institution_id', sa.Integer(), sa.ForeignKey('institutions.id'), nullable=True),
        sa.Column('regional_office', sa.String(length=100), nullable=True),
        sa.Column('designation', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 3. Banks
    op.create_table(
        'banks',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('rbi_code', sa.String(length=50), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('bank_type', sa.String(length=50), nullable=False),
        sa.Column('ifsc_prefix', sa.String(length=10), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_banks_id', 'banks', ['id'])
    op.create_index('ix_banks_name', 'banks', ['name'], unique=True)
    op.create_index('ix_banks_rbi_code', 'banks', ['rbi_code'], unique=True)

    # 4. FDR Records
    op.create_table(
        'fdr_records',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('internal_fdr_id', sa.String(length=64), nullable=False),
        sa.Column('lineage_id', sa.String(length=64), nullable=False),
        sa.Column('institution_id', sa.Integer(), sa.ForeignKey('institutions.id'), nullable=False),
        sa.Column('bank_id', sa.Integer(), sa.ForeignKey('banks.id'), nullable=True),
        sa.Column('bank_name', sa.String(length=255), nullable=False),
        sa.Column('branch_name', sa.String(length=255), nullable=False),
        sa.Column('ifsc_code', sa.String(length=20), nullable=False),
        sa.Column('fdr_number', sa.String(length=100), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('maturity_date', sa.Date(), nullable=False),
        sa.Column('tenure_months', sa.Integer(), nullable=False),
        sa.Column('interest_rate', sa.Float(), nullable=True),
        sa.Column('auto_renewal', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('joint_holder_name', sa.String(length=255), nullable=True),
        sa.Column('lien_marked_to_aicte', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('lien_clause_text', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('predecessor_fdr_id', sa.Integer(), sa.ForeignKey('fdr_records.id'), nullable=True),
        sa.Column('successor_fdr_id', sa.Integer(), sa.ForeignKey('fdr_records.id'), nullable=True),
        sa.Column('superseded_by', sa.Integer(), sa.ForeignKey('fdr_records.id'), nullable=True),
        sa.Column('review_priority_score', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('review_priority_level', sa.String(length=20), server_default='LOW', nullable=False),
        sa.Column('review_flags', sa.JSON(), nullable=True),
        sa.Column('officer_override', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('officer_override_justification', sa.Text(), nullable=True),
        sa.Column('officer_override_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('officer_override_at', sa.DateTime(), nullable=True),
        sa.Column('release_requested_at', sa.DateTime(), nullable=True),
        sa.Column('release_justification', sa.Text(), nullable=True),
        sa.Column('release_authorized_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('release_authorized_at', sa.DateTime(), nullable=True),
        sa.Column('release_order_ref', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_fdr_records_id', 'fdr_records', ['id'])
    op.create_index('ix_fdr_records_internal_fdr_id', 'fdr_records', ['internal_fdr_id'], unique=True)
    op.create_index('ix_fdr_records_lineage_id', 'fdr_records', ['lineage_id'])
    op.create_index('ix_fdr_records_bank_name', 'fdr_records', ['bank_name'])
    op.create_index('ix_fdr_records_ifsc_code', 'fdr_records', ['ifsc_code'])
    op.create_index('ix_fdr_records_fdr_number', 'fdr_records', ['fdr_number'])
    op.create_index('ix_fdr_records_status', 'fdr_records', ['status'])
    op.create_index('ix_bank_fdr_composite', 'fdr_records', ['bank_name', 'fdr_number'])

    # 5. Documents (Versioned)
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('fdr_id', sa.Integer(), sa.ForeignKey('fdr_records.id'), nullable=False),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=True),
        sa.Column('file_hash_sha256', sa.String(length=64), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=True),
        sa.Column('perceptual_hash', sa.String(length=64), nullable=True),
        sa.Column('mime_type', sa.String(length=100), server_default='application/pdf', nullable=False),
        sa.Column('doc_type', sa.String(length=50), server_default='FDR_CERTIFICATE', nullable=False),
        sa.Column('ocr_status', sa.String(length=50), server_default='COMPLETED', nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('forensic_metadata', sa.JSON(), nullable=True),
        sa.Column('uploaded_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_documents_id', 'documents', ['id'])
    op.create_index('ix_documents_file_hash_sha256', 'documents', ['file_hash_sha256'])
    op.create_index('ix_documents_perceptual_hash', 'documents', ['perceptual_hash'])

    # 6. Extracted Fields
    op.create_table(
        'extracted_fields',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('fdr_id', sa.Integer(), sa.ForeignKey('fdr_records.id'), nullable=False),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('documents.id'), nullable=True),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('value', sa.String(length=500), nullable=True),
        sa.Column('confidence', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('provenance', sa.String(length=50), server_default='AI_EXTRACTED', nullable=False),
        sa.Column('page', sa.Integer(), server_default='1', nullable=False),
        sa.Column('bbox', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_extracted_fields_id', 'extracted_fields', ['id'])

    # 7. Field Provenance
    op.create_table(
        'field_provenance',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('fdr_id', sa.Integer(), sa.ForeignKey('fdr_records.id'), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('submitted_value', sa.String(length=500), nullable=True),
        sa.Column('ai_extracted_value', sa.String(length=500), nullable=True),
        sa.Column('bank_confirmed_value', sa.String(length=500), nullable=True),
        sa.Column('officer_verified_value', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='SUBMITTED', nullable=False),
        sa.Column('ai_confidence', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('bounding_box', sa.JSON(), nullable=True),
        sa.Column('mismatch_reason', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_field_provenance_id', 'field_provenance', ['id'])

    # 8. Verifications
    op.create_table(
        'verifications',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('fdr_id', sa.Integer(), sa.ForeignKey('fdr_records.id'), nullable=False),
        sa.Column('adapter_used', sa.String(length=50), nullable=False),
        sa.Column('verification_status', sa.String(length=50), nullable=False),
        sa.Column('api_reference_id', sa.String(length=100), nullable=True),
        sa.Column('watermark_notice', sa.String(length=255), server_default='SIMULATED, not a real bank verification', nullable=False),
        sa.Column('manual_evidence_type', sa.String(length=100), nullable=True),
        sa.Column('evidence_data', sa.JSON(), nullable=True),
        sa.Column('manual_evidence_details', sa.JSON(), nullable=True),
        sa.Column('verified_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True)
    )
    op.create_index('ix_verifications_id', 'verifications', ['id'])

    # 9. Renewals
    op.create_table(
        'renewals',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('lineage_id', sa.String(length=64), nullable=False),
        sa.Column('old_fdr_id', sa.Integer(), sa.ForeignKey('fdr_records.id'), nullable=False),
        sa.Column('new_fdr_id', sa.Integer(), sa.ForeignKey('fdr_records.id'), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='COMPLETED', nullable=False),
        sa.Column('initiated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_renewals_id', 'renewals', ['id'])
    op.create_index('ix_renewals_lineage_id', 'renewals', ['lineage_id'])

    # 10. Release Requests
    op.create_table(
        'release_requests',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('fdr_id', sa.Integer(), sa.ForeignKey('fdr_records.id'), nullable=False),
        sa.Column('institution_id', sa.Integer(), sa.ForeignKey('institutions.id'), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('justification', sa.Text(), nullable=False),
        sa.Column('noc_reference', sa.String(length=100), nullable=True),
        sa.Column('requested_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('recommended_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('release_order_ref', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_release_requests_id', 'release_requests', ['id'])

    # 11. Notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('recipient', sa.String(length=255), nullable=False),
        sa.Column('recipient_role', sa.String(length=50), nullable=True),
        sa.Column('fdr_id', sa.Integer(), sa.ForeignKey('fdr_records.id'), nullable=True),
        sa.Column('notification_type', sa.String(length=50), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('delivery_status', sa.String(length=50), server_default='SENT', nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_notifications_id', 'notifications', ['id'])

    # 12. Compliance Rules
    op.create_table(
        'compliance_rules',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('version_tag', sa.String(length=50), unique=True, nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('rules_json', sa.JSON(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_compliance_rules_id', 'compliance_rules', ['id'])

    # 13. Compliance Results
    op.create_table(
        'compliance_results',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('fdr_id', sa.Integer(), sa.ForeignKey('fdr_records.id'), nullable=False),
        sa.Column('rule_version_used', sa.String(length=50), nullable=False),
        sa.Column('overall_passed', sa.Boolean(), nullable=False),
        sa.Column('checks_json', sa.JSON(), nullable=True),
        sa.Column('evaluated_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_compliance_results_id', 'compliance_results', ['id'])

    # 14. Risk Assessments
    op.create_table(
        'risk_assessments',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('fdr_id', sa.Integer(), sa.ForeignKey('fdr_records.id'), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('risk_level', sa.String(length=20), nullable=False),
        sa.Column('reasons', sa.JSON(), nullable=True),
        sa.Column('assessed_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_risk_assessments_id', 'risk_assessments', ['id'])

    # 15. Audit Logs (Cryptographic Hash Chain)
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('sequence_num', sa.Integer(), unique=True, nullable=False),
        sa.Column('previous_hash', sa.String(length=64), nullable=False),
        sa.Column('prev_hash', sa.String(length=64), nullable=True),
        sa.Column('current_hash', sa.String(length=64), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.String(length=50), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('actor_role', sa.String(length=50), nullable=True),
        sa.Column('ip_address', sa.String(length=50), server_default='127.0.0.1', nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('timestamp_iso', sa.String(length=50), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=True)
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'])
    op.create_index('ix_audit_logs_sequence_num', 'audit_logs', ['sequence_num'])
    op.create_index('ix_audit_logs_current_hash', 'audit_logs', ['current_hash'])
    op.create_index('ix_audit_logs_event_type', 'audit_logs', ['event_type'])

    # 16. Demo Clock
    op.create_table(
        'demo_clock',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('current_simulated_date', sa.Date(), nullable=False),
        sa.Column('offset_days', sa.Integer(), server_default='0', nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True)
    )

def downgrade() -> None:
    op.drop_table('demo_clock')
    op.drop_table('audit_logs')
    op.drop_table('risk_assessments')
    op.drop_table('compliance_results')
    op.drop_table('compliance_rules')
    op.drop_table('notifications')
    op.drop_table('release_requests')
    op.drop_table('renewals')
    op.drop_table('verifications')
    op.drop_table('field_provenance')
    op.drop_table('extracted_fields')
    op.drop_table('documents')
    op.drop_table('fdr_records')
    op.drop_table('banks')
    op.drop_table('users')
    op.drop_table('institutions')

