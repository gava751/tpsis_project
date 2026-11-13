"""Тесты сквозного потока расчета прогноза (UC-3, BR-2, BR-3, BR-5)."""
from __future__ import annotations

from datetime import date, timedelta

from app.core.di import get_erp_gateway
from tests.conftest import FakeErpGateway, future_promo_payload


def _create_promo(client, headers, **kwargs) -> int:
    response = client.post("/api/v1/promos",
                           json=future_promo_payload(**kwargs), headers=headers)
    assert response.status_code == 201
    return response.json()["id_promo"]


def test_forecast_applies_pack_quantum_br2(client, auth_headers):
    """FR3-5: итоговый объем кратен упаковке поставщика (BR-2)."""
    id_promo = _create_promo(client, auth_headers, id_product=2001)  # pack_qty=6
    response = client.post(
        f"/api/v1/promos/{id_promo}/forecast", json={}, headers=auth_headers
    )
    assert response.status_code == 200
    rows = response.json()["rows"]
    assert rows, "Ожидаются строки прогноза по трем магазинам"
    for row in rows:
        assert row["status"] == "CALCULATED"
        assert row["final_order_qty"] % 6 == 0
        # baseline=60, uplift=40 -> 100 округляется вверх до 102 (17 упаковок)
        assert row["final_order_qty"] == 102
        assert row["baseline_qty"] == 60


def test_forecast_fresh_uses_weekday_coefficient_br5(client, auth_headers):
    """FR3-4: для категории «Фреш» применяются коэффициенты дней недели (BR-5)."""
    id_promo = _create_promo(client, auth_headers, id_product=1001)  # Фреш, pack 12
    start = date.today() + timedelta(days=30)
    response = client.post(
        f"/api/v1/promos/{id_promo}/forecast", json={}, headers=auth_headers
    )
    rows = response.json()["rows"]
    assert rows[0]["status"] == "CALCULATED"
    coefficient = {0: 1.05, 1: 0.95, 2: 0.90, 3: 0.92, 4: 1.10, 5: 1.30, 6: 1.15}[
        start.weekday()
    ]
    expected = int(-(-int((100 + 50) * coefficient) // 12)) * 12  # ceil-округление
    assert rows[0]["final_order_qty"] == expected


def test_forecast_new_product_requires_analog_br3(client, auth_headers):
    """FR3-2: при недостаточной истории возвращается 409 и запрос аналога."""
    from app.main import app

    app.dependency_overrides[get_erp_gateway] = lambda: FakeErpGateway(
        history_days=10
    )
    id_promo = _create_promo(client, auth_headers, id_product=2001)
    response = client.post(
        f"/api/v1/promos/{id_promo}/forecast", json={}, headers=auth_headers
    )
    assert response.status_code == 409
    assert response.json()["code"] == "INSUFFICIENT_HISTORY"


def test_forecast_with_analog_succeeds(client, auth_headers):
    """BR-3: прогноз по новинке рассчитывается по данным товара-аналога."""
    from app.core.di import get_erp_gateway
    from app.main import app

    app.dependency_overrides[get_erp_gateway] = lambda: FakeErpGateway(
        history_days=10
    )
    id_promo = _create_promo(client, auth_headers, id_product=2001)
    response = client.post(
        f"/api/v1/promos/{id_promo}/forecast",
        json={"analog_products": {"2001": 1001}},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["rows"][0]["status"] == "CALCULATED"


def test_recalculation_replaces_rows(client, auth_headers):
    """Повторный запуск UC-3 заменяет строки прогноза (переход Ошибка→Расчет, ЛР8).

    Примечание: SQLite переиспользует идентификаторы после удаления строк,
    поэтому проверяется состав и статус набора, а не значения идентификаторов.
    """
    id_promo = _create_promo(client, auth_headers, id_product=2001)
    first = client.post(f"/api/v1/promos/{id_promo}/forecast",
                        json={}, headers=auth_headers).json()
    second = client.post(f"/api/v1/promos/{id_promo}/forecast",
                         json={}, headers=auth_headers).json()
    assert len(second["rows"]) == len(first["rows"])
    assert all(row["status"] == "CALCULATED" for row in second["rows"])
