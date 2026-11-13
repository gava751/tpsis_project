"""Наполнение базы данных справочниками ERP (товары, магазины).

Запуск: python seed.py (из корня репозитория, после настройки .env).
Справочники импортируются из заглушки ERP – мастер-данных торговой сети.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "server_app"))

from app.core.database import Base, create_engine_from_url  # noqa: E402
from app.core.di import get_engine  # noqa: E402
from app.model import orm  # noqa: E402,F401
from app.model.orm import Product, Store  # noqa: E402
from app.core.database import make_session_factory  # noqa: E402


def main() -> None:
    # Загрузка мастер-данных ERP без конфликта имен пакетов app/*
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "erp_catalog", ROOT / "erp_mock" / "app" / "catalog.py"
    )
    erp_catalog = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(erp_catalog)
    PRODUCTS, STORES = erp_catalog.PRODUCTS, erp_catalog.STORES

    engine = create_engine_from_url()
    Base.metadata.create_all(engine)
    session = make_session_factory(engine)()

    for item in PRODUCTS:
        exists = session.get(Product, item["id_product"])
        if exists is None:
            session.add(Product(
                id_product=item["id_product"],
                name=item["name"],
                category=item["category"],
                base_price=item["base_price"],
                pack_qty=item["pack_qty"],
            ))
    for item in STORES:
        exists = session.get(Store, item["id_store"])
        if exists is None:
            session.add(Store(
                id_store=item["id_store"],
                address=item["address"],
                format=item["format"],
            ))
    session.commit()
    print("Справочники наполнены: "
          f"{session.query(Product).count()} товаров, "
          f"{session.query(Store).count()} магазинов")


if __name__ == "__main__":
    main()
