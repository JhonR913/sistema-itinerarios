"""outbox: seguimiento de entrega (attempts, published_at, last_error)

El relay marca PUBLISHED solo tras el confirm del broker, cuenta intentos
y registra el ultimo error; pasado MAX_ATTEMPTS el evento queda FAILED.
Aditiva y reversible: no pierde datos al subir; al bajar solo elimina las
columnas nuevas.
"""
from alembic import op

revision = "0002_outbox_delivery_tracking"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE outbox ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE outbox ADD COLUMN IF NOT EXISTS published_at TIMESTAMP")
    op.execute("ALTER TABLE outbox ADD COLUMN IF NOT EXISTS last_error TEXT")
    op.execute("CREATE INDEX IF NOT EXISTS idx_outbox_pending ON outbox(id) WHERE status = 'PENDING'")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_outbox_pending")
    op.execute("ALTER TABLE outbox DROP COLUMN IF EXISTS last_error")
    op.execute("ALTER TABLE outbox DROP COLUMN IF EXISTS published_at")
    op.execute("ALTER TABLE outbox DROP COLUMN IF EXISTS attempts")
