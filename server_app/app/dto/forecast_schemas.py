"""Схемы расчета и корректировки прогноза (UC-3, UC-4, UC-5)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ForecastStartRequest(BaseModel):
    """Запуск расчета прогноза.

    analog_products – карта «товар-новинка -> товар-аналог» (BR-3, FR3-2):
    пользователь выбирает аналог из справочника, если история недостаточна.
    """

    analog_products: dict[int, int] = Field(default_factory=dict)


class ForecastRowResponse(BaseModel):
    id_forecast: int
    id_promo_prod: int
    id_product: int
    product_name: str
    category: str
    id_store: int
    store_address: str
    baseline_qty: int
    uplift_qty: int
    final_order_qty: int
    status: str
    is_corrected: bool
    correction_reason: str | None = None

    class Config:
        from_attributes = True


class ForecastResponse(BaseModel):
    id_promo: int
    promo_status: str
    rows: list[ForecastRowResponse]


class CorrectionItem(BaseModel):
    """Ручная корректировка строки прогноза (UC-4, шаг 3: причина обязательна)."""

    id_forecast: int
    final_order_qty: int = Field(ge=0)
    correction_reason: str = Field(
        min_length=1, max_length=100,
        description="Причина: «ограничение склада», «риск недовоза», "
                    "«ожидание сверхспроса» и др.",
    )


class CorrectionRequest(BaseModel):
    corrections: list[CorrectionItem] = Field(min_length=1)


class ApprovalRequest(BaseModel):
    """Подтверждение утверждения объемов заказа (UC-5, шаг 3)."""

    confirmed: bool = Field(description="Пользователь подтвердил утверждение")


class ExportResultRow(BaseModel):
    id_product: int
    id_store: int
    final_order_qty: int
    erp_status: str
    reason: str | None = None


class ExportResponse(BaseModel):
    promo_status: str
    rows: list[ExportResultRow]
