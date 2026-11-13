"""Сервис промоакций: UC-2 «Настроить параметры промоакции».

Валидация бизнес-правил BR-1 (не менее 14 дней до старта) и BR-4
(скидка не более 50 %) выполняется до сохранения акции (FR2-1, FR2-2).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.enums import PromoStatus
from app.core.errors import NotFoundError
from app.dto.promo_schemas import PromoCreateRequest, PromoProductItem
from app.model.orm import Product, PromoCampaign, PromoProduct
from app.repository.interfaces import CatalogRepository, DateTimeProvider, PromoRepository
from app.service import rules


class PromoService:
    """Создание и просмотр промоакций (принцип SRP: только логика акций)."""

    def __init__(self, promos: PromoRepository, catalogs: CatalogRepository,
                 clock: DateTimeProvider) -> None:
        self._promos = promos
        self._catalogs = catalogs
        self._clock = clock

    def create_promo(self, request: PromoCreateRequest) -> PromoCampaign:
        rules.validate_promo_dates(request.start_date, request.end_date,
                                   self._clock.today())
        products = self._catalogs.get_products(
            [item.id_product for item in request.products]
        )
        found_ids = {p.id_product for p in products}
        missing = [item.id_product for item in request.products
                   if item.id_product not in found_ids]
        if missing:
            raise NotFoundError(f"Товары не найдены в справочнике: {missing}")

        promo = PromoCampaign(
            promo_name=request.promo_name,
            start_date=request.start_date,
            end_date=request.end_date,
            status=PromoStatus.DRAFT.value,
        )
        self._promos.create(promo)
        for item in request.products:
            rules.validate_discount(item.discount_percent)  # BR-4
            self._promos.add_promo_product(
                PromoProduct(
                    id_promo=promo.id_promo,
                    id_product=item.id_product,
                    discount_percent=item.discount_percent,
                )
            )
        return promo

    def get_promo(self, id_promo: int) -> PromoCampaign:
        promo = self._promos.get(id_promo)
        if promo is None:
            raise NotFoundError(f"Промоакция {id_promo} не найдена")
        return promo

    def list_promos(self) -> list[PromoCampaign]:
        return self._promos.list()
