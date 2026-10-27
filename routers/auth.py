from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from settings import get_db
from schemas.user_schema import UserRegister, UserLogin, UserOut, TokenOut
from services.user_service import UserService
from core.security import verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    user_svc = UserService(db)
    existing_user = user_svc.get_by_email(payload.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )

    # Public registration must never allow callers to assign privileged roles.
    return user_svc.create_user(
        email=payload.email,
        name=payload.name,
        password=payload.password,
        role="CUSTOMER",
        contact=payload.contact,
    )


@router.post("/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user_svc = UserService(db)
    user = user_svc.get_by_email(payload.email)
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(data={"sub": str(user.private_id), "role": user.role.name if user.role else "GUEST"})
    return TokenOut(access_token=token, token_type="bearer", user=user)


@router.get("/me", response_model=UserOut)
def get_me(current_user=Depends(get_current_user)):
    return current_user
