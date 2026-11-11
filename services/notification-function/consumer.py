"""
Consumidor real de RabbitMQ para desarrollo local (sin el stack completo
de OpenFaaS). En produccion, el mismo handler.py se invoca via el
conector queue-worker de OpenFaaS (ADR-004, Documento_Arquitectura.docx).

Politica de errores:
  - OK                  -> ack.
  - InvalidMessageError -> reject(requeue=False): va a la DLQ (no se
                           reintenta algo que nunca va a funcionar).
  - Error transitorio   -> nack(requeue=True) tras una pausa corta (BD caida).
Reconexion automatica con backoff si RabbitMQ aun no esta listo.
"""
import logging
import os
import time

import pika
from pika.exceptions import AMQPError

from handler import InvalidMessageError, handle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("notification-consumer")

QUEUE_NAME = "itinerary.events"
DLX_NAME = "itinerary.dlx"
DLQ_NAME = "itinerary.events.dlq"
TRANSIENT_RETRY_DELAY_SECONDS = 3


def declare_topology(channel) -> None:
    """Debe coincidir exactamente con la del outbox-worker."""
    channel.exchange_declare(exchange=DLX_NAME, exchange_type="direct", durable=True)
    channel.queue_declare(queue=DLQ_NAME, durable=True)
    channel.queue_bind(queue=DLQ_NAME, exchange=DLX_NAME, routing_key=DLQ_NAME)
    channel.queue_declare(
        queue=QUEUE_NAME, durable=True,
        arguments={"x-dead-letter-exchange": DLX_NAME, "x-dead-letter-routing-key": DLQ_NAME},
    )


def _on_message(channel, method, properties, body):
    try:
        handle(body, context={"type": getattr(properties, "type", None),
                              "message_id": getattr(properties, "message_id", None)})
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except InvalidMessageError as exc:
        logger.error('{"event":"message_rejected_to_dlq","error":"%s"}', str(exc))
        channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as exc:  # noqa: BLE001 - transitorio: se reintenta
        logger.error('{"event":"handler_failed_will_retry","error":"%s"}', repr(exc))
        time.sleep(TRANSIENT_RETRY_DELAY_SECONDS)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def run(rabbitmq_url: str, reconnect_delay_seconds: float = 5.0) -> None:
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
            channel = connection.channel()
            declare_topology(channel)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=_on_message)
            logger.info('{"event":"consumer_started","queue":"%s"}', QUEUE_NAME)
            channel.start_consuming()
        except AMQPError as exc:
            logger.error('{"event":"consumer_reconnecting","error":"%s"}', repr(exc))
            time.sleep(reconnect_delay_seconds)


if __name__ == "__main__":
    run(os.environ["RABBITMQ_URL"])
