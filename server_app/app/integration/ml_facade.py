"""Фасад ML-сервиса (паттерн «Фасад», ЛР8).

Скрывает детали сетевого взаимодействия с вычислительным узлом:
формирование датасета, вызов расчета baseline/uplift и обучение модели (UC-7).
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx

from app.core.config import settings
from app.core.errors import IntegrationError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HistoryRow:
    date: str
    id_product: int
    id_store: int
    qty: int
    price: float
    discount_percent: float = 0.0
    category: str = ""
    store_format: str = ""


@dataclass(frozen=True)
class ForecastTaskRow:
    """Строка задачи расчета: акционный товар в магазине с параметрами акции."""

    id_product: int
    id_store: int
    category: str
    store_format: str
    base_price: float
    discount_percent: float
    promo_days: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MlForecastResult:
    id_product: int
    id_store: int
    baseline_qty: int
    uplift_qty: int


@dataclass(frozen=True)
class MlTrainResult:
    version: str
    trained_at: str
    category: str | None
    mape: float
    wape: float


class MlServiceFacade(ABC):
    @abstractmethod
    def request_forecast(
        self, history: list[HistoryRow], tasks: list[ForecastTaskRow]
    ) -> list[MlForecastResult]: ...

    @abstractmethod
    def train_model(self, category: str | None,
                    category_weights: dict[str, float]) -> MlTrainResult: ...


class HttpMlServiceFacade(MlServiceFacade):
    """HTTP-реализация фасада к ML-сервису (Uvicorn-узел)."""

    def __init__(self, base_url: str | None = None, timeout: float = 120.0) -> None:
        self._base_url = (base_url or settings.ml_service_url).rstrip("/")
        self._timeout = timeout

    def request_forecast(
        self, history: list[HistoryRow], tasks: list[ForecastTaskRow]
    ) -> list[MlForecastResult]:
        try:
            response = httpx.post(
                f"{self._base_url}/forecast",
                json={
                    "history": [row.__dict__ for row in history],
                    "tasks": [row.__dict__ for row in tasks],
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            logger.error("ML-сервис недоступен: %s", exc)
            raise IntegrationError("ML-сервис недоступен")
        return [
            MlForecastResult(
                id_product=item["id_product"],
                id_store=item["id_store"],
                baseline_qty=item["baseline_qty"],
                uplift_qty=item["uplift_qty"],
            )
            for item in data["results"]
        ]

    def train_model(self, category: str | None,
                    category_weights: dict[str, float]) -> MlTrainResult:
        try:
            response = httpx.post(
                f"{self._base_url}/train",
                json={"category": category, "category_weights": category_weights},
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            logger.error("Сбой обучения модели: %s", exc)
            raise IntegrationError("ML-сервис недоступен")
        return MlTrainResult(
            version=data["version"],
            trained_at=data["trained_at"],
            category=data.get("category"),
            mape=data["mape"],
            wape=data["wape"],
        )
