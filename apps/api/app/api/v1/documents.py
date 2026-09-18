from fastapi import APIRouter, File, UploadFile, status
from pydantic import BaseModel, ConfigDict

from app.api.deps import LLM, CurrentUser, SessionDep
from app.schemas.errors import AUTH_ERROR_RESPONSES, ErrorResponse
from app.services.candidate import CandidateProfileService
from app.services.documents import MAX_UPLOAD_BYTES, extract_text, parse_document
from app.services.documents.accept import accept_import
from app.services.documents.parsing import DocumentContents

router = APIRouter(prefix="/documents", tags=["documents"])


class ImportProposal(BaseModel):
    """What an uploaded resume appears to contain. Nothing is recorded until it is accepted."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    pages: int
    contents: DocumentContents
    #  What the document did not support, so the user can see what was left out.
    dropped: list[str]
    prompt_version: str
    model: str


@router.post(
    "/import",
    response_model=ImportProposal,
    status_code=status.HTTP_200_OK,
    responses={
        **AUTH_ERROR_RESPONSES,
        422: {"model": ErrorResponse, "description": "The file could not be read"},
        503: {"model": ErrorResponse, "description": "AI is unavailable"},
    },
)
async def import_document(
    user: CurrentUser,
    session: SessionDep,
    llm: LLM,
    document: UploadFile = File(description="An existing resume, as PDF or DOCX"),
) -> ImportProposal:
    """Read an existing resume and propose what it says (PRD §37).

    Nothing is written to the career record here. The file is identified by its bytes rather
    than its name, held in memory, reduced to text, read into structure, and every item is
    checked against the document's own words. The result is a proposal for the user to accept,
    which is the confirmation step the PRD requires — and the reason a mis-parse cannot quietly
    become part of somebody's history.
    """
    # The profile is created now so the user has somewhere to accept the proposal into.
    await CandidateProfileService(session).get_or_create(user)

    content = await document.read(MAX_UPLOAD_BYTES + 1)
    extracted = extract_text(content)
    parsed = await parse_document(llm, extracted.text)
    return ImportProposal(
        kind=extracted.kind.value,
        pages=extracted.pages,
        contents=parsed.contents,
        dropped=parsed.dropped,
        prompt_version=parsed.prompt_version,
        model=parsed.model,
    )


class AcceptResultRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    added: list[str]
    #  Already in the record, so not added a second time.
    skipped: list[str]


@router.post(
    "/import/accept",
    response_model=AcceptResultRead,
    responses=AUTH_ERROR_RESPONSES,
)
async def accept_imported(
    user: CurrentUser, session: SessionDep, accepted: DocumentContents
) -> AcceptResultRead:
    """Add what the user confirmed from an upload to their career record.

    Each item is recorded as evidence from an uploaded document, confirmed by the user. Nothing
    already in the record is duplicated, and details the user filled in themselves are never
    overwritten by what a document said.
    """
    _, result = await accept_import(session, user, accepted)
    return AcceptResultRead(added=result.added, skipped=result.skipped)
