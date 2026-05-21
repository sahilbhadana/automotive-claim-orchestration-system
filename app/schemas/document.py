from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict

from app.models.document import DocumentType


class ClaimDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    claim_id: UUID
    document_type: DocumentType
    original_filename: str
    storage_path: str
    content_type: str
    size_bytes: int
    created_at: datetime
