"""Variables minimas para importar app.settings en las pruebas. Son valores
de prueba, no secretos reales."""
import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET", "unit-test-secret-not-for-production")
