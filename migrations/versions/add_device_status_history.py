"""add device status history table

Revision ID: add_device_status_history
Revises: a64395706c9f  # 修改这里，设置为之前迁移的ID
Create Date: 2024-01-20
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic
revision = 'add_device_status_history'
down_revision = 'a64395706c9f'  # 修改这里，设置为之前迁移的ID
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'device_status_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('timestamp', sa.DateTime(), default=datetime.utcnow),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('device_status_history') 