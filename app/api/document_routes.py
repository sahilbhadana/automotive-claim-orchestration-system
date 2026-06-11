from pathlib import Path
from uuid import UUID

from fastapi import APIRouter
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi import status
from fastapi.responses import FileResponse

from app.api.authz import ensure_claim_view_access
from app.api.authz import ensure_claimant_upload_access
from app.api.dependencies import CurrentUser
from app.api.dependencies import DatabaseSession
from app.models.document import DocumentType
from app.schemas.document import ClaimDocumentRead
from app.services.claim_service import get_claim_by_id
from app.services.document_service import DocumentValidationError
from app.services.document_service import get_claim_document_by_id
from app.services.document_service import list_claim_documents
from app.services.document_service import store_claim_document

router = APIRouter(prefix="/claims/{claim_id}/documents", tags=["documents"])


@router.post("", response_model=ClaimDocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_claim_document(
    claim_id: UUID,
    session: DatabaseSession,
    *,
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    current_user: CurrentUser,
) -> ClaimDocumentRead:
    claim = get_claim_by_id(session, claim_id)
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )
    # Only the claim's own claimant supplies evidence; staff review.
    ensure_claimant_upload_access(current_user, claim)

    file_bytes = await file.read()

    try:
        document = store_claim_document(
            session=session,
            claim_id=claim_id,
            document_type=document_type,
            original_filename=file.filename or "",
            content_type=file.content_type or "",
            file_bytes=file_bytes,
        )
    except DocumentValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    finally:
        await file.close()

    return ClaimDocumentRead.model_validate(document)


@router.get("", response_model=list[ClaimDocumentRead])
async def list_claim_documents_endpoint(
    claim_id: UUID, session: DatabaseSession, current_user: CurrentUser
) -> list[ClaimDocumentRead]:
    ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))

    documents = list_claim_documents(session, claim_id)
    return [ClaimDocumentRead.model_validate(document) for document in documents]


@router.get("/{document_id}/download")
async def download_claim_document(
    claim_id: UUID,
    document_id: UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> FileResponse:
    ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))

    document = get_claim_document_by_id(session, claim_id, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    file_path = Path(document.storage_path)
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Document file is missing from storage",
        )

    return FileResponse(
        path=file_path,
        media_type=document.content_type,
        filename=document.original_filename,
    )
