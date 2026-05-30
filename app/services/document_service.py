from __future__ import annotations

import re
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import ClaimDocument
from app.models.document import DocumentType
from app.services.audit_service import record_audit_event

ALLOWED_CONTENT_TYPES: dict[DocumentType, set[str]] = {
    DocumentType.ACCIDENT_PHOTO: {"image/jpeg", "image/png", "image/webp"},
    DocumentType.FIR: {"application/pdf", "image/jpeg", "image/png"},
    DocumentType.RC: {"application/pdf", "image/jpeg", "image/png"},
}


class DocumentValidationError(ValueError):
    pass


def ensure_document_storage() -> None:
    Path(settings.document_storage_path).mkdir(parents=True, exist_ok=True)


def validate_document_upload(
    document_type: DocumentType,
    filename: str,
    content_type: str | None,
    size_bytes: int,
) -> None:
    if not filename.strip():
        raise DocumentValidationError("Filename is required")

    if content_type is None:
        raise DocumentValidationError("Content type is required")

    allowed_types = ALLOWED_CONTENT_TYPES[document_type]
    if content_type not in allowed_types:
        allowed = ", ".join(sorted(allowed_types))
        raise DocumentValidationError(
            f"Unsupported content type for {document_type}: {content_type}. Allowed: {allowed}"
        )

    if size_bytes <= 0:
        raise DocumentValidationError("Uploaded file is empty")

    if size_bytes > settings.max_document_size_bytes:
        raise DocumentValidationError(
            f"Uploaded file exceeds maximum size of {settings.max_document_size_bytes} bytes"
        )


def store_claim_document(
    session: Session,
    claim_id: uuid.UUID,
    document_type: DocumentType,
    original_filename: str,
    content_type: str,
    file_bytes: bytes,
) -> ClaimDocument:
    validate_document_upload(
        document_type=document_type,
        filename=original_filename,
        content_type=content_type,
        size_bytes=len(file_bytes),
    )

    storage_directory = Path(settings.document_storage_path) / str(claim_id)
    storage_directory.mkdir(parents=True, exist_ok=True)

    sanitized_name = sanitize_filename(original_filename)
    stored_filename = f"{uuid.uuid4()}_{sanitized_name}"
    storage_path = storage_directory / stored_filename
    storage_path.write_bytes(file_bytes)

    document = ClaimDocument(
        claim_id=claim_id,
        document_type=document_type,
        original_filename=original_filename,
        storage_path=str(storage_path),
        content_type=content_type,
        size_bytes=len(file_bytes),
    )
    session.add(document)
    session.flush()
    record_audit_event(
        session,
        entity_type="document",
        entity_id=str(document.id),
        claim_id=claim_id,
        action="CLAIM_DOCUMENT_UPLOADED",
        details={
            "document_type": document_type.value,
            "original_filename": original_filename,
            "content_type": content_type,
            "size_bytes": len(file_bytes),
        },
    )
    session.commit()
    session.refresh(document)
    return document


def list_claim_documents(session: Session, claim_id: uuid.UUID) -> list[ClaimDocument]:
    statement = (
        select(ClaimDocument)
        .where(ClaimDocument.claim_id == claim_id)
        .order_by(ClaimDocument.created_at.desc())
    )
    return list(session.scalars(statement).all())


def sanitize_filename(filename: str) -> str:
    compact = re.sub(r"\s+", "_", filename.strip())
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "", compact)
    return cleaned or "document"
