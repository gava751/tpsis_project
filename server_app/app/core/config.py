"""Конфигурация серверного приложения.

Параметры считываются из переменных окружения и файла .env
(см. .env.example в корне репозитория).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    """Единая точка доступа к настройкам приложения (принцип SRP)."""

    db_url: str = field(
        default_factory=lambda: os.getenv(
            "DB_URL",
            "mysql+pymysql://santa:santa@localhost:3306/santa_promo?charset=utf8mb4",
        )
    )
    ml_service_url: str = field(
        default_factory=lambda: os.getenv("ML_SERVICE_URL", "http://127.0.0.1:8001")
    )
    erp_base_url: str = field(
        default_factory=lambda: os.getenv("ERP_BASE_URL", "http://127.0.0.1:8002")
    )
    jwt_secret: str = field(
        default_factory=lambda: os.getenv(
            "JWT_SECRET",
            "santa-promo-predictor-development-secret-key-32b",
        )
    )
    jwt_algorithm: str = field(
        default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256")
    )
    jwt_ttl_minutes: int = field(
        default_factory=lambda: int(os.getenv("JWT_TTL_MINUTES", "60"))
    )
    # Число повторных попыток при сбое интеграции с ERP (UC-8)
    erp_retries: int = field(default_factory=lambda: int(os.getenv("ERP_RETRIES", "3")))
    erp_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("ERP_TIMEOUT", "10"))
    )


settings = Settings()
