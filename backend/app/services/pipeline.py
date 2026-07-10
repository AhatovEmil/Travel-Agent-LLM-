"""Оркестрация travel-конвейера: полный прогон, одна фаза, чат по плану."""

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
    existing = [a for a in trip.artifacts if a.phase == phase]
    for artifact in existing:
        db.delete(artifact)
    db.flush()
    db.add(
        Artifact(
            trip_id=trip.id,
            phase=phase,
            title=PHASE_TITLES[phase],
            content=content,
        )
    )
    db.commit()


def _artifacts_map(trip: Trip) -> dict[str, str]:
    return {a.phase: a.content for a in trip.artifacts}


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
        for phase in PHASES:
            trip.current_phase = phase
            db.commit()
            content = engine.regenerate_phase(phase, trip.name, trip.brief)
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


def run_single_phase(trip_id: int, phase: str) -> None:
    db = SessionLocal()
    try:
        trip = db.get(Trip, trip_id)
        if trip is None:
            return
        if phase not in PHASES:
            trip.status = "failed"
            trip.error = f"Неизвестная фаза: {phase}"
            db.commit()
            return

        trip.status = "running"
        trip.current_phase = phase
        trip.error = ""
        db.commit()

        engine = get_engine()
        engine.load_context_from_artifacts(_artifacts_map(trip))
        content = engine.regenerate_phase(phase, trip.name, trip.brief)
        # если обновили brief/itinerary — следующие фазы в контексте уже невалидны,
        # но пользователь явно просил только одну фазу
        _save_artifact(db, trip, phase, content)

        trip.status = "completed"
        db.commit()
    except LLMGenerationError as exc:
        logger.error("Phase %s failed for trip %s: %s", phase, trip_id, exc)
        db.rollback()
        trip = db.get(Trip, trip_id)
        if trip is not None:
            trip.status = "failed"
            trip.error = str(exc)
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Phase rerun failed for trip %s", trip_id)
        db.rollback()
        trip = db.get(Trip, trip_id)
        if trip is not None:
            trip.status = "failed"
            trip.error = f"{type(exc).__name__}: {exc}"
            db.commit()
    finally:
        db.close()


def run_chat_revise(trip_id: int, message: str) -> None:
    db = SessionLocal()
    try:
        trip = db.get(Trip, trip_id)
        if trip is None:
            return

        arts = _artifacts_map(trip)
        current = arts.get("itinerary")
        if not current:
            trip.status = "failed"
            trip.error = "Нет плана (itinerary) — сначала сгенерируйте поездку"
            db.commit()
            return

        trip.status = "running"
        trip.current_phase = "itinerary"
        trip.error = ""
        db.commit()

        engine = get_engine()
        engine.load_context_from_artifacts(arts)
        revised = engine.revise_itinerary(trip.name, trip.brief, current, message)
        _save_artifact(db, trip, "itinerary", revised)

        trip.status = "completed"
        db.commit()
    except LLMGenerationError as exc:
        logger.error("Chat revise failed for trip %s: %s", trip_id, exc)
        db.rollback()
        trip = db.get(Trip, trip_id)
        if trip is not None:
            trip.status = "failed"
            trip.error = str(exc)
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chat revise failed for trip %s", trip_id)
        db.rollback()
        trip = db.get(Trip, trip_id)
        if trip is not None:
            trip.status = "failed"
            trip.error = f"{type(exc).__name__}: {exc}"
            db.commit()
    finally:
        db.close()
