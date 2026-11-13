"""REST-контроллер промоакций (UC-2 «Настроить параметры промоакции»)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.di import get_promo_service
from app.dto.promo_schemas import PromoCreateRequest, PromoProductResponse, PromoResponse
from app.security.jwt_utils import UserPrincipal, get_current_user
from app.service.promo_service import PromoService

router = APIRouter(prefix="/api/v1/promos", tags=["Промоакции (UC-2)"])


def to_promo_response(promo) -> PromoResponse:
    """Сопоставление ORM-объекта акции и схемы ответа (DRY: единый маппер)."""
    return PromoResponse(
        id_promo=promo.id_promo,
        promo_name=promo.promo_name,
        start_date=promo.start_date,
        end_date=promo.end_date,
        status=promo.status,
        products=[
            PromoProductResponse(
                id_promo_prod=pp.id_promo_prod,
                id_product=pp.id_product,
                product_name=pp.product.name,
                category=pp.product.category,
                discount_percent=float(pp.discount_percent),
            )
            for pp in promo.products
        ],
    )


@router.post("", response_model=PromoResponse, status_code=201)
def create_promo(
    request: PromoCreateRequest,
    user: UserPrincipal = Depends(get_current_user),
    service: PromoService = Depends(get_promo_service),
) -> PromoResponse:
    """Сохранение акции в статусе «Черновик» после валидации BR-1 и BR-4."""
    return to_promo_response(service.create_promo(request))


@router.get("", response_model=list[PromoResponse])
def list_promos(
    user: UserPrincipal = Depends(get_current_user),
    service: PromoService = Depends(get_promo_service),
) -> list[PromoResponse]:
    """Экран «Список промоакций» (ЛР6, рисунок 3.1)."""
    return [to_promo_response(p) for p in service.list_promos()]


@router.get("/{id_promo}", response_model=PromoResponse)
def get_promo(
    id_promo: int,
    user: UserPrincipal = Depends(get_current_user),
    service: PromoService = Depends(get_promo_service),
) -> PromoResponse:
    """Карточка промоакции с параметрами товаров."""
    return to_promo_response(service.get_promo(id_promo))
