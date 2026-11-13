"""Схемы промоакций (UC-2 «Настроить параметры промоакции»)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class PromoProductItem(BaseModel):
    """Товар, включаемый в промоакцию, с механикой «скидка %» (UC-2, шаг 4)."""

    id_product: int
    discount_percent: float = Field(gt=0, le=50, description="Глубина скидки, % (BR-4)")


class PromoCreateRequest(BaseModel):
    promo_name: str = Field(min_length=1, max_length=150)
    start_date: date
    end_date: date
    products: list[PromoProductItem] = Field(min_length=1)


class PromoProductResponse(BaseModel):
    id_promo_prod: int
    id_product: int
    product_name: str
    category: str
    discount_percent: float

    class Config:
        from_attributes = True


class PromoResponse(BaseModel):
    id_promo: int
    promo_name: str
    start_date: date
    end_date: date
    status: str
    products: list[PromoProductResponse] = []

    class Config:
        from_attributes = True
