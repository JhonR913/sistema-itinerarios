
FROM python:3.11-slim

WORKDIR /home/app

COPY requirements.txt .
RUN pip install --no-cache-dir --only-binary=:all: -r requirements.txt

RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /home/app

COPY --chown=appuser:appuser handler.py consumer.py ./

ENV PYTHONUNBUFFERED=1

USER appuser

CMD ["python", "consumer.py"]
