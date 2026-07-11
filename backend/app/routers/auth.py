from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_current_user, get_db
from ..models import User
from ..schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from ..security import create_access_token, hash_password, verify_password
from ..services.rate_limit import check_auth_rate_limit

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    check_auth_rate_limit(request)
    if not settings.registration_enabled:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Регистрация временно закрыта. Войдите в существующий аккаунт.",
        )
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        # Одинаковый тон с login — меньше утечки «email занят»
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Не удалось зарегистрироваться. Войдите или укажите другой email.",
        )
    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    check_auth_rate_limit(request)
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
