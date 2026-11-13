"""Реализации репозиториев на SQLAlchemy (СУБД MySQL по ЛР7)."""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.enums import ForecastStatus
from app.model.orm import (
    ForecastResult,
    Product,
    PromoCampaign,
    PromoProduct,
    Store,
)
from app.repository.interfaces import (
    CatalogRepository,
    DateTimeProvider,
    ForecastRepository,
    PromoRepository,
)


class SqlAlchemyPromoRepository(PromoRepository):
    """Доступ к таблицам promo_campaign и promo_product."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, promo: PromoCampaign) -> PromoCampaign:
        self._session.add(promo)
        self._session.flush()
        return promo

    def get(self, id_promo: int) -> PromoCampaign | None:
        return self._session.get(PromoCampaign, id_promo)

    def list(self) -> list[PromoCampaign]:
        return list(
            self._session.scalars(
                select(PromoCampaign).order_by(PromoCampaign.id_promo)
            )
        )

    def update_status(self, id_promo: int, status: str) -> None:
        self._session.execute(
            update(PromoCampaign)
            .where(PromoCampaign.id_promo == id_promo)
            .values(status=status)
        )

    def add_promo_product(self, promo_product: PromoProduct) -> PromoProduct:
        self._session.add(promo_product)
        self._session.flush()
        return promo_product


class SqlAlchemyCatalogRepository(CatalogRepository):
    """Доступ к справочникам product и store."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_products(self, ids: list[int]) -> list[Product]:
        return list(
            self._session.scalars(select(Product).where(Product.id_product.in_(ids)))
        )

    def get_product(self, id_product: int) -> Product | None:
        return self._session.get(Product, id_product)

    def list_products(self) -> list[Product]:
        return list(self._session.scalars(select(Product)))

    def list_stores(self) -> list[Store]:
        return list(self._session.scalars(select(Store)))


class SqlAlchemyForecastRepository(ForecastRepository):
    """Доступ к таблице forecast_result (жизненный цикл статусов прогноза)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_promo_product(self, id_promo_prod: int) -> PromoProduct | None:
        return self._session.get(PromoProduct, id_promo_prod)

    def create_forecasts(self, rows: list[ForecastResult]) -> list[ForecastResult]:
        self._session.add_all(rows)
        self._session.flush()
        return rows

    def list_by_promo(self, id_promo: int) -> list[ForecastResult]:
        stmt = (
            select(ForecastResult)
            .join(PromoProduct, PromoProduct.id_promo_prod == ForecastResult.id_promo_prod)
            .where(PromoProduct.id_promo == id_promo)
            .order_by(ForecastResult.id_forecast)
        )
        return list(self._session.scalars(stmt))

    def get_forecast(self, id_forecast: int) -> ForecastResult | None:
        return self._session.get(ForecastResult, id_forecast)

    def update_status(self, id_forecast: int, status: str) -> None:
        self._session.execute(
            update(ForecastResult)
            .where(ForecastResult.id_forecast == id_forecast)
            .values(status=status)
        )

    def save(self, forecast: ForecastResult) -> None:
        self._session.add(forecast)
        self._session.flush()

    def _transition(self, id_promo: int, source: tuple[str, ...], target: str) -> None:
        self._session.execute(
            update(ForecastResult)
            .where(
                ForecastResult.id_promo_prod.in_(
                    select(PromoProduct.id_promo_prod).where(
                        PromoProduct.id_promo == id_promo
                    )
                ),
                ForecastResult.status.in_(source),
            )
            .values(status=target)
        )

    def approve(self, id_promo: int) -> None:
        self._transition(id_promo, (ForecastStatus.CALCULATED.value,
                                   ForecastStatus.CORRECTED.value),
                         ForecastStatus.APPROVED.value)

    def export_done(self, id_promo: int) -> None:
        self._transition(id_promo, (ForecastStatus.APPROVED.value,),
                         ForecastStatus.EXPORTED.value)


class SystemDateTimeProvider(DateTimeProvider):
    """Реальный системный источник текущей даты."""

    def today(self) -> date:
        return datetime.now(timezone.utc).date()
