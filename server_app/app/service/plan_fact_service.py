"""Аналитический сервис: отчет план-факт (UC-6) с метриками MAPE и WAPE."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.enums import ForecastStatus
from app.core.errors import ConflictError, NotFoundError
from app.dto.analytics_schemas import (
    PlanFactMetrics,
    PlanFactResponse,
    PlanFactRow,
)
from app.integration.erp_gateway import ErpGateway
from app.repository.interfaces import CatalogRepository, DateTimeProvider, ForecastRepository, PromoRepository


class PlanFactService:
    """Сравнение утвержденного плана с фактическими продажами из ERP (UC-6)."""

    def __init__(self, promos: PromoRepository, forecasts: ForecastRepository,
                 catalogs: CatalogRepository, erp: ErpGateway,
                 clock: DateTimeProvider, session: Session) -> None:
        self._promos = promos
        self._forecasts = forecasts
        self._catalogs = catalogs
        self._erp = erp
        self._clock = clock
        self._session = session

    def build_plan_fact(self, id_promo: int) -> PlanFactResponse:
        promo = self._promos.get(id_promo)
        if promo is None:
            raise NotFoundError(f"Промоакция {id_promo} не найдена")
        if promo.end_date >= self._clock.today():
            raise ConflictError("Отчет план-факт доступен только для завершенных акций")

        rows = self._forecasts.list_by_promo(id_promo)
        exported = [
            r for r in rows
            if r.status in (ForecastStatus.EXPORTED.value, ForecastStatus.APPROVED.value)
        ]
        if not exported:
            raise ConflictError("Для акции отсутствуют утвержденные объемы заказа")

        facts = self._erp.get_fact(  # шаг 2 основного потока UC-6
            id_promo,
            list({row.promo_product.id_product for row in exported}),
            promo.start_date,
            promo.end_date,
        )
        fact_map = {(f.id_product, f.id_store): f.fact_qty for f in facts}

        result_rows: list[PlanFactRow] = []
        deviations_pct: list[float] = []
        abs_deviation_sum = 0.0
        fact_sum = 0.0
        for forecast in exported:
            product = forecast.promo_product.product
            store = forecast.store
            plan_qty = forecast.final_order_qty
            fact_qty = fact_map.get((product.id_product, store.id_store), 0)
            deviation = fact_qty - plan_qty
            deviation_pct = (deviation / plan_qty * 100) if plan_qty else 0.0
            amount = deviation * float(product.base_price)
            result_rows.append(
                PlanFactRow(
                    id_product=product.id_product,
                    product_name=product.name,
                    id_store=store.id_store,
                    store_address=store.address,
                    plan_qty=plan_qty,
                    fact_qty=fact_qty,
                    deviation_qty=deviation,
                    deviation_pct=round(deviation_pct, 1),
                    deviation_amount=round(amount, 2),
                )
            )
            if fact_qty > 0:
                deviations_pct.append(abs(deviation) / fact_qty * 100)
            abs_deviation_sum += abs(deviation)
            fact_sum += fact_qty

        # Шаг 4 UC-6: метрики точности модели
        mape = round(sum(deviations_pct) / len(deviations_pct), 2) if deviations_pct else 0.0
        wape = round(abs_deviation_sum / fact_sum * 100, 2) if fact_sum else 0.0

        return PlanFactResponse(
            id_promo=id_promo,
            promo_name=promo.promo_name,
            rows=result_rows,
            metrics=PlanFactMetrics(mape=mape, wape=wape),
        )
