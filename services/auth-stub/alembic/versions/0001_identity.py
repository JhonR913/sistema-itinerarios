"""identidad: usuarios, codigos de verificacion y sesiones"""
from alembic import op

revision = "0001_identity"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE users (
            id UUID PRIMARY KEY,
            email VARCHAR(254) NOT NULL UNIQUE CHECK (email = lower(email)),
            name VARCHAR(120) NOT NULL,
            password_hash TEXT NOT NULL,
            verified_at TIMESTAMPTZ,
            failed_logins INTEGER NOT NULL DEFAULT 0,
            locked_until TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE auth_codes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            purpose VARCHAR(16) NOT NULL CHECK (purpose IN ('verify', 'reset')),
            code_hash CHAR(64) NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            consumed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_auth_codes_user ON auth_codes (user_id, purpose, created_at DESC)")
    op.execute("CREATE INDEX idx_auth_codes_created ON auth_codes (created_at)")
    op.execute("""
        CREATE TABLE auth_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash CHAR(64) NOT NULL UNIQUE,
            expires_at TIMESTAMPTZ NOT NULL,
            revoked_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_auth_sessions_user ON auth_sessions (user_id)")


def downgrade() -> None:
    # DESTRUCTIVO: elimina todas las cuentas.
    op.execute("DROP TABLE IF EXISTS auth_sessions")
    op.execute("DROP TABLE IF EXISTS auth_codes")
    op.execute("DROP TABLE IF EXISTS users")
