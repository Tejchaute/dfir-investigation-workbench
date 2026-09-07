import uuid
from datetime import datetime

from app.schemas.common import ReadSchema


class AuditEventRead(ReadSchema):
    id: uuid.UUID
    case_id: uuid.UUID | None
    evidence_id: uuid.UUID | None
    action: str
    actor: str
    timestamp: datetime
    details: dict[str, object] | None
