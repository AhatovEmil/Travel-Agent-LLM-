"""Месячная квота бесплатных генераций + купленные кредиты."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..config import settings
from ..models import User


def current_period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def roll_free_month(user: User) -> None:
    period = current_period()
    if (user.free_used_month or "") != period:
        user.free_used_month = period
        user.free_used_count = 0


def free_left(user: User) -> int:
    roll_free_month(user)
    limit = max(0, int(settings.free_generations_per_month))
    used = max(0, int(user.free_used_count or 0))
    return max(0, limit - used)


def quota_payload(user: User) -> dict:
    roll_free_month(user)
    limit = max(0, int(settings.free_generations_per_month))
    used = max(0, int(user.free_used_count or 0))
    credits = max(0, int(user.credit_balance or 0))
    return {
        "free_left": max(0, limit - used),
        "free_limit": limit,
        "free_used": used,
        "credit_balance": credits,
        "period": user.free_used_month or current_period(),
    }


def packages_payload() -> dict:
    bot = (settings.telegram_bot_username or "").strip().lstrip("@")
    bot_url = f"https://t.me/{bot}" if bot else (settings.support_telegram or "https://t.me/")
    return {
        "packages": settings.generation_packages,
        "telegram_url": bot_url if bot else ((settings.support_telegram or "").strip() or "https://t.me/"),
        "bot_url": settings.bot_deep_link("buy"),
        "bot_username": bot,
        "free_generations_per_month": max(0, int(settings.free_generations_per_month)),
        "tribute_configured": bool(settings.tribute_product_map()),
    }


def quota_exceeded_detail(user: User) -> dict:
    q = quota_payload(user)
    packs = packages_payload()
    return {
        "code": "quota_exceeded",
        "message": (
            "Лимит бесплатных генераций на этот месяц исчерпан. "
            "Купите пакет через Telegram-бота (Tribute) или дождитесь следующего месяца."
        ),
        "free_left": q["free_left"],
        "free_limit": q["free_limit"],
        "credits": q["credit_balance"],
        "period": q["period"],
        "packages": packs["packages"],
        "telegram_url": packs["telegram_url"],
        "bot_url": packs["bot_url"],
        "telegram_linked": bool(user.telegram_id),
    }


def check_and_consume_generation(user: User, db: Session) -> None:
    """Списать 1 генерацию (free → credits). 402 если нет квоты."""
    roll_free_month(user)
    limit = max(0, int(settings.free_generations_per_month))
    if int(user.free_used_count or 0) < limit:
        user.free_used_count = int(user.free_used_count or 0) + 1
        db.add(user)
        db.commit()
        db.refresh(user)
        return
    if int(user.credit_balance or 0) > 0:
        user.credit_balance = int(user.credit_balance) - 1
        db.add(user)
        db.commit()
        db.refresh(user)
        return
    raise HTTPException(
        status.HTTP_402_PAYMENT_REQUIRED,
        detail=quota_exceeded_detail(user),
    )


def add_credits(user: User, amount: int, db: Session) -> User:
    if amount < 1 or amount > 10_000:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "amount must be between 1 and 10000",
        )
    user.credit_balance = int(user.credit_balance or 0) + amount
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
