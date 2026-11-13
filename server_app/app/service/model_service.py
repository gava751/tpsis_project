"""Сервис управления ML-моделями (UC-7 «Настроить ML-модели»).

Проксирует запросы панели аналитика в ML-сервис через фасад
(изменение весов признаков, backtesting, выбор активной версии).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.dto.model_schemas import ModelInfoResponse, TrainRequest, TrainResponse
from app.integration.ml_facade import MlServiceFacade


class MlModelRegistryClient(ABC):
    """Источник сведений о версиях моделей (зависит от ML-сервиса)."""

    @abstractmethod
    def list_models(self) -> list[ModelInfoResponse]: ...


class HttpMlModelRegistryClient(MlModelRegistryClient):
    def __init__(self, facade: MlServiceFacade) -> None:
        self._facade = facade

    def list_models(self) -> list[ModelInfoResponse]:
        # Делегирование фасаду исключает прямые зависимости контроллера от HTTP
        import httpx

        from app.core.config import settings
        from app.core.errors import IntegrationError
        try:
            response = httpx.get(
                f"{settings.ml_service_url.rstrip('/')}/models", timeout=30
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise IntegrationError("ML-сервис недоступен")
        return [
            ModelInfoResponse(**item)
            for item in response.json()["models"]
        ]


class ModelService:
    """Управление моделями машинного обучения (роль «Аналитик»)."""

    def __init__(self, facade: MlServiceFacade,
                 registry: MlModelRegistryClient) -> None:
        self._facade = facade
        self._registry = registry

    def train(self, request: TrainRequest) -> TrainResponse:
        """UC-7, шаги 3–6: тестовое обучение с новыми весами и метриками точности."""
        result = self._facade.train_model(request.category, request.category_weights)
        return TrainResponse(
            version=result.version,
            trained_at=result.trained_at,
            category=result.category,
            mape=result.mape,
            wape=result.wape,
            activated=True,
        )

    def list_models(self) -> list[ModelInfoResponse]:
        return self._registry.list_models()
