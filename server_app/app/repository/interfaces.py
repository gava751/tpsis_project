"""Интерфейсы репозиториев (паттерн «Репозиторий», принципы ISP и DIP).

Сервисный слой зависит только от абстракций, а не от конкретной СУБД
– это позволяет подменять реализации и изолированно тестировать логику.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from app.model.orm import ForecastResult, Product, PromoCampaign, PromoProduct, Store


class PromoRepository(ABC):
    @abstractmethod
    def create(self, promo: PromoCampaign) -> PromoCampaign: ...

    @abstractmethod
    def get(self, id_promo: int) -> PromoCampaign | None: ...

    @abstractmethod
    def list(self) -> list[PromoCampaign]: ...

    @abstractmethod
    def update_status(self, id_promo: int, status: str) -> None: ...

    @abstractmethod
    def add_promo_product(self, promo_product: PromoProduct) -> PromoProduct: ...


class CatalogRepository(ABC):
    @abstractmethod
    def get_products(self, ids: list[int]) -> list[Product]: ...

    @abstractmethod
    def get_product(self, id_product: int) -> Product | None: ...

    @abstractmethod
    def list_products(self) -> list[Product]: ...

    @abstractmethod
    def list_stores(self) -> list[Store]: ...


class ForecastRepository(ABC):
    @abstractmethod
    def get_promo_product(self, id_promo_prod: int) -> PromoProduct | None: ...

    @abstractmethod
    def create_forecasts(self, rows: list[ForecastResult]) -> list[ForecastResult]: ...

    @abstractmethod
    def list_by_promo(self, id_promo: int) -> list[ForecastResult]: ...

    @abstractmethod
    def get_forecast(self, id_forecast: int) -> ForecastResult | None: ...

    @abstractmethod
    def update_status(self, id_forecast: int, status: str) -> None: ...

    @abstractmethod
    def save(self, forecast: ForecastResult) -> None: ...

    @abstractmethod
    def approve(self, id_promo: int) -> None:
        """Переводит CALCULATED/CORRECTED-строки промоакции в статус APPROVED."""

    @abstractmethod
    def export_done(self, id_promo: int) -> None:
        """Переводит строки промоакции из APPROVED в EXPORTED (UC-9)."""


class DateTimeProvider(ABC):
    """Поставщик текущей даты – упрощает тестирование бизнес-правил."""

    @abstractmethod
    def today(self) -> date: ...
