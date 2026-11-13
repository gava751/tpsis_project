"""Контейнер внедрения зависимостей (шаблон DI).

FastAPI-зависимости собирают граф объектов приложения: контроллеры
получают готовые сервисы, сервисы – абстрактные репозитории и шлюзы.
Изменение провайдера данных не затрагивает бизнес-логику.
"""
from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import create_engine_from_url, make_session_factory
from app.integration.erp_exporter import ErpExporter, HttpErpExporter
from app.integration.erp_gateway import ErpGateway, HttpErpGateway
from app.integration.ml_facade import MlServiceFacade, HttpMlServiceFacade
from app.repository.interfaces import (
    CatalogRepository,
    DateTimeProvider,
    ForecastRepository,
    PromoRepository,
)
from app.repository.sqlalchemy_impl import (
    SqlAlchemyCatalogRepository,
    SqlAlchemyForecastRepository,
    SqlAlchemyPromoRepository,
    SystemDateTimeProvider,
)
from app.service.forecast_service import ForecastService
from app.service.model_service import HttpMlModelRegistryClient, ModelService
from app.service.notifications import NotificationService
from app.service.plan_fact_service import PlanFactService
from app.service.promo_service import PromoService

_engine = None
_session_factory = None
_notifications = NotificationService()


def get_engine():
    global _engine, _session_factory
    if _engine is None:
        _engine = create_engine_from_url()
        _session_factory = make_session_factory(_engine)
    return _engine


def get_session() -> Iterator[Session]:
    """Сессия БД на время обработки запроса (Unit of Work на запрос)."""
    get_engine()
    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# --- репозитории -------------------------------------------------------

def get_promo_repository(session: Session = Depends(get_session)) -> PromoRepository:
    return SqlAlchemyPromoRepository(session)


def get_catalog_repository(session: Session = Depends(get_session)) -> CatalogRepository:
    return SqlAlchemyCatalogRepository(session)


def get_forecast_repository(session: Session = Depends(get_session)) -> ForecastRepository:
    return SqlAlchemyForecastRepository(session)


def get_clock() -> DateTimeProvider:
    return SystemDateTimeProvider()


def get_notification_service() -> NotificationService:
    return _notifications


# --- интеграции --------------------------------------------------------

def get_erp_gateway() -> ErpGateway:
    return HttpErpGateway()


def get_ml_facade() -> MlServiceFacade:
    return HttpMlServiceFacade()


def get_erp_exporter(gateway: ErpGateway = Depends(get_erp_gateway)) -> ErpExporter:
    return HttpErpExporter(gateway)


# --- сервисы -----------------------------------------------------------

def get_promo_service(
    promos: PromoRepository = Depends(get_promo_repository),
    catalogs: CatalogRepository = Depends(get_catalog_repository),
    clock: DateTimeProvider = Depends(get_clock),
) -> PromoService:
    return PromoService(promos, catalogs, clock)


def get_forecast_service(
    session: Session = Depends(get_session),
    promos: PromoRepository = Depends(get_promo_repository),
    forecasts: ForecastRepository = Depends(get_forecast_repository),
    catalogs: CatalogRepository = Depends(get_catalog_repository),
    erp: ErpGateway = Depends(get_erp_gateway),
    ml_facade: MlServiceFacade = Depends(get_ml_facade),
    exporter: ErpExporter = Depends(get_erp_exporter),
    clock: DateTimeProvider = Depends(get_clock),
    notifications: NotificationService = Depends(get_notification_service),
) -> ForecastService:
    return ForecastService(
        session, promos, forecasts, catalogs, erp, ml_facade,
        exporter, clock, notifications,
    )


def get_plan_fact_service(
    session: Session = Depends(get_session),
    promos: PromoRepository = Depends(get_promo_repository),
    forecasts: ForecastRepository = Depends(get_forecast_repository),
    catalogs: CatalogRepository = Depends(get_catalog_repository),
    erp: ErpGateway = Depends(get_erp_gateway),
    clock: DateTimeProvider = Depends(get_clock),
) -> PlanFactService:
    return PlanFactService(promos, forecasts, catalogs, erp, clock, session)


def get_model_service(
    ml_facade: MlServiceFacade = Depends(get_ml_facade),
) -> ModelService:
    return ModelService(ml_facade, HttpMlModelRegistryClient(ml_facade))
