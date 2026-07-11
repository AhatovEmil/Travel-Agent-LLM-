"""Простые in-memory лимиты (один worker uvicorn — ок для небольшого VPS)."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from ..config import settings

_llm_hits: dict[int, deque[float]] = defaultdict(deque)
_ip_hits: dict[str, deque[float]] = defaultdict(deque)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _check_window(
    key: str,
    *,
    limit: int,
    window_seconds: float,
    message: str,
) -> None:
    now = time.time()
    q = _ip_hits[key]
    while q and now - q[0] > window_seconds:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, message)
    q.append(now)


def check_llm_rate_limit(user_id: int) -> None:
    limit = max(1, int(settings.llm_rate_limit_per_hour))
    now = time.time()
    window = 3600.0
    q = _llm_hits[user_id]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Слишком много запросов к ИИ ({limit}/час). Подождите и попробуйте снова.",
        )
    q.append(now)


def check_auth_rate_limit(request: Request) -> None:
    limit = max(1, int(settings.auth_rate_limit_per_minute))
    ip = client_ip(request)
    _check_window(
        f"auth:{ip}",
        limit=limit,
        window_seconds=60.0,
        message="Слишком много попыток входа. Подождите минуту.",
    )


def check_share_rate_limit(request: Request) -> None:
    limit = max(1, int(settings.share_rate_limit_per_minute))
    ip = client_ip(request)
    _check_window(
        f"share:{ip}",
        limit=limit,
        window_seconds=60.0,
        message="Слишком много запросов к общей ссылке. Подождите минуту.",
    )


def reset_rate_limits() -> None:
    """Для тестов."""
    _llm_hits.clear()
    _ip_hits.clear()
