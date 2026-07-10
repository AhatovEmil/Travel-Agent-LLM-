"""Восстановление поездок, зависших в status=running."""

from __future__ import annotations

import logging

from sqlalchemy import update

from ..database import SessionLocal
from ..models import Trip

logger = logging.getLogger(__name__)

STUCK_MESSAGE = "Прервано перезапуском сервера. Запустите снова."


def fail_stuck_running_trips() -> int:
    db = SessionLocal()
    try:
        result = db.execute(
            update(Trip)
            .where(Trip.status == "running")
            .values(status="failed", error=STUCK_MESSAGE)
        )
        db.commit()
        count = result.rowcount or 0
        if count:
            logger.warning("Marked %s stuck running trip(s) as failed", count)
        return count
    finally:
        db.close()


def recover_trip(trip: Trip) -> Trip:
    if trip.status == "running":
        trip.status = "failed"
        trip.error = STUCK_MESSAGE
    return trip
