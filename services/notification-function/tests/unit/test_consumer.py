"""El consumidor decide ack / reject(DLQ) / nack segun el tipo de error."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import consumer  # noqa: E402
import handler  # noqa: E402


def _deliver(side_effect=None, properties=None):
    channel = MagicMock()
    method = SimpleNamespace(delivery_tag=7)
    with patch.object(consumer, "handle", side_effect=side_effect) as h, \
            patch.object(consumer.time, "sleep") as sleep:
        consumer._on_message(channel, method, properties, b"{}")
    return channel, h, sleep


def test_ack_on_success():
    channel, _, _ = _deliver()
    channel.basic_ack.assert_called_once_with(delivery_tag=7)
    channel.basic_reject.assert_not_called()
    channel.basic_nack.assert_not_called()


def test_invalid_message_is_rejected_without_requeue_so_it_goes_to_dlq():
    channel, _, sleep = _deliver(side_effect=handler.InvalidMessageError("malo"))
    channel.basic_reject.assert_called_once_with(delivery_tag=7, requeue=False)
    channel.basic_ack.assert_not_called()
    sleep.assert_not_called()


def test_transient_error_is_requeued_after_a_pause():
    channel, _, sleep = _deliver(side_effect=RuntimeError("bd caida"))
    channel.basic_nack.assert_called_once_with(delivery_tag=7, requeue=True)
    sleep.assert_called_once()


def test_topology_declares_dead_letter_queue_and_main_queue_with_dlx():
    channel = MagicMock()
    consumer.declare_topology(channel)
    channel.queue_declare.assert_any_call(
        queue="itinerary.events", durable=True,
        arguments={"x-dead-letter-exchange": "itinerary.dlx",
                   "x-dead-letter-routing-key": "itinerary.events.dlq"},
    )
    channel.queue_declare.assert_any_call(queue="itinerary.events.dlq", durable=True)


def test_type_and_message_id_from_amqp_properties_are_passed_to_the_handler():
    props = SimpleNamespace(type="ItineraryDeletedEvent", message_id="42")
    _, handle_mock, _ = _deliver(properties=props)
    handle_mock.assert_called_once_with(b"{}", context={"type": "ItineraryDeletedEvent", "message_id": "42"})
