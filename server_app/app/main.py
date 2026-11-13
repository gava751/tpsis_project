"""Точка входа серверного приложения «Santa Promo Predictor» (FastAPI/Uvicorn).

Запуск: uvicorn app.main:app --port 8000 (из каталога server_app).
Автодокументация API: http://127.0.0.1:8000/docs (OpenAPI/Swagger).
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.controller import (
    analytics_controller,
    auth_controller,
    catalog_controller,
    forecast_controller,
    model_controller,
    promo_controller,
)
from app.core.config import BASE_DIR
from app.core.di import get_engine
from app.core.errors import AppError
from app.core.database import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server_app")

app = FastAPI(
    title="Santa Promo Predictor API",
    description="Серверная часть ПС прогнозирования продаж промоакций "
    "ООО «Санта Ритейл» (вариант 17, ЛР9)",
    version="1.0.0",
)

app.include_router(auth_controller.router)
app.include_router(promo_controller.router)
app.include_router(forecast_controller.router)
app.include_router(analytics_controller.router)
app.include_router(model_controller.router)
app.include_router(catalog_controller.router)


@app.exception_handler(AppError)
def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Единый формат ошибок бизнес-логики (DRY: один обработчик для всех слоев)."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
    )


@app.on_event("startup")
def on_startup() -> None:
    """Создание таблиц, если БД доступна (структура ЛР7)."""
    from app.model import orm  # noqa: F401 – регистрация моделей в Base.metadata

    try:
        engine = get_engine()
        Base.metadata.create_all(engine)
        logger.info("Серверное приложение запущено, база данных готова")
    except Exception as exc:  # БД может быть недоступна до завершения настройки
        logger.warning("База данных недоступна при старте: %s", exc)


@app.get("/api/v1/health", tags=["Служебные"])
def health() -> dict:
    return {"status": "ok", "service": "server_app"}


# ---------------------------------------------------------------------------
# Раздача пользовательского интерфейса (SPA React/TypeScript, ЛР6).
# Собранная сборка web_client/dist отдается тем же процессом Uvicorn,
# что позволяет демонстрировать систему без отдельного веб-сервера.
_web_dist = BASE_DIR / "web_client" / "dist"
if _web_dist.exists():
    assets = _web_dist / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_entry(full_path: str) -> FileResponse:
        """SPA-маршрутизация: неизвестные пути отдают index.html (client-side routing)."""
        candidate = _web_dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_web_dist / "index.html")
