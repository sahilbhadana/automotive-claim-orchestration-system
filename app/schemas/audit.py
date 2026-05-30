from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    claim_id: UUID | None
    entity_type: str
    entity_id: str
    action: str
    actor: str
    details: dict
    created_at: datetime
