"""ML-сервис «Santa Promo Predictor» (FastAPI + CatBoost).

Вычислительное ядро системы: обучение модели (backtesting, UC-7) и расчет
базового спроса и uplift-прироста (UC-3). Развертывается на выделенном
ML-узле (диаграмма развертывания, ЛР8).

Запуск: uvicorn main:app --port 8001 (из каталога ml_service).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Request

from ml.features import history_frame, task_frame
from ml.forecaster import forecast_task
from ml.registry import ModelRegistry
from ml.trainer import train_model
from schemas import (
    ForecastRequest,
    ForecastResponse,
    ModelsResponse,
    TrainRequest,
    TrainResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ml_service")

REGISTRY_DIR = Path(
    os.getenv("MODEL_REGISTRY_DIR", Path(__file__).resolve().parent / "models")
)
# Кэш исторических данных, переданных серверным приложением (UC-3, шаг 3)
HISTORY_CACHE = REGISTRY_DIR / "history_cache.csv"

app = FastAPI(
    title="Santa Promo Predictor ML Service",
    description="Вычислительное ядро прогнозирования продаж промоакций",
    version="1.0.0",
)

registry = ModelRegistry(REGISTRY_DIR)


def _cached_history() -> pd.DataFrame | None:
    if not HISTORY_CACHE.exists():
        return None
    frame = pd.read_csv(HISTORY_CACHE)
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    return frame


@app.get("/health")
def health() -> dict:
    meta = registry.latest_meta()
    return {
        "status": "ok",
        "service": "ml_service",
        "active_model": meta.version if meta else None,
    }


@app.post("/forecast", response_model=ForecastResponse)
def forecast(request: ForecastRequest) -> ForecastResponse:
    """Расчет baseline и uplift для акционных товаров по всем магазинам."""
    frame = history_frame([row.model_dump() for row in request.history])

    # Кэширование истории для последующего обучения (UC-7)
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(HISTORY_CACHE, index=False)

    model = registry.load_latest()
    meta = registry.latest_meta()
    if model is None or meta.trained_rows != len(frame):
        # Модель отсутствует либо состав исторических данных изменился
        # (появились новые товары/категории) – выполняется дообучение
        logger.info("Обучение модели на %d строках истории", len(frame))
        meta = train_model(frame, registry)
        logger.info("Обучена модель %s (MAPE=%.4f)", meta.version, meta.mape)
        model = registry.load_latest()

    results = []
    for task_row in request.tasks:
        task = task_row.model_dump()
        features = task_frame(
            [task], task["promo_days"],
            task["discount_percent"], task["base_price"],
        )
        results.append(forecast_task(model, task, features))
    return ForecastResponse(results=results)


@app.post("/train", response_model=TrainResponse)
def train(request: TrainRequest) -> TrainResponse:
    """UC-7, шаг 4: тестовое обучение модели на накопленной истории."""
    frame = _cached_history()
    if frame is None or len(frame) == 0:
        raise HTTPException(
            status_code=409,
            detail="Исторические данные отсутствуют: сначала выполните расчет прогноза",
        )
    if request.category:
        frame = frame[frame["category"] == request.category]
        if len(frame) < 30:
            raise HTTPException(
                status_code=409,
                detail=f"Недостаточно данных категории «{request.category}»",
            )
    try:
        meta = train_model(frame, registry, request.category, request.category_weights)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return TrainResponse(
        version=meta.version,
        trained_at=meta.trained_at,
        category=meta.category,
        mape=meta.mape,
        wape=meta.wape,
    )


@app.get("/models", response_model=ModelsResponse)
def models() -> ModelsResponse:
    """Панель управления моделями (UC-7, шаг 1): версии и метрики точности."""
    return ModelsResponse(
        models=[
            {
                "version": m.version,
                "trained_at": m.trained_at,
                "category": m.category,
                "mape": m.mape,
                "wape": m.wape,
            }
            for m in registry.list_meta()
        ]
    )
