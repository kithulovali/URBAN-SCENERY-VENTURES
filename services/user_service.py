from uuid import UUID
from typing import Optional
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from models.users_model import User
from models.utils import UserRole
from core.security import hash_password
from services.lookup_service import get_lookup

_UPDATABLE_FIELDS = {"name", "contact", "role"}

class UserService:
    def __init__(self, session: Session):
        self.session = session

    def create_user(self, email: str, name: str, password: Optional[str] = None,
                    role: str = "CUSTOMER", contact: Optional[str] = None) -> User:
        role_row = get_lookup(self.session, UserRole, role or "CUSTOMER")
        user = User(email=email.strip().lower(), name=name.strip(),
                    hashed_password=hash_password(password) if password else None,
                    role=role_row, contact=contact)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def get_by_email(self, email: str) -> Optional[User]:
        return self.session.scalars(select(User).where(User.email == email.strip().lower())).first()

    def get_by_public_id(self, public_id: UUID | str) -> Optional[User]:
        try:
            parsed = UUID(str(public_id))
        except (TypeError, ValueError):
            return None
        return self.session.scalars(select(User).where(User.public_id == parsed)).first()

    def get_user(self, private_id: str | UUID) -> Optional[User]:
        try:
            return self.session.get(User, UUID(str(private_id)))
        except (TypeError, ValueError):
            return None

    def get_all_users(self, offset: int = 0, limit: int = 100):
        return list(self.session.scalars(select(User).offset(offset).limit(limit)).all())

    def update_user(self, public_id: UUID | str, updates: dict[str, object] | None = None) -> Optional[User]:
        user = self.get_by_public_id(public_id) or self.get_user(public_id)
        if user is None:
            return None
        for field, value in (updates or {}).items():
            if field not in _UPDATABLE_FIELDS or value is None:
                continue
            if field == "role":
                user.role = get_lookup(self.session, UserRole, str(value))
            else:
                setattr(user, field, value)
        self.session.commit()
        self.session.refresh(user)
        return user

    def remove_user(
        self,
        public_id: UUID | str | None = None,
        *,
        private_id: UUID | str | None = None,
    ) -> bool:
        """Remove a user by public ID or legacy private_id argument.

        ``private_id`` is retained for compatibility with older callers.
        """
        identifier = public_id if public_id is not None else private_id
        if identifier is None:
            return False
        user = self.get_by_public_id(identifier) or self.get_user(identifier)
        if user is None:
            return False
        self.session.delete(user)
        self.session.commit()
        return True
