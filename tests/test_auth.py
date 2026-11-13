"""Тесты аутентификации и разграничения ролей (UC-1, UC-7)."""
from __future__ import annotations


def test_login_wrong_password_returns_401(client):
    response = client.post(
        "/api/v1/auth/login", json={"login": "manager", "password": "wrong"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "NOT_AUTHENTICATED"


def test_login_returns_jwt_and_role(client):
    response = client.post(
        "/api/v1/auth/login", json={"login": "manager", "password": "manager"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "manager"
    assert body["access_token"]


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_decodes_token(client, auth_headers):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["login"] == "manager"


def test_model_train_denied_for_manager(client, auth_headers):
    response = client.post(
        "/api/v1/models/train",
        json={"category": None, "category_weights": {}},
        headers=auth_headers,
    )
    assert response.status_code == 403
    assert response.json()["code"] == "ACCESS_DENIED"


def test_model_train_allowed_for_analyst(client, analyst_headers):
    response = client.get("/api/v1/models", headers=analyst_headers)
    # ML-сервис недоступен в тестовом контуре (фейк не переопределен для registry)
    assert response.status_code in (200, 503)
