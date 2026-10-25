
FROM python:3.11-slim

WORKDIR /home/app

COPY requirements.lock .
RUN pip install --no-cache-dir --only-binary=:all: --require-hashes -r requirements.lock

RUN useradd --create-home --uid 10001 appuser \
    && chown root:root /home/app \
    && chmod 0555 /home/app

COPY --chown=root:root --chmod=0444 handler.py consumer.py ./

ENV PYTHONUNBUFFERED=1

USER appuser

CMD ["python", "consumer.py"]
