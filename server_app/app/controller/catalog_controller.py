"""REST-контроллер справочников (товары и магазины) для интерфейса системы."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.di import get_catalog_repository
from app.repository.interfaces import CatalogRepository
from app.security.jwt_utils import UserPrincipal, get_current_user

router = APIRouter(prefix="/api/v1/catalog", tags=["Справочники"])


@router.get("/products")
def list_products(
    user: UserPrincipal = Depends(get_current_user),
    catalogs: CatalogRepository = Depends(get_catalog_repository),
) -> list[dict]:
    """Справочник товаров (SKU) для выбора аналогов и настройки акции (UC-2, UC-3)."""
    return [
        {
            "id_product": p.id_product,
            "name": p.name,
            "category": p.category,
            "base_price": float(p.base_price),
            "pack_qty": p.pack_qty,
        }
        for p in catalogs.list_products()
    ]


@router.get("/stores")
def list_stores(
    user: UserPrincipal = Depends(get_current_user),
    catalogs: CatalogRepository = Depends(get_catalog_repository),
) -> list[dict]:
    """Справочник магазинов торговой сети."""
    return [
        {"id_store": s.id_store, "address": s.address, "format": s.format}
        for s in catalogs.list_stores()
    ]
