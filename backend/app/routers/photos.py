"""Публичные/общие эндпоинты для фото направлений."""

from fastapi import APIRouter, Depends, Query

from ..deps import get_current_user
from ..models import User
from ..services.photos import destination_photos

router = APIRouter(prefix="/api/photos", tags=["photos"])


@router.get("")
def lookup_photos(
    q: str = Query(..., min_length=2, max_length=120),
    current_user: User = Depends(get_current_user),
):
    """Реальные фото по названию города/страны (Wikimedia, кэш)."""
    photos = destination_photos(q.strip(), limit=6)
    return {"destination": q.strip(), "photos": photos}
