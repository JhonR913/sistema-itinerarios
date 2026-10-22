CREATE TABLE IF NOT EXISTS itineraries (
    id UUID PRIMARY KEY,
    nombre_usuario VARCHAR(120) NOT NULL,
    user_id VARCHAR(120) NOT NULL,
    origin_airport_id VARCHAR(64) NOT NULL,
    origin_iata VARCHAR(4) NOT NULL,
    origin_name VARCHAR(200) NOT NULL,
    origin_city VARCHAR(120) NOT NULL,
    destination_airport_id VARCHAR(64) NOT NULL,
    destination_iata VARCHAR(4) NOT NULL,
    destination_name VARCHAR(200) NOT NULL,
    destination_city VARCHAR(120) NOT NULL,
    travel_date DATE NOT NULL,
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    CHECK (origin_airport_id <> destination_airport_id)
);
CREATE INDEX IF NOT EXISTS idx_itineraries_user_id ON itineraries(user_id);

CREATE TABLE IF NOT EXISTS outbox (
    id SERIAL PRIMARY KEY,
    aggregate_id UUID NOT NULL,
    event_type VARCHAR(120) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_outbox_status ON outbox(status);
