from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A Workaholic account.

    Credentials live with the identity provider. `auth_subject` links this row to the
    provider's user; the internal `id` is what every user-owned resource references, so
    the provider can be replaced without rewriting ownership across the schema.
    """

    __tablename__ = "users"

    auth_subject: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    auth_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320))
    name: Mapped[str | None] = mapped_column(String(200))
