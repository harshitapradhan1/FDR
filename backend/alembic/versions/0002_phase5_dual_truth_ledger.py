"""Phase 5 Dual-Truth Four-Source Ledger Migration

Revision ID: 0002_phase5_dual_truth
Revises: 0001_phase1_foundation
Create Date: 2026-10-30 09:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0002_phase5_dual_truth'
down_revision: Union[str, None] = '0001_phase1_foundation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    existing_cols = [c['name'] for c in insp.get_columns('field_provenance')]
    existing_tables = insp.get_table_names()

    # 1. Add timestamps and actor fields to field_provenance if missing
    with op.batch_alter_table('field_provenance') as batch_op:
        if 'submitted_at' not in existing_cols:
            batch_op.add_column(sa.Column('submitted_at', sa.DateTime(), nullable=True))
        if 'ai_extracted_at' not in existing_cols:
            batch_op.add_column(sa.Column('ai_extracted_at', sa.DateTime(), nullable=True))
        if 'bank_confirmed_at' not in existing_cols:
            batch_op.add_column(sa.Column('bank_confirmed_at', sa.DateTime(), nullable=True))
        if 'officer_verified_at' not in existing_cols:
            batch_op.add_column(sa.Column('officer_verified_at', sa.DateTime(), nullable=True))
        if 'submitted_by' not in existing_cols:
            batch_op.add_column(sa.Column('submitted_by', sa.String(length=100), nullable=True))
        if 'ai_extracted_by' not in existing_cols:
            batch_op.add_column(sa.Column('ai_extracted_by', sa.String(length=100), nullable=True))
        if 'bank_confirmed_by' not in existing_cols:
            batch_op.add_column(sa.Column('bank_confirmed_by', sa.String(length=100), nullable=True))
        if 'officer_verified_by' not in existing_cols:
            batch_op.add_column(sa.Column('officer_verified_by', sa.String(length=100), nullable=True))
        if 'conflicts' not in existing_cols:
            batch_op.add_column(sa.Column('conflicts', sa.JSON(), nullable=True, server_default='[]'))

    # 2. Create provenance_ledger table if missing
    if 'provenance_ledger' not in existing_tables:
        op.create_table(
            'provenance_ledger',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('fdr_id', sa.Integer(), sa.ForeignKey('fdr_records.id'), nullable=False),
            sa.Column('field_name', sa.String(length=100), nullable=False),
            sa.Column('source', sa.String(length=50), nullable=False),
            sa.Column('value', sa.String(length=500), nullable=True),
            sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('actor_name', sa.String(length=255), nullable=True),
            sa.Column('actor_role', sa.String(length=100), nullable=True),
            sa.Column('timestamp', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('confidence', sa.Float(), server_default='1.0', nullable=False),
            sa.Column('bounding_box', sa.JSON(), nullable=True),
            sa.Column('evidence_ref', sa.String(length=255), nullable=True),
            sa.Column('remarks', sa.Text(), nullable=True),
        )

    # 3. Create verification_queue table if missing
    if 'verification_queue' not in existing_tables:
        op.create_table(
            'verification_queue',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('fdr_id', sa.Integer(), sa.ForeignKey('fdr_records.id'), nullable=False),
            sa.Column('status', sa.String(length=50), server_default='QUEUED', nullable=False),
            sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
            sa.Column('max_attempts', sa.Integer(), server_default='3', nullable=False),
            sa.Column('last_error', sa.Text(), nullable=True),
            sa.Column('scenario', sa.String(length=50), nullable=True),
            sa.Column('next_retry_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

def downgrade() -> None:
    op.drop_table('verification_queue')
    op.drop_table('provenance_ledger')
    with op.batch_alter_table('field_provenance') as batch_op:
        batch_op.drop_column('conflicts')
        batch_op.drop_column('officer_verified_by')
        batch_op.drop_column('bank_confirmed_by')
        batch_op.drop_column('ai_extracted_by')
        batch_op.drop_column('submitted_by')
        batch_op.drop_column('officer_verified_at')
        batch_op.drop_column('bank_confirmed_at')
        batch_op.drop_column('ai_extracted_at')
        batch_op.drop_column('submitted_at')
