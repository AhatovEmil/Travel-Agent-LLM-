import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_current_user, get_db
from ..models import ArtifactVersion, ChatMessage, JournalEntry, Trip, User
from ..schemas import (
    AskResponse,
    ArtifactOut,
    ArtifactVersionOut,
    ChatMessageOut,
    ChatRequest,
    EveningCheckin,
    JournalCreate,
    JournalOut,
    JournalUpdate,
    LiveAdjustRequest,
    PhaseRerunRequest,
    QuestRequest,
    ShareResponse,
    TripCreate,
    TripOut,
    VoteOut,
)
from ..services.engine import LLMGenerationError, get_engine
from ..services.export import build_trip_markdown, build_trip_pdf
from ..services.extras import build_live_status, build_trip_extras
from ..services.parse import extract_destination
from ..services.photos import destination_photos
from ..services.pipeline import (
    PHASES,
    rollback_itinerary,
    run_chat_revise,
    run_live_adjust,
    run_pipeline,
    run_rebuild_from_votes,
    run_single_phase,
)
from ..services.street_smart import (
    build_arrival,
    build_quest_fallback,
    build_survival,
    build_taste,
    build_traps,
)
from ..services.trip_os import (
    MOODS,
    build_morning_briefing,
    parse_done_slots,
    serialize_done_slots,
    trip_day_window,
)
from ..services.parse import parse_itinerary_days


def _journal_out(entry: JournalEntry) -> JournalOut:
    return JournalOut(
        id=entry.id,
        trip_id=entry.trip_id,
        day_index=entry.day_index,
        kind=entry.kind,
        mood=entry.mood or "",
        content=entry.content or "",
        done_slots=parse_done_slots(entry.done_slots),
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )

router = APIRouter(prefix="/api/trips", tags=["trips"])


def _get_owned_trip(trip_id: int, user: User, db: Session) -> Trip:
    trip = db.get(Trip, trip_id)
    if trip is None or trip.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")
    return trip


def _require_llm_key() -> None:
    if not settings.llm_api_key.strip():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "LLM_API_KEY не задан. Добавьте ключ DeepSeek в backend/.env и перезапустите сервер.",
        )


def _require_llm_budget(user: User) -> None:
    from ..services.rate_limit import check_llm_rate_limit

    check_llm_rate_limit(user.id)


def _require_idle(trip: Trip) -> None:
    if trip.status == "running":
        raise HTTPException(status.HTTP_409_CONFLICT, "Pipeline is already running")


def _disposition(trip: Trip, ext: str) -> str:
    from urllib.parse import quote

    ascii_name = "".join(
        c if c.isascii() and (c.isalnum() or c in "-_") else "_" for c in trip.name
    )
    ascii_name = ascii_name.strip("_")[:60] or f"trip-{trip.id}"
    filename = f"{ascii_name}.{ext}"
    utf8_name = quote(f"{trip.name.strip() or ascii_name}.{ext}")
    return f"attachment; filename=\"{filename}\"; filename*=UTF-8''{utf8_name}"


@router.post("", response_model=TripOut, status_code=status.HTTP_201_CREATED)
def create_trip(
    payload: TripCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = Trip(
        owner_id=current_user.id,
        name=payload.name,
        brief=payload.brief,
        start_date=payload.start_date,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


@router.get("", response_model=list[TripOut])
def list_trips(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.scalars(
        select(Trip).where(Trip.owner_id == current_user.id).order_by(Trip.id.desc())
    ).all()


@router.get("/{trip_id}", response_model=TripOut)
def get_trip(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_trip(trip_id, current_user, db)


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    db.delete(trip)
    db.commit()


@router.post("/{trip_id}/run", response_model=TripOut, status_code=status.HTTP_202_ACCEPTED)
def run_trip(
    trip_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    _require_idle(trip)
    _require_llm_key()
    _require_llm_budget(current_user)
    trip.status = "running"
    trip.current_phase = "brief"
    trip.error = ""
    db.commit()
    db.refresh(trip)
    background_tasks.add_task(run_pipeline, trip.id)
    return trip


@router.post(
    "/{trip_id}/phases/rerun",
    response_model=TripOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def rerun_phase(
    trip_id: int,
    payload: PhaseRerunRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    _require_idle(trip)
    _require_llm_key()
    _require_llm_budget(current_user)
    if payload.phase not in PHASES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown phase")
    trip.status = "running"
    trip.current_phase = payload.phase
    trip.error = ""
    db.commit()
    db.refresh(trip)
    background_tasks.add_task(run_single_phase, trip.id, payload.phase)
    return trip


@router.post(
    "/{trip_id}/chat",
    response_model=TripOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def chat_revise(
    trip_id: int,
    payload: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    _require_idle(trip)
    _require_llm_key()
    _require_llm_budget(current_user)
    has_itinerary = any(a.phase == "itinerary" for a in trip.artifacts)
    if not has_itinerary:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Нет плана (itinerary) — сначала сгенерируйте поездку",
        )
    trip.status = "running"
    trip.current_phase = "itinerary"
    trip.error = ""
    db.commit()
    db.refresh(trip)
    background_tasks.add_task(run_chat_revise, trip.id, payload.message.strip())
    return trip


@router.get("/{trip_id}/messages", response_model=list[ChatMessageOut])
def list_messages(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    return trip.messages


@router.post("/{trip_id}/ask", response_model=AskResponse)
def ask_question(
    trip_id: int,
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    _require_llm_key()
    _require_llm_budget(current_user)
    question = payload.message.strip()
    history = [{"role": m.role, "content": m.content} for m in trip.messages]
    artifacts = {a.phase: a.content for a in trip.artifacts}

    db.add(ChatMessage(trip_id=trip.id, role="user", content=question))
    db.commit()

    try:
        engine = get_engine()
        reply = engine.answer_question(trip.name, trip.brief, artifacts, history, question)
    except LLMGenerationError as exc:
        db.add(
            ChatMessage(
                trip_id=trip.id,
                role="assistant",
                content=f"Не удалось ответить: {exc}",
            )
        )
        db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    db.add(ChatMessage(trip_id=trip.id, role="assistant", content=reply))
    db.commit()
    db.refresh(trip)
    return AskResponse(reply=reply, messages=list(trip.messages))


@router.get("/{trip_id}/artifacts", response_model=list[ArtifactOut])
def list_artifacts(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    return trip.artifacts


@router.get("/{trip_id}/itinerary/versions", response_model=list[ArtifactVersionOut])
def list_itinerary_versions(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    rows = db.scalars(
        select(ArtifactVersion)
        .where(ArtifactVersion.trip_id == trip.id, ArtifactVersion.phase == "itinerary")
        .order_by(ArtifactVersion.id.desc())
    ).all()
    return list(rows)


@router.post(
    "/{trip_id}/itinerary/versions/{version_id}/rollback",
    response_model=TripOut,
)
def rollback_itinerary_version(
    trip_id: int,
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    try:
        return rollback_itinerary(db, trip, version_id)
    except ValueError as exc:
        code = status.HTTP_409_CONFLICT if "генерации" in str(exc) else status.HTTP_404_NOT_FOUND
        raise HTTPException(code, str(exc)) from exc


@router.get("/{trip_id}/extras")
def trip_extras(
    trip_id: int,
    fast: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    return build_trip_extras(trip, geocode_limit=0 if fast else 10)


@router.get("/{trip_id}/photos")
def trip_photos(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Реальные фото направления (Wikimedia Commons), с кэшем."""
    trip = _get_owned_trip(trip_id, current_user, db)
    destination = extract_destination(trip.brief or "", trip.name or "")
    photos = destination_photos(destination, limit=8)
    return {"destination": destination, "photos": photos}


@router.get("/{trip_id}/live")
def trip_live(
    trip_id: int,
    lat: float | None = Query(default=None),
    lon: float | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    return build_live_status(trip, lat, lon)


@router.post(
    "/{trip_id}/live/adjust",
    response_model=TripOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def trip_live_adjust(
    trip_id: int,
    payload: LiveAdjustRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    _require_idle(trip)
    _require_llm_key()
    _require_llm_budget(current_user)
    if not any(a.phase == "itinerary" for a in trip.artifacts):
        raise HTTPException(status.HTTP_409_CONFLICT, "Нет плана (itinerary)")
    trip.status = "running"
    trip.current_phase = "itinerary"
    trip.error = ""
    db.commit()
    db.refresh(trip)
    background_tasks.add_task(
        run_live_adjust, trip.id, payload.reason, payload.message.strip()
    )
    return trip


@router.post("/{trip_id}/recover", response_model=TripOut)
def recover_stuck_trip(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from ..services.recover import recover_trip

    trip = _get_owned_trip(trip_id, current_user, db)
    if trip.status != "running":
        raise HTTPException(status.HTTP_409_CONFLICT, "Trip is not stuck in running")
    recover_trip(trip)
    db.commit()
    db.refresh(trip)
    return trip


@router.post("/{trip_id}/share", response_model=ShareResponse)
def enable_share(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    trip.share_token = secrets.token_urlsafe(16)
    db.commit()
    db.refresh(trip)
    return ShareResponse(
        share_token=trip.share_token,
        share_path=f"#/share/{trip.share_token}",
    )


@router.delete("/{trip_id}/share", status_code=status.HTTP_204_NO_CONTENT)
def revoke_share(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Отзывает публичную ссылку — старый токен перестаёт работать."""
    trip = _get_owned_trip(trip_id, current_user, db)
    trip.share_token = None
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{trip_id}/votes", response_model=list[VoteOut])
def list_votes(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    return trip.votes


@router.post(
    "/{trip_id}/rebuild-from-votes",
    response_model=TripOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def rebuild_from_votes(
    trip_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    _require_idle(trip)
    _require_llm_key()
    _require_llm_budget(current_user)
    if not trip.votes:
        raise HTTPException(status.HTTP_409_CONFLICT, "Нет голосов")
    trip.status = "running"
    trip.current_phase = "itinerary"
    trip.error = ""
    db.commit()
    db.refresh(trip)
    background_tasks.add_task(run_rebuild_from_votes, trip.id)
    return trip


@router.get("/{trip_id}/export")
def export_trip(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    if trip.status != "completed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Trip is not completed yet")
    if not trip.artifacts:
        raise HTTPException(status.HTTP_409_CONFLICT, "No artifacts to export")
    content = build_trip_markdown(trip)
    return Response(
        content=content.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": _disposition(trip, "md")},
    )


@router.get("/{trip_id}/export.pdf")
def export_trip_pdf(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    if trip.status != "completed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Trip is not completed yet")
    if not trip.artifacts:
        raise HTTPException(status.HTTP_409_CONFLICT, "No artifacts to export")
    try:
        content = build_trip_pdf(trip)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": _disposition(trip, "pdf")},
    )


# ——— Street Smart ———


@router.get("/{trip_id}/street-smart/survival")
def street_survival(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    return build_survival(trip)


@router.post("/{trip_id}/street-smart/survival/enrich")
def street_survival_enrich(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    _require_llm_key()
    _require_llm_budget(current_user)
    base = build_survival(trip)
    try:
        engine = get_engine()
        phrases = engine.enrich_survival_phrases(base["destination"], base["region_label"])
        if phrases:
            base["phrases"] = phrases
            base["source"] = "llm"
    except LLMGenerationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return base


@router.get("/{trip_id}/street-smart/traps")
def street_traps(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    return build_traps(trip)


@router.post("/{trip_id}/street-smart/traps/enrich")
def street_traps_enrich(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    _require_llm_key()
    _require_llm_budget(current_user)
    base = build_traps(trip)
    try:
        engine = get_engine()
        traps = engine.enrich_traps(base["destination"], build_survival(trip)["region_label"])
        if traps:
            base["traps"] = traps
            base["source"] = "llm"
    except LLMGenerationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return base


@router.get("/{trip_id}/street-smart/taste")
def street_taste(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    return build_taste(trip)


@router.get("/{trip_id}/street-smart/arrival")
def street_arrival(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    return build_arrival(trip)


@router.post("/{trip_id}/street-smart/quest")
def street_quest(
    trip_id: int,
    payload: QuestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    fallback = build_quest_fallback(trip, payload.day_index)
    if not settings.llm_api_key.strip():
        return fallback
    try:
        _require_llm_budget(current_user)
        arts = {a.phase: a.content for a in trip.artifacts}
        days = parse_itinerary_days(arts.get("itinerary", ""), start_date=trip.start_date)
        day = days[payload.day_index] if 0 <= payload.day_index < len(days) else None
        places = [s["place"] for s in (day or {}).get("slots") or []]
        engine = get_engine()
        missions = engine.generate_day_quest(
            fallback["destination"],
            fallback["day_title"],
            places,
        )
        if len(missions) >= 3:
            fallback["missions"] = [
                {"id": i, "text": m} for i, m in enumerate(missions[:3])
            ]
            fallback["source"] = "llm"
    except LLMGenerationError:
        pass
    except HTTPException:
        # rate limit — return rules
        pass
    return fallback


# ——— Trip OS: modes, briefing, journal ———


@router.get("/{trip_id}/os/window")
def trip_os_window(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    window = trip_day_window(trip)
    window.pop("days", None)
    return window


@router.get("/{trip_id}/os/briefing")
def trip_os_briefing(
    trip_id: int,
    day_index: int | None = Query(default=None, ge=0, le=60),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    return build_morning_briefing(trip, day_index)


@router.get("/{trip_id}/journal", response_model=list[JournalOut])
def list_journal(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    rows = db.scalars(
        select(JournalEntry)
        .where(JournalEntry.trip_id == trip.id)
        .order_by(JournalEntry.day_index, JournalEntry.id)
    ).all()
    return [_journal_out(r) for r in rows]


@router.post("/{trip_id}/journal", response_model=JournalOut, status_code=status.HTTP_201_CREATED)
def create_journal(
    trip_id: int,
    payload: JournalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    if payload.kind == "evening":
        existing = db.scalars(
            select(JournalEntry).where(
                JournalEntry.trip_id == trip.id,
                JournalEntry.day_index == payload.day_index,
                JournalEntry.kind == "evening",
            )
        ).first()
        if existing:
            existing.mood = payload.mood if payload.mood in MOODS else (payload.mood or existing.mood)
            existing.content = payload.content
            existing.done_slots = serialize_done_slots(payload.done_slots)
            db.commit()
            db.refresh(existing)
            return _journal_out(existing)

    entry = JournalEntry(
        trip_id=trip.id,
        day_index=payload.day_index,
        kind=payload.kind,
        mood=payload.mood if payload.mood in MOODS else (payload.mood or ""),
        content=payload.content,
        done_slots=serialize_done_slots(payload.done_slots),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _journal_out(entry)


@router.patch("/{trip_id}/journal/{entry_id}", response_model=JournalOut)
def update_journal(
    trip_id: int,
    entry_id: int,
    payload: JournalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    entry = db.get(JournalEntry, entry_id)
    if entry is None or entry.trip_id != trip.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Journal entry not found")
    if payload.mood is not None:
        entry.mood = payload.mood
    if payload.content is not None:
        entry.content = payload.content
    if payload.done_slots is not None:
        entry.done_slots = serialize_done_slots(payload.done_slots)
    db.commit()
    db.refresh(entry)
    return _journal_out(entry)


@router.delete("/{trip_id}/journal/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_journal(
    trip_id: int,
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    entry = db.get(JournalEntry, entry_id)
    if entry is None or entry.trip_id != trip.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Journal entry not found")
    db.delete(entry)
    db.commit()
    return None


@router.post("/{trip_id}/os/evening", response_model=JournalOut)
def evening_checkin(
    trip_id: int,
    payload: EveningCheckin,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    mood = payload.mood if payload.mood in MOODS else "ok"
    existing = db.scalars(
        select(JournalEntry).where(
            JournalEntry.trip_id == trip.id,
            JournalEntry.day_index == payload.day_index,
            JournalEntry.kind == "evening",
        )
    ).first()
    if existing:
        existing.mood = mood
        existing.content = payload.content
        existing.done_slots = serialize_done_slots(payload.done_slots)
        db.commit()
        db.refresh(existing)
        return _journal_out(existing)

    entry = JournalEntry(
        trip_id=trip.id,
        day_index=payload.day_index,
        kind="evening",
        mood=mood,
        content=payload.content,
        done_slots=serialize_done_slots(payload.done_slots),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _journal_out(entry)
