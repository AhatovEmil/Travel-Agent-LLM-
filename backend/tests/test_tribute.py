"""Tribute webhook + Telegram link + bot deep-links."""

import hashlib
import hmac
import json

from sqlalchemy import select


def _sign(body: bytes, api_key: str) -> str:
    return hmac.new(api_key.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_tribute_webhook_credits_linked_user(client, monkeypatch, auth_headers):
    monkeypatch.setattr("app.config.settings.tribute_api_key", "tribute-secret")
    monkeypatch.setattr("app.services.tribute.settings.tribute_api_key", "tribute-secret")
    monkeypatch.setattr("app.config.settings.tribute_product_10", "111")
    monkeypatch.setattr("app.services.tribute.settings.tribute_product_10", "111")

    from app.database import SessionLocal
    from app.models import User

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == "traveler@test.com"))
        assert user is not None
        user.telegram_id = "999001"
        db.commit()
    finally:
        db.close()

    payload = {
        "name": "new_digital_product",
        "sent_at": "2026-07-11T12:00:00.000Z",
        "payload": {
            "product_id": 111,
            "telegram_user_id": 999001,
            "amount": 29900,
            "currency": "rub",
        },
    }
    raw = json.dumps(payload).encode("utf-8")
    sig = _sign(raw, "tribute-secret")
    r = client.post(
        "/api/billing/tribute/webhook",
        content=raw,
        headers={"Content-Type": "application/json", "trbt-signature": sig},
    )
    assert r.status_code == 200, r.text
    assert r.json()["action"] == "credited"

    me = client.get("/api/auth/me", headers=auth_headers).json()
    assert me["credit_balance"] == 10
    assert me["telegram_linked"] is True

    # idempotent
    r2 = client.post(
        "/api/billing/tribute/webhook",
        content=raw,
        headers={"Content-Type": "application/json", "trbt-signature": sig},
    )
    assert r2.status_code == 200
    assert r2.json()["action"] == "duplicate"
    me2 = client.get("/api/auth/me", headers=auth_headers).json()
    assert me2["credit_balance"] == 10


def test_tribute_webhook_bad_signature(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.tribute_api_key", "tribute-secret")
    monkeypatch.setattr("app.services.tribute.settings.tribute_api_key", "tribute-secret")
    raw = b'{"name":"new_digital_product","payload":{}}'
    r = client.post(
        "/api/billing/tribute/webhook",
        content=raw,
        headers={"Content-Type": "application/json", "trbt-signature": "deadbeef"},
    )
    assert r.status_code == 401


def test_tribute_pending_then_claim_on_link(client, monkeypatch, auth_headers):
    monkeypatch.setattr("app.config.settings.tribute_api_key", "tribute-secret")
    monkeypatch.setattr("app.services.tribute.settings.tribute_api_key", "tribute-secret")
    monkeypatch.setattr("app.config.settings.tribute_product_30", "222")
    monkeypatch.setattr("app.services.tribute.settings.tribute_product_30", "222")
    monkeypatch.setattr("app.config.settings.telegram_bot_token", "123456:ABC-TESTTOKEN")
    monkeypatch.setattr("app.services.telegram_auth.settings.telegram_bot_token", "123456:ABC-TESTTOKEN")

    payload = {
        "name": "new_digital_product",
        "sent_at": "2026-07-11T13:00:00.000Z",
        "payload": {"product_id": "222", "telegram_user_id": "888002"},
    }
    raw = json.dumps(payload).encode("utf-8")
    sig = _sign(raw, "tribute-secret")
    r = client.post(
        "/api/billing/tribute/webhook",
        content=raw,
        headers={"Content-Type": "application/json", "trbt-signature": sig},
    )
    assert r.status_code == 200
    assert r.json()["action"] == "pending"

    # Build valid Login Widget signature
    import time

    auth_date = int(time.time())
    fields = {
        "id": "888002",
        "first_name": "Test",
        "auth_date": str(auth_date),
    }
    check = "\n".join(f"{k}={fields[k]}" for k in sorted(fields.keys()))
    secret = hashlib.sha256(b"123456:ABC-TESTTOKEN").digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    fields["id"] = 888002
    fields["auth_date"] = auth_date

    link = client.post(
        "/api/billing/telegram/link-widget",
        headers=auth_headers,
        json=fields,
    )
    assert link.status_code == 200, link.text
    body = link.json()
    assert body["telegram_linked"] is True
    assert body["credits_claimed"] == 30
    assert body["credit_balance"] == 30


def test_packages_include_buy_url(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.telegram_bot_username", "TravelPayBot")
    monkeypatch.setattr("app.services.billing.settings.telegram_bot_username", "TravelPayBot")
    monkeypatch.setattr("app.config.settings.tribute_link_10", "https://t.me/tribute/app?startapp=x")
    monkeypatch.setattr("app.services.billing.settings.tribute_link_10", "https://t.me/tribute/app?startapp=x")
    # generation_packages reads from settings singleton - patch config.settings used by property
    monkeypatch.setattr("app.config.settings.telegram_bot_username", "TravelPayBot")
    monkeypatch.setattr("app.config.settings.tribute_link_10", "https://t.me/tribute/app?startapp=x")

    r = client.get("/api/billing/packages")
    assert r.status_code == 200
    body = r.json()
    assert body["bot_username"] == "TravelPayBot"
    pack10 = next(p for p in body["packages"] if p["id"] == "pack10")
    assert "TravelPayBot" in pack10["buy_url"]
    assert "buy10" in pack10["buy_url"]


def test_telegram_bot_start_sends_menu(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.telegram_bot_token", "123:token")
    monkeypatch.setattr("app.routers.billing.settings.telegram_bot_token", "123:token")
    monkeypatch.setattr("app.services.telegram_bot.settings.telegram_bot_token", "123:token")
    monkeypatch.setattr(
        "app.config.settings.tribute_link_10", "https://example.com/pay10"
    )
    monkeypatch.setattr(
        "app.services.telegram_bot.settings.tribute_link_10", "https://example.com/pay10"
    )
    monkeypatch.setattr(
        "app.config.settings.tribute_link_30", "https://example.com/pay30"
    )
    monkeypatch.setattr(
        "app.services.telegram_bot.settings.tribute_link_30", "https://example.com/pay30"
    )

    calls = []

    def fake_api(method, payload):
        calls.append((method, payload))
        return {"ok": True}

    monkeypatch.setattr("app.services.telegram_bot.telegram_api", fake_api)

    r = client.post(
        "/api/billing/telegram/webhook",
        json={"message": {"chat": {"id": 7}, "text": "/start"}},
    )
    assert r.status_code == 200
    assert any(m == "sendMessage" for m, _ in calls)
    assert any("https://example.com/pay10" in json.dumps(p) for m, p in calls if m == "sendMessage")
