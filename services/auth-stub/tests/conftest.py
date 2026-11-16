import os

os.environ.setdefault("JWT_SECRET", "unit-test-secret-not-for-production")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
