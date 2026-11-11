"""baseline: itineraries y outbox

Adopta el esquema que antes creaba el initdb de Docker (001_init.sql).
Idempotente: en una base existente no modifica ni borra datos.
"""
from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS itineraries (
            id UUID PRIMARY KEY,
            nombre_usuario VARCHAR(120) NOT NULL,
            user_id VARCHAR(120) NOT NULL,
            origin_airport_id VARCHAR(64) NOT NULL,
            origin_iata VARCHAR(4) NOT NULL,
            origin_name VARCHAR(200) NOT NULL,
            origin_city VARCHAR(120) NOT NULL,
            destination_airport_id VARCHAR(64) NOT NULL,
            destination_iata VARCHAR(4) NOT NULL,
            destination_name VARCHAR(200) NOT NULL,
            destination_city VARCHAR(120) NOT NULL,
            travel_date DATE NOT NULL,
            duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            CHECK (origin_airport_id <> destination_airport_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_itineraries_user_id ON itineraries(user_id)")
    op.execute("""
        CREATE TABLE IF NOT EXISTS outbox (
            id SERIAL PRIMARY KEY,
            aggregate_id UUID NOT NULL,
            event_type VARCHAR(120) NOT NULL,
            payload JSONB NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            created_at TIMESTAMP NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_outbox_status ON outbox(status)")


def downgrade() -> None:
    # DESTRUCTIVO: elimina itinerarios y eventos pendientes.
    op.execute("DROP TABLE IF EXISTS outbox")
    op.execute("DROP TABLE IF EXISTS itineraries")
