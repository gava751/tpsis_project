"""REST-контроллер аутентификации (UC-1 «Авторизоваться в системе»)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.di import get_notification_service
from app.dto.auth_schemas import LoginRequest, TokenResponse
from app.security.directory_stub import DirectoryStub
from app.security.jwt_utils import UserPrincipal, create_access_token, get_current_user
from app.service.notifications import NotificationService

router = APIRouter(prefix="/api/v1/auth", tags=["Аутентификация (UC-1)"])

_directory = DirectoryStub()


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest) -> TokenResponse:
    """Шаги 1–4 основного потока UC-1: проверка учетных данных, выпуск JWT."""
    login_name, role = _directory.authenticate(request.login, request.password)
    return TokenResponse(
        access_token=create_access_token(login_name, role),
        login=login_name,
        role=role,
    )


@router.get("/me")
def me(user: UserPrincipal = Depends(get_current_user)) -> dict:
    """Проверка действительности токена и роли пользователя."""
    return {"login": user.login, "role": user.role.value}


@router.get("/notifications")
def notifications(
    user: UserPrincipal = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    """Уведомления о сбоях расчета и экспорта (UC-3, UC-9)."""
    return {
        "items": [
            {"text": n.text, "created_at": n.created_at}
            for n in service.for_user(user.login)
        ]
    }
