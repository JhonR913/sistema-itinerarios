FROM ghcr.io/openfaas/classic-watchdog:0.3.4 AS watchdog
FROM python:3.11-slim
COPY --from=watchdog /fwatchdog /usr/bin/fwatchdog
RUN chmod +x /usr/bin/fwatchdog

WORKDIR /home/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY handler.py .

ENV fprocess="python3 handler.py"
ENV DATABASE_URL=""
EXPOSE 8080
CMD ["fwatchdog"]
