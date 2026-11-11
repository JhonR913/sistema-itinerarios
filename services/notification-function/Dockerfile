FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /home/app

COPY requirements.lock .
RUN pip install --no-cache-dir --only-binary=:all: --require-hashes -r requirements.lock

RUN useradd --create-home --uid 10001 appuser \
    && chown root:root /home/app \
    && chmod 0555 /home/app

COPY --chown=root:root --chmod=0444 handler.py consumer.py reminders.py reminder_worker.py mailer.py alembic.ini ./
COPY --chown=root:root --chmod=0555 alembic/ ./alembic/

USER appuser

# Aplica migraciones (idempotentes) y luego consume la cola.
CMD ["sh", "-c", "alembic upgrade head && exec python consumer.py"]
