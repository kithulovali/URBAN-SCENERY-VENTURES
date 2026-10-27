import uuid
from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from settings import Model
from models.shared import Timestamp


class User(Model, Timestamp):
    __tablename__ = "users"

    private_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    public_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, index=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    contact: Mapped[str | None] = mapped_column(String(128), nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String(256), nullable=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("user_roles.id"), nullable=False)

    role: Mapped["UserRole"] = relationship("UserRole", back_populates="users")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user")

    @property
    def role_name(self) -> str:
        return self.role.name if self.role else "GUEST"
