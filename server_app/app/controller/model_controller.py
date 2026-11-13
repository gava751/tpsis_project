"""REST-контроллер панели ML-моделей (UC-7) – доступ только для роли «Аналитик»."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.di import get_model_service
from app.core.enums import Role
from app.dto.model_schemas import ModelInfoResponse, TrainRequest, TrainResponse
from app.security.jwt_utils import UserPrincipal, require_roles
from app.service.model_service import ModelService

router = APIRouter(prefix="/api/v1/models", tags=["ML-модели (UC-7)"])


@router.post("/train", response_model=TrainResponse)
def train_model(
    request: TrainRequest,
    user: UserPrincipal = Depends(require_roles(Role.ANALYST)),
    service: ModelService = Depends(get_model_service),
) -> TrainResponse:
    """Шаги 4–6 UC-7: тестовое обучение (backtesting) с новыми весами признаков."""
    return service.train(request)


@router.get("", response_model=list[ModelInfoResponse])
def list_models(
    user: UserPrincipal = Depends(require_roles(Role.ANALYST)),
    service: ModelService = Depends(get_model_service),
) -> list[ModelInfoResponse]:
    """Панель управления моделями: версии и метрики точности."""
    return service.list_models()
