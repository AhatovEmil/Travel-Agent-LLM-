from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    trips: Mapped[list["Trip"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    brief: Mapped[str] = mapped_column(Text, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    share_token: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft|running|completed|failed
    current_phase: Mapped[str] = mapped_column(String(32), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    owner: Mapped[User] = relationship(back_populates="trips")
    artifacts: Mapped[list["Artifact"]] = relationship(
        back_populates="trip", cascade="all, delete-orphan", order_by="Artifact.id"
    )
    versions: Mapped[list["ArtifactVersion"]] = relationship(
        back_populates="trip", cascade="all, delete-orphan", order_by="ArtifactVersion.id"
    )
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="trip", cascade="all, delete-orphan", order_by="ChatMessage.id"
    )
    votes: Mapped[list["Vote"]] = relationship(
        back_populates="trip", cascade="all, delete-orphan", order_by="Vote.id"
    )


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"), index=True, nullable=False)
    phase: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    trip: Mapped[Trip] = relationship(back_populates="artifacts")


class ArtifactVersion(Base):
    """Snapshots of itinerary before overwrite (chat / live / rebuild / rollback)."""

    __tablename__ = "artifact_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"), index=True, nullable=False)
    phase: Mapped[str] = mapped_column(String(32), nullable=False, default="itinerary")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="pipeline")
    source_meta: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    trip: Mapped[Trip] = relationship(back_populates="versions")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    trip: Mapped[Trip] = relationship(back_populates="messages")


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("trip_id", "slot_key", "voter", name="uq_vote_trip_slot_voter"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"), index=True, nullable=False)
    day_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    slot_key: Mapped[str] = mapped_column(String(160), nullable=False)
    voter: Mapped[str] = mapped_column(String(40), nullable=False)
    value: Mapped[str] = mapped_column(String(16), nullable=False)  # want | skip
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    trip: Mapped[Trip] = relationship(back_populates="votes")
