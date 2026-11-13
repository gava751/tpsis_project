"""Обучение модели градиентного бустинга CatBoost (алгоритм ЛР8).

Гиперпараметры зафиксированы при проектировании: 1200 деревьев,
скорость обучения 0,05, глубина 8, ранняя остановка на 50 итерациях.
Метрика качества – MAPE на валидационной выборке (backtesting).
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.metrics import mean_absolute_percentage_error

from ml.features import CATEGORICAL_FEATURES, FEATURE_COLUMNS, TARGET
from ml.registry import ModelMeta, ModelRegistry

logger = logging.getLogger(__name__)


def _make_model() -> CatBoostRegressor:
    return CatBoostRegressor(
        iterations=1200,
        learning_rate=0.05,
        depth=8,
        loss_function="RMSE",
        cat_features=CATEGORICAL_FEATURES,
        verbose=False,
    )


def _backtest_split(frame: pd.DataFrame, validation_fraction: float = 0.2):
    """Хронологическое разбиение: последние 20 % дат – валидация."""
    dates = sorted(frame["date"].unique())
    cutoff = dates[int(len(dates) * (1 - validation_fraction))]
    train = frame[frame["date"] < cutoff]
    validation = frame[frame["date"] >= cutoff]
    return train, validation


def train_model(frame: pd.DataFrame, registry: ModelRegistry,
                category: str | None = None,
                category_weights: dict[str, float] | None = None) -> ModelMeta:
    """Шаги 3–5 алгоритма обучения (ЛР8) с учетом весов категорий (UC-7)."""
    if len(frame) < 30:
        raise ValueError("Недостаточно исторических данных для обучения модели")

    train, validation = _backtest_split(frame)
    weights = None
    if category_weights:
        weights = np.array(
            [
                category_weights.get(row_category, 1.0)
                for row_category in train["category"]
            ],
            dtype=float,
        )

    model = _make_model()
    model.fit(
        train[FEATURE_COLUMNS],
        train[TARGET],
        sample_weight=weights,
        eval_set=(validation[FEATURE_COLUMNS], validation[TARGET]),
        early_stopping_rounds=50,
    )

    predictions = model.predict(validation[FEATURE_COLUMNS])
    y_true = validation[TARGET].to_numpy(dtype=float)
    nonzero = y_true > 0
    mape = float(mean_absolute_percentage_error(y_true[nonzero],
                                                predictions[nonzero]))
    wape = float(np.abs(y_true - predictions).sum() / max(y_true.sum(), 1e-9))

    meta = ModelMeta(
        version=f"v{pd.Timestamp.utcnow().strftime('%Y%m%d%H%M%S')}",
        trained_at=pd.Timestamp.utcnow().isoformat(timespec="seconds"),
        category=category,
        mape=round(mape, 4),
        wape=round(wape, 4),
        iterations=int(model.get_param("iterations")),
    )
    registry.save(model, meta)
    logger.info("Обучена модель %s: MAPE=%.4f, WAPE=%.4f", meta.version, mape, wape)
    return meta
