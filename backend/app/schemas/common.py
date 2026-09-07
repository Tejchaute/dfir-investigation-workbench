from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class ReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimezoneAwareSchema(BaseModel):
    @field_validator("*", mode="after")
    @classmethod
    def require_timezone_for_datetimes(cls, value: object) -> object:
        if isinstance(value, datetime) and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("datetime values must include timezone information")
        return value
