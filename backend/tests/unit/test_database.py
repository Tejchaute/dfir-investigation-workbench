from sqlalchemy.engine import make_url

from app.db.session import engine


def test_database_engine_uses_postgresql_without_connecting() -> None:
    assert make_url(engine.url).get_backend_name() == "postgresql"
    assert engine.pool._pre_ping is True
