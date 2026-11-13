"""Сервис прогнозирования: UC-3, UC-4, UC-5 (+ include UC-8, UC-9).

Реализует алгоритм запуска расчета прогноза промоакции (схема ЛР8):
проверка доступа -> валидация -> проверка истории -> запись «В расчете» ->
вызов ML-сервиса через фасад -> применение бизнес-правил -> сохранение.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.enums import ForecastStatus, PromoStatus
from app.core.errors import ConflictError, InsufficientHistoryError, NotFoundError
from app.dto.forecast_schemas import (
    ApprovalRequest,
    CorrectionRequest,
    ExportResultRow,
    ForecastStartRequest,
)
from app.integration.erp_exporter import ErpExporter, ExportRow
from app.integration.erp_gateway import ErpGateway, SalesRecord
from app.integration.ml_facade import (
    ForecastTaskRow,
    HistoryRow,
    MlServiceFacade,
)
from app.model.orm import ForecastResult, PromoProduct
from app.repository.interfaces import (
    CatalogRepository,
    DateTimeProvider,
    ForecastRepository,
    PromoRepository,
)
from app.service import rules
from app.service.notifications import NotificationService
from app.service.strategies import ForecastStrategyResolver

logger = logging.getLogger(__name__)


class ForecastService:
    """Координация расчета, корректировки и утверждения прогнозов.

    Зависимости внедряются через конструктор (шаблон DI): сервис
    опирается только на абстракции репозиториев, шлюзов и фасада (DIP).
    """

    def __init__(
        self,
        session: Session,
        promos: PromoRepository,
        forecasts: ForecastRepository,
        catalogs: CatalogRepository,
        erp: ErpGateway,
        ml_facade: MlServiceFacade,
        exporter: ErpExporter,
        clock: DateTimeProvider,
        notifications: NotificationService,
    ) -> None:
        self._session = session
        self._promos = promos
        self._forecasts = forecasts
        self._catalogs = catalogs
        self._erp = erp
        self._ml = ml_facade
        self._exporter = exporter
        self._clock = clock
        self._notifications = notifications
        self._strategies = ForecastStrategyResolver()

    # ------------------------------------------------------------------ UC-3

    def run_forecast(self, id_promo: int, request: ForecastStartRequest) -> list[ForecastResult]:
        """Запуск расчета прогноза продаж промоакции (алгоритм ЛР8)."""
        promo = self._promos.get(id_promo)
        if promo is None:
            raise NotFoundError(f"Промоакция {id_promo} не найдена")
        if promo.status != PromoStatus.DRAFT.value:
            raise ConflictError("Расчет прогноза возможен только для акции в статусе «Черновик»")

        promo_products = list(promo.products)
        stores = self._catalogs.list_stores()

        # UC-8 (include): загрузка исторических данных из ERP-системы
        history = self._load_history(promo_products, request.analog_products)

        # Шаг 5: фиксация запуска вычислительной задачи (статус «В расчете»)
        self._discard_previous_forecasts(promo_products)
        running_rows: list[ForecastResult] = []
        tasks: list[ForecastTaskRow] = []
        for pp in promo_products:
            for store in stores:
                row = ForecastResult(
                    id_promo_prod=pp.id_promo_prod,
                    id_store=store.id_store,
                    baseline_qty=0,
                    uplift_qty=0,
                    final_order_qty=0,
                    status=ForecastStatus.RUNNING.value,
                )
                running_rows.append(row)
                tasks.append(
                    ForecastTaskRow(
                        id_product=pp.id_product,
                        id_store=store.id_store,
                        category=pp.product.category,
                        store_format=store.format,
                        base_price=float(pp.product.base_price),
                        discount_percent=float(pp.discount_percent),
                        promo_days=[
                            (promo.start_date + timedelta(days=i)).isoformat()
                            for i in range((promo.end_date - promo.start_date).days + 1)
                        ],
                    )
                )
        self._forecasts.create_forecasts(running_rows)

        # Шаги 6–8: вызов ML-сервиса и применение бизнес-правил
        try:
            predictions = self._ml.request_forecast(history, tasks)
        except Exception:
            for row in running_rows:
                row.status = ForecastStatus.ERROR.value
            self._session.commit()
            self._notifications.notify(
                "manager", f"Ошибка расчета прогноза промоакции {id_promo}"
            )
            raise

        prediction_map = {
            (p.id_product, p.id_store): p for p in predictions
        }
        for row, task in zip(running_rows, tasks):
            prediction = prediction_map.get((task.id_product, task.id_store))
            if prediction is None:
                row.status = ForecastStatus.ERROR.value
                continue
            strategy = self._strategies.resolve(task.category)  # Стратегия
            baseline, final_order = strategy.calculate(
                prediction,
                pack_qty=self._pack_qty(task.id_product),
                promo_start=promo.start_date,
            )
            row.baseline_qty = baseline
            row.uplift_qty = prediction.uplift_qty
            row.final_order_qty = final_order
            row.status = ForecastStatus.CALCULATED.value

        self._session.commit()
        return self._forecasts.list_by_promo(id_promo)

    def _load_history(
        self, promo_products: list[PromoProduct], analogs: dict[int, int]
    ) -> list[HistoryRow]:
        """UC-8 + FR3-2: история продаж или данные товара-аналога (BR-3)."""
        today = self._clock.today()
        date_from = today - timedelta(days=365 * 3)  # глубина истории: 3 года
        history: list[HistoryRow] = []
        for pp in promo_products:
            source_id = analogs.get(pp.id_product, pp.id_product)
            records = self._erp.get_history([source_id], date_from, today)
            if not rules_enough_history(records):
                if source_id == pp.id_product:
                    raise InsufficientHistoryError(
                        f"Для товара {pp.id_product} накоплено менее "
                        f"{rules.MIN_HISTORY_DAYS} дней наблюдений; "
                        "выберите товар-аналог из справочника"
                    )
                # Данные аналога все равно недостаточны — считаем по ним
            history.extend(self._to_history_rows(records, category=pp.product.category))
        return history

    def _to_history_rows(self, records: list[SalesRecord], category: str) -> list[HistoryRow]:
        rows: list[HistoryRow] = []
        for record in records:
            rows.append(
                HistoryRow(
                    date=record.date.isoformat(),
                    id_product=record.id_product,
                    id_store=record.id_store,
                    qty=record.qty,
                    price=record.price,
                    discount_percent=record.discount_percent,
                    category=category,
                    store_format=self._store_format(record.id_store),
                )
            )
        return rows

    def _store_format(self, id_store: int) -> str:
        store = next((s for s in self._catalogs.list_stores() if s.id_store == id_store), None)
        return store.format if store else "unknown"

    def _pack_qty(self, id_product: int) -> int:
        product = self._catalogs.get_product(id_product)
        return product.pack_qty if product else 1

    def _discard_previous_forecasts(self, promo_products: list[PromoProduct]) -> None:
        """Повторный запуск расчета допустим для CALCULATED/CORRECTED/ERROR-строк."""
        for pp in promo_products:
            for forecast in list(pp.forecasts):
                if forecast.status in (
                    ForecastStatus.APPROVED.value, ForecastStatus.EXPORTED.value
                ):
                    raise ConflictError(
                        "Прогноз уже утвержден и не может быть пересчитан"
                    )
                self._session.delete(forecast)
        self._session.flush()

    # ------------------------------------------------------------------ UC-4

    def correct_forecast(self, request: CorrectionRequest) -> list[ForecastResult]:
        """Ручная корректировка объемов с обязательной причиной (UC-4)."""
        allowed = set(rules.correction_reasons())
        for item in request.corrections:
            forecast = self._forecasts.get_forecast(item.id_forecast)
            if forecast is None:
                raise NotFoundError(f"Строка прогноза {item.id_forecast} не найдена")
            if forecast.status not in (
                ForecastStatus.CALCULATED.value, ForecastStatus.CORRECTED.value
            ):
                raise ConflictError(
                    f"Корректировка невозможна: строка в статусе {forecast.status}"
                )
            if item.correction_reason.strip().lower() not in allowed:
                raise ConflictError(
                    "Причина корректировки должна быть выбрана из списка: "
                    + ", ".join(rules.correction_reasons())
                )
        for item in request.corrections:
            forecast = self._forecasts.get_forecast(item.id_forecast)
            forecast.final_order_qty = item.final_order_qty
            forecast.status = ForecastStatus.CORRECTED.value
            forecast.is_corrected = True
            forecast.correction_reason = item.correction_reason
            self._forecasts.save(forecast)
        self._session.commit()
        return [self._forecasts.get_forecast(i.id_forecast)
                for i in request.corrections]

    # ------------------------------------------------------------------ UC-5 + UC-9

    def approve_forecast(self, id_promo: int, request: ApprovalRequest,
                         user_login: str) -> list[ExportResultRow]:
        """Утверждение объемов заказа и экспорт в ERP (UC-5, include UC-9)."""
        promo = self._promos.get(id_promo)
        if promo is None:
            raise NotFoundError(f"Промоакция {id_promo} не найдена")
        if promo.status != PromoStatus.DRAFT.value:
            raise ConflictError("Акция уже утверждена")
        if not request.confirmed:
            raise ConflictError("Утверждение отменено пользователем")

        rows = self._forecasts.list_by_promo(id_promo)
        active = [r for r in rows if r.status in (
            ForecastStatus.CALCULATED.value, ForecastStatus.CORRECTED.value
        )]
        if not active:
            raise ConflictError("Нет рассчитанных объемов для утверждения")

        self._promos.update_status(id_promo, PromoStatus.APPROVED.value)
        self._forecasts.approve(id_promo)
        self._session.commit()

        # UC-9 (include): экспорт утвержденных объемов в ERP-систему
        export_rows = [
            ExportRow(
                id_product=row.promo_product.id_product,
                id_store=row.id_store,
                final_order_qty=row.final_order_qty,
            )
            for row in rows
            if row.status == ForecastStatus.APPROVED.value
        ]
        results = self._exporter.export(id_promo, export_rows)
        failed_keys = {
            (r.id_product, r.id_store)
            for r in results
            if r.erp_status != "OK"
        }
        for row in rows:
            if row.status != ForecastStatus.APPROVED.value:
                continue
            key = (row.promo_product.id_product, row.id_store)
            if key in failed_keys:
                # Альтернативный поток UC-9: строка помечается «Ошибка экспорта»
                row.status = ForecastStatus.ERROR.value
            else:
                row.status = ForecastStatus.EXPORTED.value
            self._forecasts.save(row)
        self._session.commit()
        if failed_keys:
            self._notifications.notify(
                user_login,
                f"Экспорт в ERP: {len(failed_keys)} строк с ошибкой; "
                "требуется разбор ошибок экспорта",
            )
        return results

    # ------------------------------------------------------------------ чтение

    def get_promo(self, id_promo: int):
        promo = self._promos.get(id_promo)
        if promo is None:
            raise NotFoundError(f"Промоакция {id_promo} не найдена")
        return promo

    def list_forecasts(self, id_promo: int) -> list[ForecastResult]:
        if self._promos.get(id_promo) is None:
            raise NotFoundError(f"Промоакция {id_promo} не найдена")
        return self._forecasts.list_by_promo(id_promo)


def rules_enough_history(records: list[SalesRecord]) -> bool:
    """Достаточность истории: не менее 30 уникальных дней наблюдений (ЛР8)."""
    return len({record.date for record in records}) >= rules.MIN_HISTORY_DAYS
