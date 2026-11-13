"""Расчет прогноза: базовый спрос (baseline) и прирост (uplift) по модели ЛР8.

Модель дважды применяется к матрице признаков периода акции:
с фактической скидкой (promo_features) и без скидки (baseline_features).
Разница прогнозов дает ожидаемый прирост продаж от промоакции.
"""
from __future__ import annotations

import pandas as pd

from ml.features import FEATURE_COLUMNS


def forecast_task(model, task: dict, task_frame: pd.DataFrame) -> dict:
    """Прогноз для одного акционного товара в магазине на весь период акции.

    task_frame строится функцией task_frame() из ml.features для пары
    (товар, магазин) на все дни промоакции.
    """
    promo_features = task_frame.copy()
    baseline_features = task_frame.copy()
    base_price = float(task["base_price"])
    baseline_features["discount_percent"] = 0.0
    baseline_features["price"] = base_price
    baseline_features["base_price_index"] = 1.0

    promo_qty = model.predict(promo_features[FEATURE_COLUMNS])
    baseline_qty = model.predict(baseline_features[FEATURE_COLUMNS])

    baseline_total = max(0.0, float(baseline_qty.sum()))
    promo_total = max(0.0, float(promo_qty.sum()))
    uplift = promo_total - baseline_total
    return {
        "id_product": task["id_product"],
        "id_store": task["id_store"],
        "baseline_qty": int(round(baseline_total)),
        "uplift_qty": int(round(uplift)),
    }
