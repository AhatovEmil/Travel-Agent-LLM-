"""Простой in-memory лимит LLM-запросов на пользователя."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, status

from ..config import settings

_hits: dict[int, deque[float]] = defaultdict(deque)


def check_llm_rate_limit(user_id: int) -> None:
    limit = max(1, int(settings.llm_rate_limit_per_hour))
    now = time.time()
    window = 3600.0
    q = _hits[user_id]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Слишком много запросов к ИИ ({limit}/час). Подождите и попробуйте снова.",
        )
    q.append(now)


def reset_rate_limits() -> None:
    """Для тестов."""
    _hits.clear()
