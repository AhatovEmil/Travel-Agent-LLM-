"""Публичный доступ к совместному плану по share_token."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import Trip, Vote
from ..schemas import VoteOut, VoteRequest
from ..services.extras import build_trip_extras
from ..services.rate_limit import check_share_rate_limit

router = APIRouter(prefix="/api/share", tags=["share"])


def _trip_by_token(token: str, db: Session) -> Trip:
    trip = db.scalars(select(Trip).where(Trip.share_token == token)).first()
    if trip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Share link not found")
    return trip


def _vote_summary(votes: list[Vote]) -> dict[str, dict]:
    summary: dict[str, dict] = {}
    for v in votes:
        bucket = summary.setdefault(
            v.slot_key, {"want": 0, "skip": 0, "day_index": v.day_index, "voters": []}
        )
        if v.value == "want":
            bucket["want"] += 1
        else:
            bucket["skip"] += 1
        bucket["voters"].append({"voter": v.voter, "value": v.value})
    return summary


@router.get("/{token}")
def get_shared_trip(token: str, request: Request, db: Session = Depends(get_db)):
    check_share_rate_limit(request)
    trip = _trip_by_token(token, db)
    extras = build_trip_extras(trip, geocode_limit=3)
    return {
        "name": trip.name,
        "brief": trip.brief,
        "start_date": trip.start_date.isoformat() if trip.start_date else None,
        "status": trip.status,
        "destination": extras["destination"],
        "days": extras["days"],
        "weather": extras["weather"],
        "links": extras["links"],
        "votes": _vote_summary(list(trip.votes)),
    }


@router.post("/{token}/votes", response_model=VoteOut)
def cast_vote(
    token: str,
    payload: VoteRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    check_share_rate_limit(request)
    trip = _trip_by_token(token, db)
    voter = payload.voter.strip()[:40]
    if not voter:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Укажите имя")
    existing = db.scalars(
        select(Vote).where(
            Vote.trip_id == trip.id,
            Vote.slot_key == payload.slot_key,
            Vote.voter == voter,
        )
    ).first()
    if existing:
        existing.value = payload.value
        existing.day_index = payload.day_index
        db.commit()
        db.refresh(existing)
        return existing
    vote = Vote(
        trip_id=trip.id,
        day_index=payload.day_index,
        slot_key=payload.slot_key[:160],
        voter=voter,
        value=payload.value,
    )
    db.add(vote)
    db.commit()
    db.refresh(vote)
    return vote
