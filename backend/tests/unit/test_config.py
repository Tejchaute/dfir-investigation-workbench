import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.config import Settings


def test_configuration_loads_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@db:5432/workbench")
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:4173"]')
    settings = Settings()
    assert settings.database_url.endswith("/workbench")
    assert settings.cors_origins == ["http://localhost:4173"]


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(PydanticValidationError):
        Settings(_env_file=None)


def test_non_postgresql_database_is_rejected() -> None:
    with pytest.raises(PydanticValidationError):
        Settings(database_url="sqlite:///unsafe.db", _env_file=None)
