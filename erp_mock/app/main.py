"""Заглушка корпоративной ERP-системы «Santa Promo Predictor».

Эмулирует контракт интеграции реальной ERP: выгрузка чековой истории
за 3 года (UC-8), фактических продаж (UC-6) и прием утвержденных заказов
(UC-9). Данные генерируются детерминированно ( seeded RNG) – результаты
воспроизводимы при повторных запусках.

Запуск: uvicorn app.main:app --port 8002 (из каталога erp_mock).
"""
from __future__ import annotations

import logging
import random
from datetime import date, timedelta

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.catalog import BLOCKED_PRODUCTS, PRODUCTS, STORES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("erp_mock")

app = FastAPI(
    title="ERP Mock Service",
    description="Заглушка ERP-системы ООО «Санта Ритейл» для лабораторного контура",
    version="1.0.0",
)

_HISTORY_DAYS_LIMIT = 365 * 3


class HistoryRequest(BaseModel):
    id_products: list[int] = Field(min_length=1)
    date_from: date
    date_to: date


class FactRequest(BaseModel):
    id_promo: int
    id_products: list[int] = Field(min_length=1)
    date_from: date
    date_to: date


class OrderItem(BaseModel):
    id_product: int
    id_store: int
    qty: int


class OrdersRequest(BaseModel):
    id_promo: int
    orders: list[OrderItem] = Field(min_length=1)


def _product(id_product: int) -> dict:
    product = next((p for p in PRODUCTS if p["id_product"] == id_product), None)
    if product is None:
        raise HTTPException(status_code=404, detail=f"SKU {id_product} неизвестен ERP")
    return product


# Эластичность спроса по скидке (модель план-факта прошлых промоакций ERP)
ELASTICITY = {"Фреш": 1.6, "Бакалея": 2.2, "Кондитерские изделия": 2.6}


def _historic_discount(day: date) -> float:
    """Расписание прошлых промоакций ERP: 2-я неделя каждого месяца, 15/25/30 %.

    История за 3 года содержит проведенные акции, на которых модель
    машинного обучения учится оценивать uplift-прирост (UC-3, ЛР8).
    """
    schedule = [0.0, 15.0, 0.0, 25.0, 0.0, 30.0, 0.0, 15.0, 0.0, 25.0, 0.0, 30.0]
    if 10 <= day.day <= 16:
        return schedule[day.month - 1]
    return 0.0


def _history_days(product: dict, day: date, id_store: int) -> int:
    """Синтетический дневной спрос: база по категории × сезонность × шум."""
    rng = random.Random(f"{product['id_product']}:{id_store}:{day.isoformat()}")
    base = {"Фреш": 40, "Бакалея": 18, "Кондитерские изделия": 25}.get(
        product["category"], 15
    )
    store_factor = {1: 1.4, 2: 0.8, 3: 1.1}.get(id_store, 1.0)
    dow_factor = [0.9, 0.85, 0.8, 0.85, 1.1, 1.5, 1.3][day.weekday()]
    month_factor = [0.9, 0.9, 1.0, 1.0, 1.05, 1.05, 1.0, 1.0, 1.1, 1.1, 1.2, 1.3][
        day.month - 1
    ]
    noise = rng.uniform(0.8, 1.2)
    return max(0, int(base * store_factor * dow_factor * month_factor * noise))


@app.post("/api/v1/history")
def history(request: HistoryRequest) -> dict:
    """UC-8, шаг 2–3: пакет чековых данных в формате JSON."""
    if (request.date_to - request.date_from).days > _HISTORY_DAYS_LIMIT:
        raise HTTPException(status_code=400, detail="Период превышает 3 года")

    records: list[dict] = []
    for id_product in request.id_products:
        product = _product(id_product)
        for store in STORES:
            day = request.date_from
            while day <= request.date_to:
                discount = _historic_discount(day)
                rng = random.Random(
                    f"{id_product}:{store['id_store']}:{day.isoformat()}"
                )
                qty = _history_days(product, day, store["id_store"])
                if discount > 0:
                    qty = int(qty * (1 + ELASTICITY.get(product["category"], 1.8)
                                     * discount / 100
                                     * rng.uniform(0.85, 1.15)))
                if qty > 0:
                    records.append(
                        {
                            "date": day.isoformat(),
                            "id_product": id_product,
                            "id_store": store["id_store"],
                            "qty": qty,
                            "price": round(float(product["base_price"])
                                           * (1 - discount / 100), 2),
                            "discount_percent": discount,
                        }
                    )
                day += timedelta(days=1)
    logger.info("Выгружена история: %d записей за период %s…%s",
                len(records), request.date_from, request.date_to)
    return {"records": records}


@app.post("/api/v1/fact")
def fact(request: FactRequest) -> dict:
    """UC-6, шаг 2: фактические продажи за период завершенной акции.

    Факт моделируется как продажи с ростом от проведенной промоакции
    (uplift-эффект) и естественным разбросом относительно плана.
    """
    records: list[dict] = []
    for id_product in request.id_products:
        product = _product(id_product)
        days = (request.date_to - request.date_from).days + 1
        for store in STORES:
            base_total = sum(
                _history_days(product, request.date_from + timedelta(days=i),
                              store["id_store"])
                for i in range(days)
            )
            # промо-эффект: прирост пропорционален категории товара
            promo_boost = {"Фреш": 1.35, "Бакалея": 1.5,
                           "Кондитерские изделия": 1.6}.get(product["category"], 1.4)
            noise = random.Random(f"fact:{request.id_promo}:{id_product}:"
                                  f"{store['id_store']}").uniform(0.75, 1.2)
            fact_qty = int(base_total * promo_boost * noise)
            records.append(
                {
                    "id_product": id_product,
                    "id_store": store["id_store"],
                    "fact_qty": max(0, fact_qty),
                }
            )
    return {"records": records}


@app.post("/api/v1/orders")
def orders(request: OrdersRequest) -> dict:
    """UC-9, шаги 2–4: прием утвержденных объемов и создание «Заказов поставщику»."""
    results = []
    for item in request.orders:
        if item.id_product in BLOCKED_PRODUCTS:
            results.append(
                {
                    "id_product": item.id_product,
                    "id_store": item.id_store,
                    "qty": item.qty,
                    "status": "ERROR",
                    "reason": "Товар заблокирован для закупок отделом закупок ERP",
                }
            )
            continue
        results.append(
            {
                "id_product": item.id_product,
                "id_store": item.id_store,
                "qty": item.qty,
                "status": "OK",
                "reason": None,
            }
        )
    logger.info("Принят заказ промоакции %d: %d позиций",
                request.id_promo, len(request.orders))
    return {"results": results, "documents_created": sum(
        1 for r in results if r["status"] == "OK"
    )}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "erp_mock"}
