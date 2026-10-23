-- Tabla airports tal como quedo definida en el Diagrama Entidad-Relacion
-- (Documento_Diseno_y_Diagramas.docx figura 5). Es el almacen durable;
-- Redis sigue siendo la cache rapida por encima de esta tabla.
CREATE TABLE IF NOT EXISTS airports (
    id VARCHAR(64) PRIMARY KEY,
    external_id VARCHAR(64) NOT NULL,
    iata_code VARCHAR(4) NOT NULL,
    name VARCHAR(200) NOT NULL,
    city VARCHAR(120) NOT NULL,
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(9,6) NOT NULL,
    cached_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_airports_iata ON airports(iata_code);
