"""Общая конфигурация pytest: приложение с изолированной БД и фейковыми интеграциями.

Интеграционные компоненты (ERP, ML-сервис) заменяются тестовыми двойниками
через dependency_overrides – проверяется только бизнес-логика серверного слоя.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server_app"))

from app.core.database import Base, make_session_factory  # noqa: E402
from app.main import app  # noqa: E402
from app.core.di import (  # noqa: E402
    get_erp_exporter,
    get_erp_gateway,
    get_ml_facade,
    get_session,
)
from app.integration.erp_exporter import ErpExporter  # noqa: E402
from app.dto.forecast_schemas import ExportResultRow  # noqa: E402
from app.integration.erp_gateway import ErpGateway, FactRecord, SalesRecord  # noqa: E402
from app.integration.ml_facade import (  # noqa: E402
    ForecastTaskRow,
    HistoryRow,
    MlForecastResult,
    MlServiceFacade,
)
from app.model.orm import Product, Store  # noqa: E402


class FakeErpGateway(ErpGateway):
    """Тестовый двойник ERP: история за 90 дней, детерминированный факт."""

    def __init__(self, history_days: int = 90) -> None:
        self.history_days = history_days

    def get_history(self, id_products, date_from, date_to) -> list[SalesRecord]:
        end = min(date_to, date.today())
        start = end - timedelta(days=self.history_days)
        records = []
        for id_product in id_products:
            for id_store in (1, 2, 3):
                for i in range(self.history_days):
                    day = start + timedelta(days=i)
                    records.append(
                        SalesRecord(date=day, id_product=id_product,
                                    id_store=id_store, qty=10, price=5.0)
                    )
        return records

    def get_fact(self, id_promo, id_products, date_from, date_to) -> list[FactRecord]:
        return [
            FactRecord(id_product=p, id_store=s, fact_qty=100)
            for p in id_products
            for s in (1, 2, 3)
        ]

    def send_orders(self, payload: dict) -> dict:
        return {
            "results": [
                {"id_product": o["id_product"], "id_store": o["id_store"],
                 "qty": o["qty"], "status": "OK", "reason": None}
                for o in payload["orders"]
            ]
        }


class FakeMlFacade(MlServiceFacade):
    """Тестовый двойник ML-сервиса: фиксированные baseline/uplift по категории."""

    def request_forecast(self, history, tasks: list[ForecastTaskRow]):
        results = []
        for task in tasks:
            if task.category == "Фреш":
                baseline, uplift = 100, 50
            else:
                baseline, uplift = 60, 40
            results.append(MlForecastResult(
                id_product=task.id_product,
                id_store=task.id_store,
                baseline_qty=baseline,
                uplift_qty=uplift,
            ))
        return results

    def train_model(self, category, category_weights):
        raise NotImplementedError("Не используется в тестах")


class FakeErpExporter(ErpExporter):
    def export(self, id_promo, rows) -> list[ExportResultRow]:
        return [
            ExportResultRow(id_product=r.id_product, id_store=r.id_store,
                            final_order_qty=r.final_order_qty, erp_status="OK")
            for r in rows
        ]


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as session:
        # Справочники (аналог seed.py)
        session.add_all([
            Product(id_product=1001, name="Молоко 2,5%", category="Фреш",
                    base_price=2.49, pack_qty=12),
            Product(id_product=2001, name="Кофе растворимый", category="Бакалея",
                    base_price=18.90, pack_qty=6),
            Product(id_product=3001, name="Шоколад «Белый парус»",
                    category="Кондитерские изделия", base_price=3.05, pack_qty=24),
            Store(id_store=1, address="г. Минск, пр-т Независимости, 58",
                  format="Супермаркет"),
            Store(id_store=2, address="г. Минск, ул. Платонова, 22",
                  format="Магазин у дома"),
            Store(id_store=3, address="г. Брест, ул. Московская, 151",
                  format="Супермаркет"),
        ])
        session.commit()
    yield engine


@pytest.fixture()
def client(engine, monkeypatch):
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    def override_session():
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_erp_gateway] = lambda: FakeErpGateway()
    app.dependency_overrides[get_ml_facade] = lambda: FakeMlFacade()
    app.dependency_overrides[get_erp_exporter] = lambda: FakeErpExporter()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def manager_token(client) -> str:
    response = client.post(
        "/api/v1/auth/login", json={"login": "manager", "password": "manager"}
    )
    return response.json()["access_token"]


@pytest.fixture()
def analyst_token(client) -> str:
    response = client.post(
        "/api/v1/auth/login", json={"login": "analyst", "password": "analyst"}
    )
    return response.json()["access_token"]


@pytest.fixture()
def auth_headers(manager_token) -> dict:
    return {"Authorization": f"Bearer {manager_token}"}


@pytest.fixture()
def analyst_headers(analyst_token) -> dict:
    return {"Authorization": f"Bearer {analyst_token}"}


def future_promo_payload(id_product: int = 2001, discount: float = 20.0) -> dict:
    """Корректная промоакция: старт через 30 дней, 14 дней длительности (BR-1)."""
    start = date.today() + timedelta(days=30)
    return {
        "promo_name": "Тестовая акция",
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=14)).isoformat(),
        "products": [{"id_product": id_product, "discount_percent": discount}],
    }
