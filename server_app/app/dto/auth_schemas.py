"""Схемы аутентификации (UC-1)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    login: str = Field(min_length=1, description="Учетная запись пользователя")
    password: str = Field(min_length=1, description="Пароль")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    login: str
    role: str
