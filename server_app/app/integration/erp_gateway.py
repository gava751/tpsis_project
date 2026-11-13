"""Интеграция с ERP-системой: загрузка истории и факта продаж (UC-8, UC-6).

Принципы: DIP (сервисы зависят от абстрактного шлюза) и SRP
(класс отвечает только за транспорт данных).
При сбое выполняются 3 повторные попытки (альтернативный поток UC-8).
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

import httpx

from app.core.config import settings
from app.core.errors import IntegrationError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SalesRecord:
    """Запись исторической продажи (чековые данные за период до 3 лет)."""

    date: date
    id_product: int
    id_store: int
    qty: int
    price: float
    discount_percent: float = 0.0


@dataclass(frozen=True)
class FactRecord:
    """Фактическая продажа за период завершенной акции (план-факт, UC-6)."""

    id_product: int
    id_store: int
    fact_qty: int


class ErpGateway(ABC):
    @abstractmethod
    def get_history(
        self, id_products: list[int], date_from: date, date_to: date
    ) -> list[SalesRecord]: ...

    @abstractmethod
    def get_fact(self, id_promo: int, id_products: list[int],
                 date_from: date, date_to: date) -> list[FactRecord]: ...

    @abstractmethod
    def send_orders(self, payload: dict) -> dict: ...


class HttpErpGateway(ErpGateway):
    """HTTP-реализация шлюза к ERP-системе (формат JSON, ретраи по UC-8)."""

    def __init__(self, base_url: str | None = None,
                 retries: int | None = None,
                 timeout: float | None = None) -> None:
        self._base_url = (base_url or settings.erp_base_url).rstrip("/")
        self._retries = retries or settings.erp_retries
        self._timeout = timeout or settings.erp_timeout_seconds

    def _request(self, method: str, path: str, json_body: dict | None = None) -> dict:
        url = f"{self._base_url}{path}"
        last_error: Exception | None = None
        for attempt in range(1, self._retries + 1):
            try:
                response = httpx.request(
                    method, url, json=json_body, timeout=self._timeout
                )
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                logger.warning(
                    "ERP-запрос %s %s: попытка %d/%d не удалась: %s",
                    method, url, attempt, self._retries, exc,
                )
        raise IntegrationError("Невозможно загрузить данные из ERP-системы")

    def get_history(
        self, id_products: list[int], date_from: date, date_to: date
    ) -> list[SalesRecord]:
        data = self._request(
            "POST",
            "/api/v1/history",
            {
                "id_products": id_products,
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
            },
        )
        return [
            SalesRecord(
                date=date.fromisoformat(row["date"]),
                id_product=row["id_product"],
                id_store=row["id_store"],
                qty=row["qty"],
                price=row["price"],
                discount_percent=row.get("discount_percent", 0.0),
            )
            for row in data["records"]
        ]

    def get_fact(self, id_promo: int, id_products: list[int],
                 date_from: date, date_to: date) -> list[FactRecord]:
        data = self._request(
            "POST",
            "/api/v1/fact",
            {
                "id_promo": id_promo,
                "id_products": id_products,
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
            },
        )
        return [
            FactRecord(
                id_product=row["id_product"],
                id_store=row["id_store"],
                fact_qty=row["fact_qty"],
            )
            for row in data["records"]
        ]

    def send_orders(self, payload: dict) -> dict:
        return self._request("POST", "/api/v1/orders", payload)
