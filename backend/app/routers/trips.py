from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_current_user, get_db
from ..models import Trip, User
from ..schemas import ArtifactOut, TripCreate, TripOut
from ..services.pipeline import run_pipeline

router = APIRouter(prefix="/api/trips", tags=["trips"])


def _get_owned_trip(trip_id: int, user: User, db: Session) -> Trip:
    trip = db.get(Trip, trip_id)
    if trip is None or trip.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")
    return trip


@router.post("", response_model=TripOut, status_code=status.HTTP_201_CREATED)
def create_trip(
    payload: TripCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = Trip(owner_id=current_user.id, name=payload.name, brief=payload.brief)
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
    if trip.status == "running":
        raise HTTPException(status.HTTP_409_CONFLICT, "Pipeline is already running")
    if not settings.llm_api_key.strip():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "LLM_API_KEY не задан. Добавьте ключ DeepSeek в backend/.env и перезапустите сервер.",
        )
    trip.status = "running"
    trip.current_phase = "brief"
    trip.error = ""
    db.commit()
    db.refresh(trip)
    background_tasks.add_task(run_pipeline, trip.id)
    return trip


@router.get("/{trip_id}/artifacts", response_model=list[ArtifactOut])
def list_artifacts(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_owned_trip(trip_id, current_user, db)
    return trip.artifacts
