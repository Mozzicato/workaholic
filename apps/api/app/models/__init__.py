# Import every model here so Alembic autogenerate sees the complete schema.
from app.models.base import Base
from app.models.user import User

__all__ = ["Base", "User"]
