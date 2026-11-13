"""Доменные ошибки приложения и их отображение в HTTP-ответы."""
from __future__ import annotations


class AppError(Exception):
    """Базовая ошибка бизнес-логики с HTTP-кодом и диагностическим кодом."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class ValidationError(AppError):
    """Нарушение бизнес-правил при вводе данных (BR-1, BR-4)."""

    def __init__(self, message: str) -> None:
        super().__init__(400, "VALIDATION_ERROR", message)


class NotAuthenticatedError(AppError):
    def __init__(self, message: str = "Не авторизован") -> None:
        super().__init__(401, "NOT_AUTHENTICATED", message)


class AccessDeniedError(AppError):
    def __init__(self, message: str = "Доступ запрещен") -> None:
        super().__init__(403, "ACCESS_DENIED", message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Объект не найден") -> None:
        super().__init__(404, "NOT_FOUND", message)


class InsufficientHistoryError(AppError):
    """Недостаточно истории продаж для прогноза (товар-новинка, BR-3, FR3-2)."""

    def __init__(self, message: str = "Недостаточно данных для расчета прогноза") -> None:
        super().__init__(409, "INSUFFICIENT_HISTORY", message)


class ConflictError(AppError):
    """Конфликт состояния (например, корректировка утвержденного прогноза)."""

    def __init__(self, message: str) -> None:
        super().__init__(409, "CONFLICT", message)


class IntegrationError(AppError):
    """Сбой внешней интеграции (ERP или ML-сервис)."""

    def __init__(self, message: str = "Ошибка внешнего сервиса") -> None:
        super().__init__(503, "INTEGRATION_ERROR", message)
