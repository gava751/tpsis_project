"""REST-контроллер аналитики: отчет план-факт (UC-6)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.di import get_plan_fact_service
from app.dto.analytics_schemas import PlanFactResponse
from app.security.jwt_utils import UserPrincipal, get_current_user
from app.service.plan_fact_service import PlanFactService

router = APIRouter(prefix="/api/v1/promos", tags=["Аналитика (UC-6)"])


@router.get("/{id_promo}/plan-fact", response_model=PlanFactResponse)
def plan_fact(
    id_promo: int,
    user: UserPrincipal = Depends(get_current_user),
    service: PlanFactService = Depends(get_plan_fact_service),
) -> PlanFactResponse:
    """Экран «Отчет план-факт» (ЛР6, рисунок 3.4): отклонения, MAPE, WAPE."""
    return service.build_plan_fact(id_promo)
