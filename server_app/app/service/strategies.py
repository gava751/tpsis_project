"""Стратегии расчета прогноза (паттерн «Стратегия», диаграмма классов ЛР8).

Интерфейс ForecastStrategy реализуют StandardForecastStrategy и
FreshForecastStrategy: постобработка результатов ML отличается
для стандартных товаров и продукции категории «Фреш» (BR-5).
Новые стратегии добавляются без изменения ForecastService (принцип OCP).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from app.integration.ml_facade import MlForecastResult
from app.service import rules


class ForecastStrategy(ABC):
    """Постобработка прогнозных значений ML с учетом бизнес-правил."""

    @abstractmethod
    def calculate(self, prediction: MlForecastResult, pack_qty: int,
                  promo_start: date) -> tuple[int, int]:
        """Возвращает пару (baseline_qty, final_order_qty)."""


class StandardForecastStrategy(ForecastStrategy):
    """Стандартные товары: квантование по упаковке (BR-2)."""

    def calculate(self, prediction: MlForecastResult, pack_qty: int,
                  promo_start: date) -> tuple[int, int]:
        baseline = max(0, int(round(prediction.baseline_qty)))
        final_order = rules.round_to_pack(
            baseline + prediction.uplift_qty, pack_qty
        )
        return baseline, final_order


class FreshForecastStrategy(ForecastStrategy):
    """Категория «Фреш»: коэффициенты спроса дней недели (BR-5) + квантование."""

    def calculate(self, prediction: MlForecastResult, pack_qty: int,
                  promo_start: date) -> tuple[int, int]:
        adjusted = rules.apply_fresh_coefficient(
            prediction.baseline_qty + prediction.uplift_qty, promo_start.weekday()
        )
        baseline = max(0, int(round(prediction.baseline_qty)))
        return baseline, rules.round_to_pack(adjusted, pack_qty)


class ForecastStrategyResolver:
    """Выбор стратегии по товарной категории (KISS: простое сопоставление)."""

    def __init__(self) -> None:
        self._standard = StandardForecastStrategy()
        self._fresh = FreshForecastStrategy()

    def resolve(self, category: str) -> ForecastStrategy:
        return self._fresh if rules.is_fresh(category) else self._standard
