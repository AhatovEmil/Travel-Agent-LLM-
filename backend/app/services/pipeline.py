"""Оркестрация travel-конвейера: Brief → Itinerary → Budget → Checklist."""

import logging
import time

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Artifact, Trip
from .engine import LLMGenerationError, get_engine

logger = logging.getLogger(__name__)

PHASES = ["brief", "itinerary", "budget", "checklist"]

PHASE_TITLES = {
    "brief": "Brief — ТЗ поездки",
    "itinerary": "Itinerary — план по дням",
    "budget": "Budget — бюджет",
    "checklist": "Checklist — чеклист",
}


def _save_artifact(db: Session, trip: Trip, phase: str, content: str) -> None:
    db.add(
        Artifact(
            trip_id=trip.id,
            phase=phase,
            title=PHASE_TITLES[phase],
            content=content,
        )
    )
    db.commit()


def run_pipeline(trip_id: int) -> None:
    db = SessionLocal()
    try:
        trip = db.get(Trip, trip_id)
        if trip is None:
            return

        for artifact in list(trip.artifacts):
            db.delete(artifact)
        trip.status = "running"
        trip.error = ""
        db.commit()

        engine = get_engine()
        generators = {
            "brief": engine.generate_brief,
            "itinerary": engine.generate_itinerary,
            "budget": engine.generate_budget,
            "checklist": engine.generate_checklist,
        }

        for phase in PHASES:
            trip.current_phase = phase
            db.commit()
            content = generators[phase](trip.name, trip.brief)
            _save_artifact(db, trip, phase, content)
            time.sleep(0.8)

        trip.status = "completed"
        trip.current_phase = "checklist"
        db.commit()
    except LLMGenerationError as exc:
        logger.error("Travel LLM failed for trip %s: %s", trip_id, exc)
        db.rollback()
        trip = db.get(Trip, trip_id)
        if trip is not None:
            trip.status = "failed"
            trip.error = str(exc)
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline failed for trip %s", trip_id)
        db.rollback()
        trip = db.get(Trip, trip_id)
        if trip is not None:
            trip.status = "failed"
            trip.error = f"{type(exc).__name__}: {exc}"
            db.commit()
    finally:
        db.close()
