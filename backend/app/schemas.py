from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


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
    free_left: int = 0
    free_limit: int = 5
    free_used: int = 0
    credit_balance: int = 0
    period: str = ""
    telegram_linked: bool = False
    telegram_id: str | None = None


class GenerationPackage(BaseModel):
    id: str
    generations: int
    price_rub: int
    label: str
    tribute_url: str = ""
    buy_url: str = ""


class BillingPackagesOut(BaseModel):
    packages: list[GenerationPackage]
    telegram_url: str
    bot_url: str = ""
    bot_username: str = ""
    free_generations_per_month: int
    tribute_configured: bool = False


class AdminCreditRequest(BaseModel):
    email: EmailStr
    amount: int = Field(ge=1, le=10000)


class AdminCreditResponse(BaseModel):
    email: str
    credit_balance: int
    added: int


class TelegramLinkInitData(BaseModel):
    init_data: str = Field(min_length=10, max_length=4096)


class TelegramLinkWidget(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class TelegramLinkResponse(BaseModel):
    telegram_linked: bool
    telegram_id: str
    credits_claimed: int = 0
    credit_balance: int = 0


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


class QuestRequest(BaseModel):
    day_index: int = Field(ge=0, le=30)


class JournalCreate(BaseModel):
    day_index: int = Field(ge=0, le=60)
    kind: str = Field(default="note", pattern="^(note|evening)$")
    mood: str = Field(default="", max_length=32)
    content: str = Field(default="", max_length=8000)
    done_slots: list[str] = Field(default_factory=list)


class JournalUpdate(BaseModel):
    mood: str | None = Field(default=None, max_length=32)
    content: str | None = Field(default=None, max_length=8000)
    done_slots: list[str] | None = None


class JournalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_id: int
    day_index: int
    kind: str
    mood: str
    content: str
    done_slots: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class EveningCheckin(BaseModel):
    day_index: int = Field(ge=0, le=60)
    mood: str = Field(default="ok", max_length=32)
    content: str = Field(default="", max_length=8000)
    done_slots: list[str] = Field(default_factory=list)
