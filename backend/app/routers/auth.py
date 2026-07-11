from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_current_user, get_db
from ..models import User
from ..schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from ..security import create_access_token, hash_password, verify_password
from ..services import billing as billing_svc
from ..services.rate_limit import check_auth_rate_limit

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    q = billing_svc.quota_payload(user)
    return UserOut(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
        free_left=q["free_left"],
        free_limit=q["free_limit"],
        free_used=q["free_used"],
        credit_balance=q["credit_balance"],
        period=q["period"],
        telegram_linked=bool(user.telegram_id),
        telegram_id=user.telegram_id,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    check_auth_rate_limit(request)
    if not settings.registration_enabled:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Регистрация временно закрыта. Войдите в существующий аккаунт.",
        )
    email = str(payload.email).strip().lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        # Одинаковый тон с login — меньше утечки «email занят»
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Не удалось зарегистрироваться. Войдите или укажите другой email.",
        )
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    check_auth_rate_limit(request)
    email = str(payload.email).strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    billing_svc.roll_free_month(current_user)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return _user_out(current_user)
