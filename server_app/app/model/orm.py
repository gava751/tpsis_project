"""ORM-модели базы данных.

Схема соответствует физическому проектированию (ЛР7): таблицы
promo_campaign, product, store, promo_product, forecast_result.
Расширения реализации: статусы акции/прогноза, квант поставки,
причина ручной корректировки (см. db/init.sql и отчет ЛР9).
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PromoCampaign(Base):
    """Маркетинговая промоакция торговой сети."""

    __tablename__ = "promo_campaign"
    __table_args__ = (CheckConstraint("end_date > start_date", name="chk_promo_dates"),)

    id_promo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    promo_name: Mapped[str] = mapped_column(String(150), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")

    products: Mapped[list["PromoProduct"]] = relationship(
        back_populates="promo", cascade="all, delete-orphan"
    )


class Product(Base):
    """Номенклатурный справочник товаров (SKU из ERP-системы)."""

    __tablename__ = "product"
    __table_args__ = (CheckConstraint("pack_qty >= 1", name="chk_pack_qty"),)

    id_product: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    base_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    pack_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class Store(Base):
    """Справочник физических магазинов торговой сети."""

    __tablename__ = "store"

    id_store: Mapped[int] = mapped_column(Integer, primary_key=True)
    address: Mapped[str] = mapped_column(String(200), nullable=False)
    format: Mapped[str] = mapped_column(String(50), nullable=False)


class PromoProduct(Base):
    """Акционный товар: связь товара с промоакцией и размер скидки."""

    __tablename__ = "promo_product"
    __table_args__ = (
        CheckConstraint("discount_percent > 0 AND discount_percent <= 50",
                        name="chk_discount"),
    )

    id_promo_prod: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_promo: Mapped[int] = mapped_column(
        ForeignKey("promo_campaign.id_promo", ondelete="CASCADE"), nullable=False
    )
    id_product: Mapped[int] = mapped_column(
        ForeignKey("product.id_product"), nullable=False
    )
    discount_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)

    promo: Mapped[PromoCampaign] = relationship(back_populates="products")
    product: Mapped[Product] = relationship()
    forecasts: Mapped[list["ForecastResult"]] = relationship(
        back_populates="promo_product", cascade="all, delete-orphan"
    )


class ForecastResult(Base):
    """Строка результата прогнозирования: товар × магазин (таблица forecast_result)."""

    __tablename__ = "forecast_result"
    __table_args__ = (
        CheckConstraint("baseline_qty >= 0", name="chk_baseline"),
        CheckConstraint("final_order_qty >= 0", name="chk_final_order"),
    )

    id_forecast: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_promo_prod: Mapped[int] = mapped_column(
        ForeignKey("promo_product.id_promo_prod", ondelete="CASCADE"), nullable=False
    )
    id_store: Mapped[int] = mapped_column(
        ForeignKey("store.id_store"), nullable=False
    )
    baseline_qty: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    uplift_qty: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    final_order_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="CREATED")
    correction_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_corrected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    promo_product: Mapped[PromoProduct] = relationship(back_populates="forecasts")
    store: Mapped[Store] = relationship()
