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


def ensure_bot_commands() -> None:
    """Меню команд у кнопки «/» и подсказка к Start."""
    telegram_api(
        "setMyCommands",
        {
            "commands": [
                {"command": "start", "description": "Начать — пакеты генераций"},
                {"command": "buy", "description": "Купить генерации"},
                {"command": "buy10", "description": "Пакет 10 генераций"},
                {"command": "buy30", "description": "Пакет 30 генераций"},
                {"command": "buy100", "description": "Пакет 100 генераций"},
            ]
        },
    )


def _packages_with_links() -> list[dict]:
    out = []
    for p in settings.generation_packages:
        link = (p.get("tribute_url") or "").strip()
        if link:
            out.append({**p, "tribute_url": link})
    return out


def _cmd_parts(text: str) -> tuple[str, str]:
    """'/start@Bot buy10' → ('/start', 'buy10')."""
    first, _, rest = text.strip().partition(" ")
    cmd = first.split("@", 1)[0].lower()
    return cmd, rest.strip()


def send_buy_menu(chat_id: int | str, pack_hint: str | None = None, *, greeting: bool = False) -> None:
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
                        "Откройте ссылку Tribute (карта / СБП).\n"
                        "Чтобы кредиты упали на сайт: на ai-travel-assistant.ru "
                        "нажмите счётчик генераций в шапке → «Войти через Telegram»."
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
    intro = (
        "Привет! Я бот оплаты Travel Agent.\n\n"
        if greeting
        else ""
    )
    telegram_api(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": (
                f"{intro}"
                "Выберите пакет генераций. Оплата в Tribute (карта / СБП).\n\n"
                "После оплаты на сайте ai-travel-assistant.ru откройте счётчик "
                "в шапке (например 5/5) и нажмите «Войти через Telegram» — "
                "кредиты начислятся автоматически."
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

    cmd, payload = _cmd_parts(text)

    if cmd == "/start":
        if payload.startswith("buy") or payload in ("10", "30", "100"):
            send_buy_menu(chat_id, payload)
        else:
            send_buy_menu(chat_id, greeting=True)
        return
    if cmd == "/buy10":
        send_buy_menu(chat_id, "buy10")
        return
    if cmd == "/buy30":
        send_buy_menu(chat_id, "buy30")
        return
    if cmd == "/buy100":
        send_buy_menu(chat_id, "buy100")
        return
    if cmd == "/buy":
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
