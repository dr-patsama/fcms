"""Journey layer (j1_002) — lab task assignee.

lab_tasks: + assigned_to (users.id), assigned_at, assigned_by — who is responsible for each
to-do on the lab board, shown on every card and in the cycle workspace.
"""
from alembic import op
import sqlalchemy as sa

revision = "j1_002"
down_revision = "j1_001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("lab_tasks", sa.Column("assigned_to", sa.UUID(), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("lab_tasks", sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("lab_tasks", sa.Column("assigned_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True))
    op.create_index("ix_lab_tasks_assigned_to", "lab_tasks", ["assigned_to"])


def downgrade():
    op.drop_index("ix_lab_tasks_assigned_to", table_name="lab_tasks")
    op.drop_column("lab_tasks", "assigned_by")
    op.drop_column("lab_tasks", "assigned_at")
    op.drop_column("lab_tasks", "assigned_to")
