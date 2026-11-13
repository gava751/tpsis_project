"""Тесты валидации параметров промоакции (UC-2, BR-1, BR-4)."""
from __future__ import annotations

from datetime import date, timedelta

from tests.conftest import future_promo_payload


def test_create_promo_success(client, auth_headers):
    response = client.post("/api/v1/promos",
                           json=future_promo_payload(), headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "DRAFT"
    assert body["products"][0]["discount_percent"] == 20.0


def test_create_promo_start_too_soon_br1(client, auth_headers):
    """FR2-1: дата начала менее чем через 14 дней нарушает BR-1."""
    payload = future_promo_payload()
    payload["start_date"] = (date.today() + timedelta(days=5)).isoformat()
    payload["end_date"] = (date.today() + timedelta(days=19)).isoformat()
    response = client.post("/api/v1/promos", json=payload, headers=auth_headers)
    assert response.status_code == 400
    assert "BR-1" in response.json()["message"]


def test_create_promo_end_before_start(client, auth_headers):
    payload = future_promo_payload()
    payload["end_date"] = payload["start_date"]
    response = client.post("/api/v1/promos", json=payload, headers=auth_headers)
    assert response.status_code == 400


def test_create_promo_discount_over_limit_br4(client, auth_headers):
    """FR2-2: скидка более 50 % отклоняется (BR-4)."""
    response = client.post(
        "/api/v1/promos",
        json=future_promo_payload(discount=60.0),
        headers=auth_headers,
    )
    assert response.status_code == 422  # отклонено на границе DTO (le=50)


def test_promo_requires_auth(client):
    response = client.post("/api/v1/promos", json=future_promo_payload())
    assert response.status_code == 401
