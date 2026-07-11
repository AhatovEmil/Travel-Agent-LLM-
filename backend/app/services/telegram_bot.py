"""Telegram-бот: /start и /buy → ссылки на оплату Tribute."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from ..config import settings

log = logging.getLogger(__name__)

API = "https://api.telegram.org"


def _token() -> str:
    return (settings.telegram_bot_token or "").strip()


def telegram_api(method: str, payload: dict) -> dict | None:
    token = _token()
    if not token:
        return None
    url = f"{API}/bot{token}/{method}"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        log.warning("telegram api %s failed: %s", method, exc)
        return None


def _packages_with_links() -> list[dict]:
    """Пакеты у которых есть прямая ссылка Tribute."""
    out = []
    for p in settings.generation_packages:
        link = (p.get("tribute_url") or "").strip()
        if link:
            out.append({**p, "tribute_url": link})
    return out


def send_buy_menu(chat_id: int | str, pack_hint: str | None = None) -> None:
    packs = _packages_with_links()
    if not packs:
        telegram_api(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": (
                    "Пакеты генераций пока не настроены.\n"
                    "Администратору нужно указать TRIBUTE_LINK_10/30/100 в .env."
                ),
            },
        )
        return

    hint_map = {
        "buy10": "pack10",
        "buy30": "pack30",
        "buy100": "pack100",
        "10": "pack10",
        "30": "pack30",
        "100": "pack100",
    }
    want = hint_map.get((pack_hint or "").strip().lower())

    if want:
        chosen = next((p for p in packs if p["id"] == want), None)
        if chosen:
            telegram_api(
                "sendMessage",
                {
                    "chat_id": chat_id,
                    "text": (
                        f"Оплата: {chosen['label']} — {chosen['price_rub']} ₽\n\n"
                        "Откройте ссылку Tribute (карта / СБП). "
                        "После оплаты генерации появятся на сайте, "
                        "если Telegram привязан к аккаунту."
                    ),
                    "reply_markup": {
                        "inline_keyboard": [
                            [{"text": f"Оплатить {chosen['label']}", "url": chosen["tribute_url"]}]
                        ]
                    },
                },
            )
            return

    rows = [
        [{"text": f"{p['label']} — {p['price_rub']} ₽", "url": p["tribute_url"]}]
        for p in packs
    ]
    telegram_api(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": (
                "Выберите пакет генераций Travel Agent.\n"
                "Оплата в Tribute (мини-приложение). "
                "Перед оплатой привяжите Telegram в личном кабинете на сайте — "
                "тогда кредиты начислятся автоматически."
            ),
            "reply_markup": {"inline_keyboard": rows},
        },
    )


def handle_update(update: dict) -> None:
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return
    text = (message.get("text") or "").strip()
    if not text:
        return
    lower = text.lower()
    if lower.startswith("/start"):
        parts = text.split(maxsplit=1)
        payload = parts[1].strip() if len(parts) > 1 else ""
        if payload.startswith("buy") or payload in ("10", "30", "100"):
            send_buy_menu(chat_id, payload)
        else:
            telegram_api(
                "sendMessage",
                {
                    "chat_id": chat_id,
                    "text": (
                        "Привет! Я бот оплаты Travel Agent.\n\n"
                        "Команды:\n"
                        "/buy — пакеты генераций (ссылки Tribute)\n"
                        "/buy10 /buy30 /buy100 — конкретный пакет\n\n"
                        "После оплаты привяжите Telegram на сайте "
                        "ai-travel-assistant.ru — генерации появятся в балансе."
                    ),
                    "reply_markup": {
                        "inline_keyboard": [
                            [{"text": "Купить генерации", "callback_data": "buy"}]
                        ]
                    },
                },
            )
            # сразу меню на всякий случай
            send_buy_menu(chat_id)
        return
    if lower.startswith("/buy10"):
        send_buy_menu(chat_id, "buy10")
        return
    if lower.startswith("/buy30"):
        send_buy_menu(chat_id, "buy30")
        return
    if lower.startswith("/buy100"):
        send_buy_menu(chat_id, "buy100")
        return
    if lower.startswith("/buy"):
        send_buy_menu(chat_id)
        return


def handle_callback(update: dict) -> None:
    cq = update.get("callback_query") or {}
    data = cq.get("data") or ""
    msg = cq.get("message") or {}
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    cq_id = cq.get("id")
    if cq_id:
        telegram_api("answerCallbackQuery", {"callback_query_id": cq_id})
    if chat_id is not None and data == "buy":
        send_buy_menu(chat_id)
