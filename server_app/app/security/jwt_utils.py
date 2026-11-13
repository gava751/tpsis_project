"""Выпуск и проверка JWT-токенов (UC-1) и FastAPI-зависимости безопасности.

Реализует принцип DIP: контроллеры зависят от абстрактного Principal,
а не от деталей реализации аутентификации.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.enums import Role
from app.core.errors import AccessDeniedError, NotAuthenticatedError

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class UserPrincipal:
    """Учетная запись авторизованного пользователя."""

    login: str
    role: Role

    def require_role(self, *roles: Role) -> None:
        if self.role not in roles:
            raise AccessDeniedError(
                "Недостаточно прав для выполнения операции"
            )


def create_access_token(login: str, role: str) -> str:
    payload = {
        "sub": login,
        "role": role,
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=settings.jwt_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UserPrincipal:
    if credentials is None:
        raise NotAuthenticatedError()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError:
        raise NotAuthenticatedError("Недействительный токен")
    try:
        role = Role(payload.get("role", ""))
    except ValueError:
        raise NotAuthenticatedError("Неизвестная роль пользователя")
    return UserPrincipal(login=payload["sub"], role=role)


def require_roles(*roles: Role):
    """Фабрика зависимостей для проверки роли (например, UC-7 – только аналитик)."""

    def checker(user: UserPrincipal = Depends(get_current_user)) -> UserPrincipal:
        user.require_role(*roles)
        return user

    return checker
