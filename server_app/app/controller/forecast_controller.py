"""REST-контроллер прогнозов: расчет (UC-3), корректировка (UC-4),
утверждение и экспорт (UC-5, UC-9)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.di import get_forecast_service
from app.dto.forecast_schemas import (
    ApprovalRequest,
    CorrectionRequest,
    ExportResponse,
    ForecastResponse,
    ForecastRowResponse,
    ForecastStartRequest,
)
from app.security.jwt_utils import UserPrincipal, get_current_user
from app.service.forecast_service import ForecastService

router = APIRouter(prefix="/api/v1", tags=["Прогноз (UC-3…UC-5)"])


def _to_response(id_promo: int, promo_status: str, rows) -> ForecastResponse:
    return ForecastResponse(
        id_promo=id_promo,
        promo_status=promo_status,
        rows=[
            ForecastRowResponse(
                id_forecast=row.id_forecast,
                id_promo_prod=row.id_promo_prod,
                id_product=row.promo_product.id_product,
                product_name=row.promo_product.product.name,
                category=row.promo_product.product.category,
                id_store=row.id_store,
                store_address=row.store.address,
                baseline_qty=row.baseline_qty,
                uplift_qty=row.uplift_qty,
                final_order_qty=row.final_order_qty,
                status=row.status,
                is_corrected=row.is_corrected,
                correction_reason=row.correction_reason,
            )
            for row in rows
        ],
    )


@router.post("/promos/{id_promo}/forecast", response_model=ForecastResponse)
def run_forecast(
    id_promo: int,
    request: ForecastStartRequest,
    user: UserPrincipal = Depends(get_current_user),
    service: ForecastService = Depends(get_forecast_service),
) -> ForecastResponse:
    """UC-3: расчет baseline и uplift через ML-сервис с применением BR-2/BR-5."""
    rows = service.run_forecast(id_promo, request)
    return _to_response(id_promo, service.get_promo(id_promo).status, rows)


@router.get("/promos/{id_promo}/forecast", response_model=ForecastResponse)
def list_forecasts(
    id_promo: int,
    user: UserPrincipal = Depends(get_current_user),
    service: ForecastService = Depends(get_forecast_service),
) -> ForecastResponse:
    """Таблица прогноза для экрана ЛР6 (рисунок 3.3)."""
    rows = service.list_forecasts(id_promo)
    return _to_response(id_promo, service.get_promo(id_promo).status, rows)


@router.get("/promos/{id_promo}/forecast", response_model=ForecastResponse)
def list_forecasts(
    id_promo: int,
    user: UserPrincipal = Depends(get_current_user),
    service: ForecastService = Depends(get_forecast_service),
) -> ForecastResponse:
    """Таблица прогноза для экрана ЛР6 (рисунок 3.3)."""
    rows = service.list_forecasts(id_promo)
    return _to_response(id_promo, _promo_status(service, id_promo), rows)


@router.put("/forecasts/corrections", response_model=ForecastResponse)
def correct_forecast(
    request: CorrectionRequest,
    user: UserPrincipal = Depends(get_current_user),
    service: ForecastService = Depends(get_forecast_service),
) -> ForecastResponse:
    """UC-4: ручная корректировка объемов с обязательной причиной."""
    rows = service.correct_forecast(request)
    id_promo = rows[0].promo_product.id_promo
    return _to_response(id_promo, service.get_promo(id_promo).status, rows)


@router.post("/promos/{id_promo}/approval", response_model=ExportResponse)
def approve_forecast(
    id_promo: int,
    request: ApprovalRequest,
    user: UserPrincipal = Depends(get_current_user),
    service: ForecastService = Depends(get_forecast_service),
) -> ExportResponse:
    """UC-5: утверждение объемов; include UC-9 – экспорт заказов в ERP."""
    results = service.approve_forecast(id_promo, request, user.login)
    promo = service.get_promo(id_promo)
    return ExportResponse(promo_status=promo.status, rows=results)
