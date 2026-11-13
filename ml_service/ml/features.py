"""Формирование матрицы признаков для градиентного бустинга (алгоритм ЛР8).

Признаки: категориальные (магазин, категория, механика через размер скидки),
календарные (день недели, месяц) и ценовые индикаторы. Передаются в CatBoost
нативно без One-Hot кодирования (упорядоченный бустинг, ЛР8).
"""
from __future__ import annotations

from datetime import date

import pandas as pd

CATEGORICAL_FEATURES = ["id_store", "category", "store_format", "day_of_week", "month"]
NUMERIC_FEATURES = ["price", "discount_percent", "base_price_index"]
FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES
TARGET = "qty"


def history_frame(history: list[dict]) -> pd.DataFrame:
    """Исторические продажи -> DataFrame признаков с целевой переменной.

    История включает прошедшие промоакции ERP (значимые скидки), на которых
    модель обучается оценке uplift-прироста (ЛР8, алгоритм обучения).
    """
    rows = []
    for row in history:
        d = date.fromisoformat(row["date"])
        discount = float(row.get("discount_percent", 0.0))
        rows.append(
            {
                "date": d,
                "id_store": str(row["id_store"]),
                "category": row["category"],
                "store_format": row["store_format"],
                "day_of_week": str(d.weekday()),
                "month": str(d.month),
                "price": float(row["price"]),
                "discount_percent": discount,
                "base_price_index": 1 - discount / 100,
                "qty": int(row["qty"]),
            }
        )
    return pd.DataFrame(rows)


def task_frame(tasks: list[dict], promo_days: list[str],
               discount_percent: float, base_price: float) -> pd.DataFrame:
    """Матрица признаков для периода промоакции (baseline: скидка 0 %)."""
    rows = []
    for task in tasks:
        for day in promo_days:
            d = date.fromisoformat(day)
            rows.append(
                {
                    "id_store": str(task["id_store"]),
                    "category": task["category"],
                    "store_format": task["store_format"],
                    "day_of_week": str(d.weekday()),
                    "month": str(d.month),
                    "price": base_price * (1 - discount_percent / 100),
                    "discount_percent": discount_percent,
                    "base_price_index": (1 - discount_percent / 100),
                }
            )
    return pd.DataFrame(rows)
