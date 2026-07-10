"""Оркестрация travel-конвейера: полный прогон, одна фаза, чат по плану."""

import logging
import time

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Artifact, ArtifactVersion, Trip, Vote
from .engine import LLMGenerationError, get_engine

logger = logging.getLogger(__name__)

PHASES = ["brief", "itinerary", "budget", "checklist"]

PHASE_TITLES = {
    "brief": "Brief — ТЗ поездки",
    "itinerary": "Itinerary — план по дням",
    "budget": "Budget — бюджет",
    "checklist": "Checklist — чеклист",
}

MAX_ITINERARY_VERSIONS = 20


def _trim_versions(db: Session, trip_id: int) -> None:
    versions = (
        db.query(ArtifactVersion)
        .filter(ArtifactVersion.trip_id == trip_id, ArtifactVersion.phase == "itinerary")
        .order_by(ArtifactVersion.id.desc())
        .all()
    )
    for old in versions[MAX_ITINERARY_VERSIONS:]:
        db.delete(old)


def _archive_itinerary(
    db: Session,
    trip: Trip,
    source: str,
    source_meta: str = "",
) -> None:
    existing = next((a for a in trip.artifacts if a.phase == "itinerary"), None)
    if not existing or not (existing.content or "").strip():
        return
    db.add(
        ArtifactVersion(
            trip_id=trip.id,
            phase="itinerary",
            content=existing.content,
            source=source,
            source_meta=(source_meta or "")[:2000],
        )
    )
    db.flush()
    _trim_versions(db, trip.id)


def _save_artifact(
    db: Session,
    trip: Trip,
    phase: str,
    content: str,
    *,
    source: str = "pipeline",
    source_meta: str = "",
) -> None:
    if phase == "itinerary":
        _archive_itinerary(db, trip, source=source, source_meta=source_meta)
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

        # Keep previous itinerary in history before full regenerate
        _archive_itinerary(db, trip, source="pipeline", source_meta="полная перегенерация")
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
            # First itinerary of a fresh run has nothing to archive (already cleared)
            _save_artifact(db, trip, phase, content, source="pipeline")
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
        _save_artifact(db, trip, phase, content, source="phase_rerun")

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
        _save_artifact(
            db,
            trip,
            "itinerary",
            revised,
            source="chat_revise",
            source_meta=message,
        )

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


def run_live_adjust(trip_id: int, reason: str, message: str = "") -> None:
    from datetime import date as date_cls

    from .parse import parse_itinerary_days, replace_day_in_itinerary

    db = SessionLocal()
    try:
        trip = db.get(Trip, trip_id)
        if trip is None:
            return
        arts = _artifacts_map(trip)
        current = arts.get("itinerary")
        if not current:
            trip.status = "failed"
            trip.error = "Нет плана (itinerary)"
            db.commit()
            return

        days = parse_itinerary_days(current, start_date=trip.start_date)
        today = date_cls.today().isoformat()
        day_index = next((i for i, d in enumerate(days) if d.get("date") == today), 0)
        if day_index >= len(days):
            day_index = 0
        day = days[day_index]
        day_md = f"## {day['title']}\n\n{day['content']}"

        trip.status = "running"
        trip.current_phase = "itinerary"
        trip.error = ""
        db.commit()

        engine = get_engine()
        new_day = engine.adjust_day(trip.name, trip.brief, day_md, reason, message)
        if engine.itinerary_needs_structure(new_day):
            new_day = engine.ensure_structured_itinerary(new_day)
        revised = replace_day_in_itinerary(current, day_index, new_day)
        revised = engine.ensure_structured_itinerary(revised)
        _save_artifact(
            db,
            trip,
            "itinerary",
            revised,
            source="live_adjust",
            source_meta=reason + (f": {message}" if message else ""),
        )
        trip.status = "completed"
        db.commit()
    except LLMGenerationError as exc:
        logger.error("Live adjust failed for trip %s: %s", trip_id, exc)
        db.rollback()
        trip = db.get(Trip, trip_id)
        if trip is not None:
            trip.status = "failed"
            trip.error = str(exc)
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Live adjust failed for trip %s", trip_id)
        db.rollback()
        trip = db.get(Trip, trip_id)
        if trip is not None:
            trip.status = "failed"
            trip.error = f"{type(exc).__name__}: {exc}"
            db.commit()
    finally:
        db.close()


def run_rebuild_from_votes(trip_id: int) -> None:
    from sqlalchemy import select

    db = SessionLocal()
    try:
        trip = db.get(Trip, trip_id)
        if trip is None:
            return
        arts = _artifacts_map(trip)
        current = arts.get("itinerary")
        if not current:
            trip.status = "failed"
            trip.error = "Нет плана (itinerary)"
            db.commit()
            return

        votes = list(db.scalars(select(Vote).where(Vote.trip_id == trip_id)).all())
        if not votes:
            trip.status = "failed"
            trip.error = "Нет голосов для пересборки"
            db.commit()
            return

        lines = []
        for v in votes:
            lines.append(f"день {v.day_index}, слот {v.slot_key}: {v.voter} → {v.value}")
        summary = "\n".join(lines)

        trip.status = "running"
        trip.current_phase = "itinerary"
        trip.error = ""
        db.commit()

        engine = get_engine()
        engine.load_context_from_artifacts(arts)
        revised = engine.rebuild_from_votes(trip.name, trip.brief, current, summary)
        _save_artifact(
            db,
            trip,
            "itinerary",
            revised,
            source="rebuild_votes",
            source_meta=f"{len(votes)} голосов",
        )
        trip.status = "completed"
        db.commit()
    except LLMGenerationError as exc:
        logger.error("Rebuild votes failed for trip %s: %s", trip_id, exc)
        db.rollback()
        trip = db.get(Trip, trip_id)
        if trip is not None:
            trip.status = "failed"
            trip.error = str(exc)
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Rebuild votes failed for trip %s", trip_id)
        db.rollback()
        trip = db.get(Trip, trip_id)
        if trip is not None:
            trip.status = "failed"
            trip.error = f"{type(exc).__name__}: {exc}"
            db.commit()
    finally:
        db.close()


def rollback_itinerary(db: Session, trip: Trip, version_id: int) -> Trip:
    version = db.get(ArtifactVersion, version_id)
    if version is None or version.trip_id != trip.id or version.phase != "itinerary":
        raise ValueError("Версия не найдена")
    if trip.status == "running":
        raise ValueError("Дождитесь окончания генерации")
    _save_artifact(
        db,
        trip,
        "itinerary",
        version.content,
        source="rollback",
        source_meta=f"к версии #{version.id}",
    )
    db.refresh(trip)
    return trip
