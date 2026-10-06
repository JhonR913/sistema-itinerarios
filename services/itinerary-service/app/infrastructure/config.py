import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./itineraries.db")
AIRPORT_SERVICE_URL = os.getenv("AIRPORT_SERVICE_URL", "http://localhost:8001/api")
AIRPORT_SERVICE_TIMEOUT = float(os.getenv("AIRPORT_SERVICE_TIMEOUT", "3"))
