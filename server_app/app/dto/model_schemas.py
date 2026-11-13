"""Схемы управления ML-моделями (UC-7 «Настроить ML-модели»)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class TrainRequest(BaseModel):
    """Запуск обучения модели на исторических данных (backtesting, UC-7, шаг 4)."""

    category: str | None = Field(
        default=None, description="Товарная категория, например «Фреш»"
    )
    category_weights: dict[str, float] = Field(
        default_factory=dict,
        description="Веса признаков/категорий (UC-7, шаг 3), например {'Фреш': 1.5}",
    )


class ModelInfoResponse(BaseModel):
    version: str
    trained_at: str
    category: str | None
    mape: float
    wape: float


class TrainResponse(ModelInfoResponse):
    activated: bool = Field(
        description="Модель сохранена как активная версия для расчетов"
    )
