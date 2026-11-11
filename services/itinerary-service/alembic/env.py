"""Entorno Alembic. La URL sale de DATABASE_URL (nunca del .ini, para no
versionar credenciales). Se toma un advisory lock de PostgreSQL para que dos
contenedores arrancando a la vez no apliquen la misma migracion en paralelo."""
import os

from alembic import context
from sqlalchemy import create_engine, text

config = context.config
LOCK_ID = 727402  # unico por servicio/base de datos


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError("DATABASE_URL no esta definida")
    return url


def run_migrations_offline() -> None:
    context.configure(url=_database_url(), literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_database_url(), pool_pre_ping=True)
    with engine.connect() as connection:
        connection.execute(text("SELECT pg_advisory_lock(:k)"), {"k": LOCK_ID})
        connection.commit()
        try:
            context.configure(connection=connection, target_metadata=None)
            with context.begin_transaction():
                context.run_migrations()
            connection.commit()
        finally:
            connection.rollback()
            connection.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": LOCK_ID})
            connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
