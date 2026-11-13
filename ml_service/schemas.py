"""Схемы запросов и ответов ML-сервиса (FastAPI/Pydantic)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class HistoryRow(BaseModel):
    date: str
    id_product: int
    id_store: int
    qty: int
    price: float
    category: str
    store_format: str


class ForecastTaskRow(BaseModel):
    id_product: int
    id_store: int
    category: str
    store_format: str
    base_price: float
    discount_percent: float
    promo_days: list[str] = Field(min_length=1)


class ForecastRequest(BaseModel):
    history: list[HistoryRow]
    tasks: list[ForecastTaskRow] = Field(min_length=1)


class ForecastResultRow(BaseModel):
    id_product: int
    id_store: int
    baseline_qty: int
    uplift_qty: int


class ForecastResponse(BaseModel):
    results: list[ForecastResultRow]


class TrainRequest(BaseModel):
    category: str | None = None
    category_weights: dict[str, float] = Field(default_factory=dict)


class ModelInfo(BaseModel):
    version: str
    trained_at: str
    category: str | None
    mape: float
    wape: float


class TrainResponse(ModelInfo):
    pass


class ModelsResponse(BaseModel):
    models: list[ModelInfo]
