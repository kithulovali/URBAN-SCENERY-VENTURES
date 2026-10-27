from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from settings import get_db
from schemas.user_schema import UserOut, UserUpdate
from services.user_service import UserService
from core.security import get_current_user, get_current_admin

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=List[UserOut], dependencies=[Depends(get_current_admin)])
def list_users(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return UserService(db).get_all_users(offset=offset, limit=limit)


@router.get("/{public_id}", response_model=UserOut)
def get_user_by_id(
    public_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_svc = UserService(db)
    user = user_svc.get_by_public_id(public_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    is_admin = str(getattr(getattr(current_user, "role", None), "name", "")).upper() == "ADMIN"
    if current_user.public_id != user.public_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own profile")
    return user


@router.put("/{public_id}", response_model=UserOut)
def update_user_profile(
    public_id: UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_svc = UserService(db)
    user = user_svc.get_by_public_id(public_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    is_admin = str(getattr(getattr(current_user, "role", None), "name", "")).upper() == "ADMIN"
    if current_user.public_id != user.public_id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile",
        )

    return user_svc.update_user(public_id, updates=payload.model_dump(exclude_unset=True))


@router.delete("/{public_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
def delete_user(public_id: UUID, db: Session = Depends(get_db)):
    if not UserService(db).remove_user(public_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
