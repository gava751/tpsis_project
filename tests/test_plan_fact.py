"""Тесты отчета план-факт (UC-6, метрики MAPE/WAPE)."""
from __future__ import annotations

from datetime import date, timedelta

from app.model.orm import ForecastResult, Product, PromoCampaign, PromoProduct
from tests.conftest import future_promo_payload


def _seed_completed_promo(engine) -> int:
    """Завершенная акция с экспортированными объемами (входное условие UC-6)."""
    from sqlalchemy.orm import sessionmaker

    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with factory() as session:
        promo = PromoCampaign(
            promo_name="Завершенная акция",
            start_date=date.today() - timedelta(days=40),
            end_date=date.today() - timedelta(days=25),
            status="APPROVED",
        )
        session.add(promo)
        session.flush()
        product = session.get(Product, 2001)
        pp = PromoProduct(id_promo=promo.id_promo, id_product=product.id_product,
                          discount_percent=25.0)
        session.add(pp)
        session.flush()
        for id_store in (1, 2, 3):
            session.add(ForecastResult(
                id_promo_prod=pp.id_promo_prod,
                id_store=id_store,
                baseline_qty=60,
                uplift_qty=40,
                final_order_qty=102,
                status="EXPORTED",
            ))
        session.commit()
        return promo.id_promo


def test_plan_fact_metrics(client, auth_headers, engine):
    id_promo = _seed_completed_promo(engine)
    response = client.get(f"/api/v1/promos/{id_promo}/plan-fact",
                          headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["rows"]) == 3
    row = body["rows"][0]
    # план 102, факт 100 -> отклонение -2 шт.
    assert row["plan_qty"] == 102
    assert row["fact_qty"] == 100
    assert row["deviation_qty"] == -2
    assert body["metrics"]["mape"] > 0
    assert body["metrics"]["wape"] > 0


def test_plan_fact_rejected_for_running_promo(client, auth_headers):
    response = client.post("/api/v1/promos", json=future_promo_payload(),
                           headers=auth_headers)
    id_promo = response.json()["id_promo"]
    response = client.get(f"/api/v1/promos/{id_promo}/plan-fact",
                          headers=auth_headers)
    assert response.status_code == 409
