import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_current_user, get_db
from ..models import ArtifactVersion, ChatMessage, Trip, User
from ..schemas import (
    AskResponse,
    ArtifactOut,
    ArtifactVersionOut,
    ChatMessageOut,
    ChatRequest,
    LiveAdjustRequest,
    PhaseRerunRequest,
    ShareResponse,
    TripCreate,
    TripOut,
    VoteOut,
)
from ..services.engine import LLMGenerationError, get_engine
from ..services.export import build_trip_markdown, build_trip_pdf
from ..services.extras import build_live_status, build_trip_extras
from ..services.pipeline import (
    PHASES,
    rollback_itinerary,
    run_chat_revise,
    run_live_adjust,
    run_pipeline,
    run_rebuild_from_votes,
    run_single_phase,
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    return build_trip_extras(trip)


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
