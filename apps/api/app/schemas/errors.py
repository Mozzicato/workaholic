from pydantic import BaseModel


class ErrorDetail(BaseModel):
    field: str
    issue: str


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str | None
    details: list[ErrorDetail] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


AUTH_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Missing, invalid or expired access token"},
    503: {"model": ErrorResponse, "description": "Sign-in could not be verified right now"},
}
