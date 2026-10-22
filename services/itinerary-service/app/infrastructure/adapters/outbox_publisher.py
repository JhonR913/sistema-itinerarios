import json
from sqlalchemy import create_engine, text
from app.domain.ports import EventPublisherPort


class OutboxEventPublisher(EventPublisherPort):
    def __init__(self, database_url: str):
        self._engine = create_engine(database_url)

    def enqueue(self, event_type: str, payload: dict, aggregate_id: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO outbox (aggregate_id, event_type, payload, status, created_at)
                    VALUES (:aggregate_id, :event_type, :payload, 'PENDING', now())
                """),
                {"aggregate_id": aggregate_id, "event_type": event_type, "payload": json.dumps(payload)},
            )
