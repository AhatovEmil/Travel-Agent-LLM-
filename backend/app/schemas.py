from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


class TripCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    brief: str = Field(min_length=10, max_length=10000)
    start_date: date | None = None


class TripOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    brief: str
    start_date: date | None = None
    share_token: str | None = None
    status: str
    current_phase: str
    error: str
    created_at: datetime
    updated_at: datetime


class ArtifactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phase: str
    title: str
    content: str
    created_at: datetime


class ArtifactVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phase: str
    content: str
    source: str
    source_meta: str
    created_at: datetime


class ChatRequest(BaseModel):
    message: str = Field(min_length=3, max_length=2000)


class PhaseRerunRequest(BaseModel):
    phase: str = Field(pattern="^(brief|itinerary|budget|checklist)$")


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    created_at: datetime


class AskResponse(BaseModel):
    reply: str
    messages: list[ChatMessageOut]


class LiveAdjustRequest(BaseModel):
    reason: str = Field(pattern="^(late|rain|custom)$")
    message: str = Field(default="", max_length=1000)


class ShareResponse(BaseModel):
    share_token: str
    share_path: str


class VoteRequest(BaseModel):
    voter: str = Field(min_length=1, max_length=40)
    day_index: int = Field(ge=0, le=30)
    slot_key: str = Field(min_length=1, max_length=160)
    value: str = Field(pattern="^(want|skip)$")


class VoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    day_index: int
    slot_key: str
    voter: str
    value: str
    created_at: datetime
