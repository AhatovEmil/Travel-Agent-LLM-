"""Tribute webhook: проверка подписи и начисление кредитов."""

from __future__ import annotations

import hashlib
import hmac
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import PendingCredit, TributePayment, User, utcnow
from .billing import add_credits

log = logging.getLogger(__name__)


def verify_tribute_signature(body: bytes, signature: str | None) -> bool:
    key = (settings.tribute_api_key or "").strip()
    if not key or not signature:
        return False
    expected = hmac.new(key.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip())


def credits_for_product(product_id) -> int:
    mapping = settings.tribute_product_map()
    return int(mapping.get(str(product_id).strip(), 0))


def event_key_from_payload(name: str, payload: dict, sent_at: str | None) -> str:
    tg = str(payload.get("telegram_user_id") or payload.get("telegram_id") or "")
    pid = str(payload.get("product_id") or "")
    stamp = sent_at or payload.get("created_at") or ""
    raw = f"{name}:{pid}:{tg}:{stamp}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:64]


def process_tribute_event(data: dict, db: Session) -> dict:
    """Обработать JSON webhook. Возвращает статус для ответа."""
    name = str(data.get("name") or "")
    payload = data.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {}

    if name not in ("new_digital_product", "digital_product"):
        return {"ok": True, "action": "ignored", "reason": f"event:{name}"}

    product_id = str(payload.get("product_id") or "").strip()
    telegram_id = str(
        payload.get("telegram_user_id") or payload.get("telegram_id") or ""
    ).strip()
    credits = credits_for_product(product_id)
    sent_at = str(data.get("sent_at") or data.get("created_at") or "")
    key = event_key_from_payload(name, payload, sent_at)

    existing = db.scalar(select(TributePayment).where(TributePayment.event_key == key))
    if existing is not None:
        return {"ok": True, "action": "duplicate", "event_key": key}

    if credits < 1:
        pay = TributePayment(
            event_key=key,
            product_id=product_id,
            telegram_id=telegram_id or "unknown",
            user_id=None,
            credits=0,
            status="ignored",
            raw_name=name,
        )
        db.add(pay)
        db.commit()
        return {"ok": True, "action": "ignored", "reason": "unknown_product", "product_id": product_id}

    if not telegram_id:
        pay = TributePayment(
            event_key=key,
            product_id=product_id,
            telegram_id="",
            user_id=None,
            credits=credits,
            status="ignored",
            raw_name=name,
        )
        db.add(pay)
        db.commit()
        return {"ok": True, "action": "ignored", "reason": "no_telegram_id"}

    user = db.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        pay = TributePayment(
            event_key=key,
            product_id=product_id,
            telegram_id=telegram_id,
            user_id=None,
            credits=credits,
            status="pending",
            raw_name=name,
        )
        db.add(pay)
        pending = db.scalar(
            select(PendingCredit).where(
                PendingCredit.telegram_id == telegram_id,
                PendingCredit.event_key == key,
            )
        )
        if pending is None:
            db.add(
                PendingCredit(
                    telegram_id=telegram_id,
                    event_key=key,
                    product_id=product_id,
                    credits=credits,
                )
            )
        db.commit()
        log.info("tribute pending credits=%s tg=%s", credits, telegram_id)
        return {"ok": True, "action": "pending", "credits": credits, "telegram_id": telegram_id}

    add_credits(user, credits, db)
    pay = TributePayment(
        event_key=key,
        product_id=product_id,
        telegram_id=telegram_id,
        user_id=user.id,
        credits=credits,
        status="credited",
        raw_name=name,
    )
    db.add(pay)
    db.commit()
    log.info("tribute credited user=%s credits=%s", user.id, credits)
    return {
        "ok": True,
        "action": "credited",
        "user_id": user.id,
        "credits": credits,
        "balance": user.credit_balance,
    }


def claim_pending_credits(user: User, db: Session) -> int:
    """После привязки telegram_id зачислить отложенные платежи."""
    if not user.telegram_id:
        return 0
    rows = db.scalars(
        select(PendingCredit).where(
            PendingCredit.telegram_id == user.telegram_id,
            PendingCredit.claimed_at.is_(None),
        )
    ).all()
    total = 0
    now = utcnow()
    for row in rows:
        if row.credits > 0:
            add_credits(user, row.credits, db)
            total += row.credits
        row.claimed_at = now
        db.add(row)
        pay = db.scalar(select(TributePayment).where(TributePayment.event_key == row.event_key))
        if pay and pay.status == "pending":
            pay.status = "credited"
            pay.user_id = user.id
            db.add(pay)
    if rows:
        db.commit()
        db.refresh(user)
    return total
