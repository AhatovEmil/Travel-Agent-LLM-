"""Проверка Telegram Login Widget / WebApp initData."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import HTTPException, status

from ..config import settings


def _bot_token() -> str:
    token = (settings.telegram_bot_token or "").strip()
    if not token:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "TELEGRAM_BOT_TOKEN не задан.",
        )
    return token


def _check_hash(data_check: str, received_hash: str, secret: bytes) -> bool:
    calc = hmac.new(secret, data_check.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(calc, received_hash)


def parse_webapp_init_data(init_data: str) -> dict:
    """Валидация Telegram.WebApp.initData → dict с id пользователя."""
    token = _bot_token()
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received = pairs.pop("hash", None)
    if not received:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "init_data без hash")
    check_list = [f"{k}={v}" for k, v in sorted(pairs.items())]
    data_check = "\n".join(check_list)
    secret = hmac.new(b"WebAppData", token.encode("utf-8"), hashlib.sha256).digest()
    if not _check_hash(data_check, received, secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверная подпись Telegram")
    auth_date = int(pairs.get("auth_date") or 0)
    if auth_date and time.time() - auth_date > 86400:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Данные Telegram устарели")
    user_raw = pairs.get("user")
    if not user_raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Нет user в init_data")
    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Битый user JSON") from exc
    tg_id = user.get("id")
    if tg_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Нет telegram id")
    return {
        "telegram_id": str(tg_id),
        "username": user.get("username") or "",
        "first_name": user.get("first_name") or "",
    }


def parse_login_widget(data: dict) -> dict:
    """Валидация данных Telegram Login Widget."""
    token = _bot_token()
    payload = {k: str(v) for k, v in data.items() if v is not None and k != "hash"}
    received = str(data.get("hash") or "")
    if not received or "id" not in payload:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Неполные данные Login Widget")
    check_list = [f"{k}={payload[k]}" for k in sorted(payload.keys())]
    data_check = "\n".join(check_list)
    secret = hashlib.sha256(token.encode("utf-8")).digest()
    if not _check_hash(data_check, received, secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверная подпись Telegram")
    auth_date = int(payload.get("auth_date") or 0)
    if auth_date and time.time() - auth_date > 86400:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Данные Telegram устарели")
    return {
        "telegram_id": str(payload["id"]),
        "username": payload.get("username") or "",
        "first_name": payload.get("first_name") or "",
    }
