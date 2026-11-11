FROM python:3.15-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir --only-binary=:all: --require-hashes -r requirements.lock
COPY app/ ./app/
COPY alembic.ini ./
COPY alembic/ ./alembic/
RUN useradd -m appuser
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
