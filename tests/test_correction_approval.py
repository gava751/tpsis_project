"""Тесты корректировки (UC-4), утверждения и экспорта (UC-5, UC-9)."""
from __future__ import annotations

from datetime import date, timedelta

from tests.conftest import future_promo_payload


def _prepare_calculated(client, headers) -> int:
    response = client.post("/api/v1/promos", json=future_promo_payload(),
                           headers=headers)
    id_promo = response.json()["id_promo"]
    response = client.post(f"/api/v1/promos/{id_promo}/forecast",
                           json={}, headers=headers)
    assert response.status_code == 200
    return id_promo


def test_correction_requires_reason(client, auth_headers):
    """UC-4, альтернативный поток: без причины сохранение блокируется."""
    id_promo = _prepare_calculated(client, auth_headers)
    rows = client.get(f"/api/v1/promos/{id_promo}/forecast",
                      headers=auth_headers).json()["rows"]
    response = client.put(
        "/api/v1/forecasts/corrections",
        json={"corrections": [{"id_forecast": rows[0]["id_forecast"],
                               "final_order_qty": 120}]},
        headers=auth_headers,
    )
    assert response.status_code == 422  # причина отсутствует (min_length=1)


def test_correction_with_reason(client, auth_headers):
    id_promo = _prepare_calculated(client, auth_headers)
    rows = client.get(f"/api/v1/promos/{id_promo}/forecast",
                      headers=auth_headers).json()["rows"]
    response = client.put(
        "/api/v1/forecasts/corrections",
        json={"corrections": [{"id_forecast": rows[0]["id_forecast"],
                               "final_order_qty": 120,
                               "correction_reason": "ограничение склада"}]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    row = response.json()["rows"][0]
    assert row["status"] == "CORRECTED"
    assert row["is_corrected"] is True
    assert row["final_order_qty"] == 120


def test_correction_rejects_free_text_reason(client, auth_headers):
    id_promo = _prepare_calculated(client, auth_headers)
    rows = client.get(f"/api/v1/promos/{id_promo}/forecast",
                      headers=auth_headers).json()["rows"]
    response = client.put(
        "/api/v1/forecasts/corrections",
        json={"corrections": [{"id_forecast": rows[0]["id_forecast"],
                               "final_order_qty": 120,
                               "correction_reason": "просто так"}]},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_approval_exports_to_erp(client, auth_headers):
    """UC-5: утверждение -> статус акции «Утверждена» -> include UC-9."""
    id_promo = _prepare_calculated(client, auth_headers)
    response = client.post(
        f"/api/v1/promos/{id_promo}/approval",
        json={"confirmed": True},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["promo_status"] == "APPROVED"
    assert all(row["erp_status"] == "OK" for row in body["rows"])

    rows = client.get(f"/api/v1/promos/{id_promo}/forecast",
                      headers=auth_headers).json()["rows"]
    assert all(row["status"] == "EXPORTED" for row in rows)

    # Повторное утверждение невозможно (альтернативный поток UC-5)
    second = client.post(f"/api/v1/promos/{id_promo}/approval",
                         json={"confirmed": True}, headers=auth_headers)
    assert second.status_code == 409


def test_approval_declined(client, auth_headers):
    """UC-5, альтернативный поток: пользователь отменяет подтверждение."""
    id_promo = _prepare_calculated(client, auth_headers)
    response = client.post(f"/api/v1/promos/{id_promo}/approval",
                           json={"confirmed": False}, headers=auth_headers)
    assert response.status_code == 409
    rows = client.get(f"/api/v1/promos/{id_promo}/forecast",
                      headers=auth_headers).json()["rows"]
    assert rows[0]["status"] == "CALCULATED"
