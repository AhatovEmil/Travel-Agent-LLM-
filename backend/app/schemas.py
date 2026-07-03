from datetime import datetime

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


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    idea: str = Field(min_length=10, max_length=10000)


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    idea: str
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


class GeneratedFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    path: str
    content: str
