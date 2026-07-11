import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_current_user, get_db
from ..models import User
from ..schemas import (
    AdminCreditRequest,
    AdminCreditResponse,
    BillingPackagesOut,
    TelegramLinkInitData,
    TelegramLinkResponse,
    TelegramLinkWidget,
)
from ..services import billing as billing_svc
from ..services import telegram_auth, telegram_bot, tribute

log = logging.getLogger(__name__)

router = APIRouter(tags=["billing"])


@router.get("/api/billing/packages", response_model=BillingPackagesOut)
def list_packages():
    return billing_svc.packages_payload()


@router.post("/api/admin/credits", response_model=AdminCreditResponse)
def admin_add_credits(
    payload: AdminCreditRequest,
    db: Session = Depends(get_db),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
):
    expected = (settings.admin_credit_token or "").strip()
    if not expected:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "ADMIN_CREDIT_TOKEN не задан — начисление выключено.",
        )
    if not x_admin_token or x_admin_token != expected:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid admin token")
    email = str(payload.email).strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    billing_svc.add_credits(user, payload.amount, db)
    return AdminCreditResponse(
        email=user.email,
        credit_balance=user.credit_balance,
        added=payload.amount,
    )


def _link_telegram(user: User, telegram_id: str, db: Session) -> TelegramLinkResponse:
    other = db.scalar(
        select(User).where(User.telegram_id == telegram_id, User.id != user.id)
    )
    if other is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Этот Telegram уже привязан к другому аккаунту.",
        )
    user.telegram_id = telegram_id
    db.add(user)
    db.commit()
    db.refresh(user)
    claimed = tribute.claim_pending_credits(user, db)
    db.refresh(user)
    return TelegramLinkResponse(
        telegram_linked=True,
        telegram_id=telegram_id,
        credits_claimed=claimed,
        credit_balance=int(user.credit_balance or 0),
    )


@router.post("/api/billing/telegram/link", response_model=TelegramLinkResponse)
def link_telegram_webapp(
    payload: TelegramLinkInitData,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    parsed = telegram_auth.parse_webapp_init_data(payload.init_data)
    return _link_telegram(current_user, parsed["telegram_id"], db)


@router.post("/api/billing/telegram/link-widget", response_model=TelegramLinkResponse)
def link_telegram_widget(
    payload: TelegramLinkWidget,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    parsed = telegram_auth.parse_login_widget(payload.model_dump())
    return _link_telegram(current_user, parsed["telegram_id"], db)


@router.get("/api/billing/tribute/webhook")
def tribute_webhook_ping():
    """Проверка доступности URL (Tribute / мониторинг)."""
    configured = bool((settings.tribute_api_key or "").strip())
    return {"ok": True, "tribute_key_configured": configured}


@router.post("/api/billing/tribute/webhook")
async def tribute_webhook(
    request: Request,
    db: Session = Depends(get_db),
    trbt_signature: str | None = Header(default=None, alias="trbt-signature"),
):
    import json

    body = await request.body()
    # Пустой / тестовый ping без тела — отвечаем 200, чтобы Tribute принял URL
    if not body or body.strip() in (b"", b"{}", b"null"):
        return {"ok": True, "action": "ping"}

    if not (settings.tribute_api_key or "").strip():
        log.error("tribute webhook: TRIBUTE_API_KEY missing")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "TRIBUTE_API_KEY не задан",
        )

    # Иногда заголовок приходит в другом регистре / имени
    if not trbt_signature:
        trbt_signature = request.headers.get("trbt-signature") or request.headers.get(
            "Trbt-Signature"
        )

    if not tribute.verify_tribute_signature(body, trbt_signature):
        preview = body[:300].decode("utf-8", errors="replace")
        log.warning(
            "tribute webhook: bad signature, len(body)=%s preview=%s",
            len(body),
            preview,
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid Tribute signature")
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid JSON") from exc
    if not isinstance(data, dict):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid payload")

    log.info(
        "tribute webhook event name=%s product=%s tg=%s",
        data.get("name"),
        (data.get("payload") or {}).get("product_id")
        if isinstance(data.get("payload"), dict)
        else None,
        (data.get("payload") or {}).get("telegram_user_id")
        if isinstance(data.get("payload"), dict)
        else None,
    )

    # Тестовые события без начисления
    name = str(data.get("name") or "")
    if name in ("test", "ping", "webhook_test") or data.get("test") is True:
        return {"ok": True, "action": "test"}

    result = tribute.process_tribute_event(data, db)
    log.info("tribute webhook result=%s", result)
    return result


@router.post("/api/billing/telegram/webhook")
async def telegram_bot_webhook(request: Request):
    """Webhook бота: /start buy10 → ссылка Tribute."""
    if not (settings.telegram_bot_token or "").strip():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "TELEGRAM_BOT_TOKEN не задан",
        )
    try:
        update = await request.json()
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid JSON") from None
    if not isinstance(update, dict):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid update")
    try:
        if update.get("callback_query"):
            telegram_bot.handle_callback(update)
        else:
            telegram_bot.handle_update(update)
    except Exception:
        log.exception("telegram bot update failed")
    return {"ok": True}
