"""baseline: notification_history

Adopta el esquema que antes creaba el initdb de Docker (migration.sql).
Idempotente. El indice UNICO sobre itinerary_id es lo que hace correcta la
idempotencia del consumidor (INSERT ... ON CONFLICT DO NOTHING).
"""
from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS notification_history (
            id SERIAL PRIMARY KEY,
            itinerary_id UUID NOT NULL,
            channel VARCHAR(50) NOT NULL,
            status VARCHAR(20) NOT NULL,
            sent_at TIMESTAMP NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_notification_itinerary_unique "
        "ON notification_history(itinerary_id)"
    )


def downgrade() -> None:
    # DESTRUCTIVO: elimina el historial de notificaciones.
    op.execute("DROP TABLE IF EXISTS notification_history")
