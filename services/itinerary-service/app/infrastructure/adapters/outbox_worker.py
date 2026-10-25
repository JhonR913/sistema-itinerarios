import json
import logging
import os
import time

import pika
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("outbox-worker")


def run(database_url: str, rabbitmq_url: str, poll_interval_seconds: int = 2):
    engine = create_engine(database_url)
    connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
    channel = connection.channel()
    channel.queue_declare(queue="itinerary.created", durable=True)

    while True:
        with engine.begin() as conn:
            rows = conn.execute(
                text("SELECT id, event_type, payload FROM outbox WHERE status = 'PENDING' LIMIT 20")
            ).mappings().all()

            for row in rows:
                try:
                    channel.basic_publish(
                        exchange="", routing_key="itinerary.created",
                        body=row["payload"] if isinstance(row["payload"], str) else json.dumps(row["payload"]),
                        properties=pika.BasicProperties(delivery_mode=2),
                    )
                    conn.execute(
                        text("UPDATE outbox SET status = 'PUBLISHED' WHERE id = :id"),
                        {"id": row["id"]},
                    )
                except Exception as exc:
                    logger.error('{"event":"outbox_publish_failed","outbox_id":"%s","error":"%s"}',
                                 row["id"], str(exc))

        time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    run(os.environ["DATABASE_URL"], os.environ["RABBITMQ_URL"])
