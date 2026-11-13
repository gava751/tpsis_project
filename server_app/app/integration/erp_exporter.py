"""Экспорт утвержденных заказов в ERP-систему (UC-9 «Экспортировать заказы»)."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.integration.erp_gateway import ErpGateway
from app.dto.forecast_schemas import ExportResultRow

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExportRow:
    id_product: int
    id_store: int
    final_order_qty: int


class ErpExporter(ABC):
    @abstractmethod
    def export(self, id_promo: int, rows: list[ExportRow]) -> list[ExportResultRow]: ...


class HttpErpExporter(ErpExporter):
    """Передает утвержденные объемы в ERP методом POST и разбирает построчные статусы."""

    def __init__(self, gateway: ErpGateway) -> None:
        self._gateway = gateway

    def export(self, id_promo: int, rows: list[ExportRow]) -> list[ExportResultRow]:
        if not rows:
            return []
        response = self._gateway.send_orders(
            {
                "id_promo": id_promo,
                "orders": [
                    {
                        "id_product": row.id_product,
                        "id_store": row.id_store,
                        "qty": row.final_order_qty,
                    }
                    for row in rows
                ],
            }
        )
        results: list[ExportResultRow] = []
        for item in response.get("results", []):
            results.append(
                ExportResultRow(
                    id_product=item["id_product"],
                    id_store=item["id_store"],
                    final_order_qty=item["qty"],
                    erp_status=item["status"],
                    reason=item.get("reason"),
                )
            )
        failed = [r for r in results if r.erp_status != "OK"]
        if failed:
            logger.warning(
                "Экспорт заказа промоакции %d: %d строк с ошибкой ERP",
                id_promo, len(failed),
            )
        return results
