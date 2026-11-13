"""Схемы аналитического отчета план-факт (UC-6)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class PlanFactRow(BaseModel):
    id_product: int
    product_name: str
    id_store: int
    store_address: str
    plan_qty: int = Field(description="Утвержденный объем заказа (план)")
    fact_qty: int = Field(description="Фактические продажи за период (из ERP)")
    deviation_qty: int
    deviation_pct: float
    deviation_amount: float = Field(description="Отклонение в рублях")


class PlanFactMetrics(BaseModel):
    mape: float
    wape: float


class PlanFactResponse(BaseModel):
    id_promo: int
    promo_name: str
    rows: list[PlanFactRow]
    metrics: PlanFactMetrics
