"""create events table

Revision ID: 001
Revises: 
Create Date: 2024-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Создаем таблицу events
    op.create_table('events',
        sa.Column('event_id', sa.String(36), nullable=False, primary_key=True),
        sa.Column('schema_version', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('occurred_at', sa.DateTime(), nullable=False),
        sa.Column('payload', JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), 
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), 
                  server_default=sa.text('now()'), 
                  onupdate=sa.text('now()'), nullable=False),
    )
    
    # Создаем индексы
    op.create_index('ix_events_created_at', 'events', ['created_at'])
    op.create_index('ix_events_event_type', 'events', ['event_type'])
    op.create_index('ix_events_occurred_at', 'events', ['occurred_at'])


def downgrade() -> None:
    op.drop_index('ix_events_occurred_at')
    op.drop_index('ix_events_event_type')
    op.drop_index('ix_events_created_at')
    op.drop_table('events')
