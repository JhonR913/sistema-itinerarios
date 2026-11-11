"""departure_at: salida con fecha y hora (timestamptz)

Reemplaza la nocion de "solo fecha" por un instante. Los itinerarios
existentes se migran a las 00:00 (America/Bogota) de su travel_date, sin
perder datos. travel_date se conserva (fecha local de la salida).
"""
from alembic import op

revision = "0003_departure_at"
down_revision = "0002_outbox_delivery_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE itineraries ADD COLUMN IF NOT EXISTS departure_at TIMESTAMPTZ")
    op.execute("""
        UPDATE itineraries
           SET departure_at = (travel_date::timestamp AT TIME ZONE 'America/Bogota')
         WHERE departure_at IS NULL
    """)
    op.execute("ALTER TABLE itineraries ALTER COLUMN departure_at SET NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_itineraries_user_departure ON itineraries(user_id, departure_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_itineraries_user_departure")
    op.execute("ALTER TABLE itineraries DROP COLUMN IF EXISTS departure_at")
