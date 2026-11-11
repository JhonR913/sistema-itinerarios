"""reminders: hora de salida/llegada y ciudades

Aditiva y reversible. Las filas existentes quedan con NULL (se comportan como
antes: recordatorio relativo a la fecha).
"""
from alembic import op

revision = "0003_trip_times"
down_revision = "0002_reminders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE reminders ADD COLUMN IF NOT EXISTS departure_at TIMESTAMPTZ")
    op.execute("ALTER TABLE reminders ADD COLUMN IF NOT EXISTS arrival_at TIMESTAMPTZ")
    op.execute("ALTER TABLE reminders ADD COLUMN IF NOT EXISTS origin_city VARCHAR(120)")
    op.execute("ALTER TABLE reminders ADD COLUMN IF NOT EXISTS destination_city VARCHAR(120)")


def downgrade() -> None:
    op.execute("ALTER TABLE reminders DROP COLUMN IF EXISTS destination_city")
    op.execute("ALTER TABLE reminders DROP COLUMN IF EXISTS origin_city")
    op.execute("ALTER TABLE reminders DROP COLUMN IF EXISTS arrival_at")
    op.execute("ALTER TABLE reminders DROP COLUMN IF EXISTS departure_at")
