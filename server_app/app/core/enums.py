"""Доменные перечисления, отражающие жизненный цикл объектов системы.

ForecastStatus соответствует диаграмме состояний объекта «Прогноз» (ЛР8),
PromoStatus — статусам промоакции (UC-2 «Черновик», UC-5 «Утверждена»).
"""
from __future__ import annotations

from enum import Enum


class ForecastStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    CALCULATED = "CALCULATED"
    CORRECTED = "CORRECTED"
    APPROVED = "APPROVED"
    EXPORTED = "EXPORTED"
    ERROR = "ERROR"


class PromoStatus(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"


class Role(str, Enum):
    MANAGER = "manager"      # Категорийный менеджер
    ANALYST = "analyst"      # Руководитель отдела аналитики
