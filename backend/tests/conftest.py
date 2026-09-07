import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://dfir:test-only@localhost:5432/dfir_test"
)
