"""baseline: tabla airports

Adopta el esquema que antes creaba el initdb de Docker (001_init.sql).
Es idempotente (IF NOT EXISTS): en una base ya existente solo registra la
version en alembic_version sin tocar ni borrar datos.
"""
from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS airports (
            id VARCHAR(64) PRIMARY KEY,
            external_id VARCHAR(64) NOT NULL,
            iata_code VARCHAR(4) NOT NULL,
            name VARCHAR(200) NOT NULL,
            city VARCHAR(120) NOT NULL,
            latitude DECIMAL(9,6) NOT NULL,
            longitude DECIMAL(9,6) NOT NULL,
            cached_at TIMESTAMP NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_airports_iata ON airports(iata_code)")


def downgrade() -> None:
    # DESTRUCTIVO: elimina la tabla y sus datos (es solo una cache durable
    # de API Colombia, se repuebla sola en la siguiente consulta).
    op.execute("DROP TABLE IF EXISTS airports")
