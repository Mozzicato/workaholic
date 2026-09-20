import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str | None
    name: str | None
    auth_provider: str
    created_at: datetime
    # Whether this account may open the admin dashboard. Decided by the server, from settings.
    is_admin: bool = False
