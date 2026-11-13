"""Бизнес-правила предметной области (BR-1…BR-5, отчет ЛР1, таблица 2.4).

Правила изолированы в отдельном модуле (принцип DRY): используются
и при валидации ввода (UC-2), и при постобработке результатов ML (UC-3).
"""
from __future__ import annotations

import math
from datetime import date, timedelta

from app.core.errors import ValidationError

FRESH_CATEGORY = "Фреш"
MIN_DAYS_BEFORE_START = 14      # BR-1: прогноз утвержден не позднее, чем за 14 дней
MAX_DISCOUNT_PERCENT = 50.0     # BR-4: скидка не более 50 %
MIN_HISTORY_DAYS = 30           # порог достаточности истории продаж (ЛР8)
FRESH_DAY_COEFFICIENTS = {      # BR-5: коэффициенты спроса по дням недели (0=Пн)
    0: 1.05, 1: 0.95, 2: 0.90, 3: 0.92, 4: 1.10, 5: 1.30, 6: 1.15,
}


def validate_promo_dates(start_date: date, end_date: date, today: date) -> None:
    """FR2-1: дата начала – не менее чем на 14 дней позже текущей (BR-1)."""
    if end_date <= start_date:
        raise ValidationError("Дата окончания акции должна быть позже даты начала")
    if start_date < today + timedelta(days=MIN_DAYS_BEFORE_START):
        raise ValidationError(
            "Промоакция должна быть запланирована не менее чем за "
            f"{MIN_DAYS_BEFORE_START} дней до начала (бизнес-правило BR-1)"
        )


def validate_discount(discount_percent: float) -> None:
    """FR2-2: предупреждение о превышении лимита скидки 50 % (BR-4)."""
    if discount_percent > MAX_DISCOUNT_PERCENT:
        raise ValidationError(
            f"Скидка {discount_percent}% превышает маркетинговый лимит "
            f"{MAX_DISCOUNT_PERCENT}% (бизнес-правило BR-4)"
        )


def is_fresh(category: str) -> bool:
    """Товары категории «Фреш» (срок годности < 7 суток, BR-5)."""
    return category.strip().lower() == FRESH_CATEGORY.lower()


def round_to_pack(qty: float, pack_qty: int) -> int:
    """BR-2: объем заказа кратен упаковке поставщика, округление вверх."""
    if pack_qty <= 1:
        return max(0, int(math.ceil(qty)))
    packs = math.ceil(max(0, qty) / pack_qty)
    return int(packs * pack_qty)


def apply_fresh_coefficient(baseline_qty: float, weekday: int) -> float:
    """BR-5: пересчет объема с учетом коэффициента спроса дня недели."""
    return baseline_qty * FRESH_DAY_COEFFICIENTS.get(weekday % 7, 1.0)


def correction_reasons() -> list[str]:
    """Допустимые причины ручной корректировки (UC-4, шаг 3)."""
    return ["ограничение склада", "риск недовоза", "ожидание сверхспроса"]
