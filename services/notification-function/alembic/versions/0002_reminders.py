"""reminders: recordatorios de viaje por correo (Sprint 6)

Una fila por itinerario. `last_event_id` (= id del outbox, creciente) hace
que un evento mas viejo nunca pise a uno mas nuevo aunque lleguen desordenados
(p. ej. un Deleted antes que el Created deja una "lapida" CANCELLED que
el Created tardio no puede revivir). Al cancelar se borran email y nombre (PII).

Aditiva y reversible.
"""
from alembic import op

revision = "0002_reminders"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            itinerary_id UUID PRIMARY KEY,
            email VARCHAR(254),
            nombre_usuario VARCHAR(120),
            origin VARCHAR(4),
            destination VARCHAR(4),
            travel_date DATE,
            remind_at TIMESTAMPTZ,
            status VARCHAR(20) NOT NULL,
            last_event_id BIGINT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            sent_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT reminders_status_chk CHECK (status IN ('PENDING','SENT','CANCELLED','SKIPPED','FAILED'))
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(remind_at) WHERE status = 'PENDING'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_reminders_due")
    op.execute("DROP TABLE IF EXISTS reminders")
