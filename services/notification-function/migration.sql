CREATE TABLE IF NOT EXISTS notification_history (
    id SERIAL PRIMARY KEY,
    itinerary_id UUID NOT NULL,
    channel VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    sent_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_notification_itinerary_unique ON notification_history(itinerary_id);
