from uuid import UUID

from fastapi import APIRouter
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi import status

from app.api.dependencies import CurrentUser
from app.api.dependencies import DatabaseSession
from app.api.dependencies import require_roles
from app.models.user import UserRole
from app.models.document import DocumentType
from app.schemas.document import ClaimDocumentRead
from app.services.claim_service import get_claim_by_id
from app.services.document_service import DocumentValidationError
from app.services.document_service import list_claim_documents
from app.services.document_service import store_claim_document

router = APIRouter(prefix="/claims/{claim_id}/documents", tags=["documents"])


@router.post("", response_model=ClaimDocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_claim_document(
    claim_id: UUID,
    session: DatabaseSession,
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    current_user: CurrentUser
) -> ClaimDocumentRead:
    claim = get_claim_by_id(session, claim_id)
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )

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
    claim_id: UUID,
    session: DatabaseSession,
    current_user: CurrentUser
) -> list[ClaimDocumentRead]:
    claim = get_claim_by_id(session, claim_id)
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )

    documents = list_claim_documents(session, claim_id)
    return [ClaimDocumentRead.model_validate(document) for document in documents]


