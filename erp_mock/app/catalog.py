"""Номенклатура и магазины «ERP-системы» (мастер-данные торговой сети).

Единственный источник справочников: скрипт наполнения БД серверного
приложения (seed.py) импортирует данные отсюда, что гарантирует
согласованность справочников ПС и ERP (DRY).
"""
from __future__ import annotations

PRODUCTS: list[dict] = [
    # id_product – SKU в ERP; pack_qty – квант поставки поставщика (BR-2)
    {"id_product": 1001, "name": "Молоко «Савушкин» 2,5%, 1 л",
     "category": "Фреш", "base_price": 2.49, "pack_qty": 12},
    {"id_product": 1002, "name": "Сметана «Савушкин» 20%, 400 г",
     "category": "Фреш", "base_price": 3.19, "pack_qty": 10},
    {"id_product": 1003, "name": "Хлеб «Бородинский», 400 г",
     "category": "Фреш", "base_price": 1.29, "pack_qty": 20},
    {"id_product": 2001, "name": "Кофе растворимый «Milagro Select», 200 г",
     "category": "Бакалея", "base_price": 18.90, "pack_qty": 6},
    {"id_product": 2002, "name": "Крупа гречневая «Гуда», 900 г",
     "category": "Бакалея", "base_price": 4.75, "pack_qty": 10},
    {"id_product": 2003, "name": "Масло подсолнечное «Слобода», 1 л",
     "category": "Бакалея", "base_price": 6.49, "pack_qty": 12},
    {"id_product": 3001, "name": "Шоколад «Коммунарка» «Белый парус», 90 г",
     "category": "Кондитерские изделия", "base_price": 3.05, "pack_qty": 24},
    {"id_product": 3002, "name": "Конфеты «Красный пищевик» «Серпантин», 250 г",
     "category": "Кондитерские изделия", "base_price": 8.40, "pack_qty": 12},
]

STORES: list[dict] = [
    {"id_store": 1, "address": "г. Минск, пр-т Независимости, 58",
     "format": "Супермаркет"},
    {"id_store": 2, "address": "г. Минск, ул. Платонова, 22",
     "format": "Магазин у дома"},
    {"id_store": 3, "address": "г. Брест, ул. Московская, 151",
     "format": "Супермаркет"},
]

# Товары, заблокированные отделом закупок (демо альтернативного потока UC-9)
BLOCKED_PRODUCTS: list[int] = []
