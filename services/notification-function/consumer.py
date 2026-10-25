"""
Consumidor real de RabbitMQ para desarrollo local (sin el stack completo
de OpenFaaS). En produccion, el mismo handler.py se invoca via el
conector queue-worker de OpenFaaS (ADR-004, Documento_Arquitectura.docx).
Aqui se consume directamente para poder verificar la conexion con
RabbitMQ de punta a punta en este entorno."""
import logging
import os

import pika

from handler import handle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("notification-consumer")

QUEUE_NAME = "itinerary.created"


def _on_message(channel, method, properties, body):
    try:
        handle(body, context=None)
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as exc:
        logger.error('{"event":"handler_failed","error":"%s"}', str(exc))
        # requeue=True: at-least-once, handle() debe ser idempotente (ya lo es).
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def run(rabbitmq_url: str):
    connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=_on_message)
    logger.info('{"event":"consumer_started","queue":"%s"}', QUEUE_NAME)
    channel.start_consuming()


if __name__ == "__main__":
    run(os.environ["RABBITMQ_URL"])
