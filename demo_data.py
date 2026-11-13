"""Демонстрационные данные для показа системы.

Создает две промоакции:
  1. «Весенние скидки» – черновик без расчета (демонстрация UC-2…UC-5);
  2. «Новогодние скидки» – завершенная акция с экспортированными объемами
     (демонстрация отчета план-факт, UC-6).

Запуск: python demo_data.py (после seed.py). Идемпотентен: повторный запуск
не создает дубликаты.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "server_app"))

from app.core.database import Base, create_engine_from_url, make_session_factory  # noqa: E402
from app.core.enums import ForecastStatus, PromoStatus  # noqa: E402
from app.model import orm  # noqa: E402,F401
from app.model.orm import ForecastResult, PromoCampaign, PromoProduct  # noqa: E402


def ensure_promo(session, name, start, end, status, products, forecasts=None):
    existing = session.query(PromoCampaign).filter_by(promo_name=name).first()
    if existing is not None:
        print(f"Акция «{name}» уже существует (id {existing.id_promo})")
        return existing
    promo = PromoCampaign(promo_name=name, start_date=start, end_date=end, status=status)
    session.add(promo)
    session.flush()
    rows = []
    for id_product, discount in products:
        pp = PromoProduct(id_promo=promo.id_promo, id_product=id_product,
                          discount_percent=discount)
        session.add(pp)
        session.flush()
        rows.append(pp)
    if forecasts:
        for pp, (baseline, uplift, final) in zip(rows, forecasts):
            for id_store in (1, 2, 3):
                session.add(ForecastResult(
                    id_promo_prod=pp.id_promo_prod, id_store=id_store,
                    baseline_qty=baseline, uplift_qty=uplift, final_order_qty=final,
                    status=ForecastStatus.EXPORTED.value,
                ))
    session.commit()
    print(f"Создана акция «{name}» (id {promo.id_promo})")
    return promo


def main() -> None:
    Base.metadata.create_all(create_engine_from_url())
    session = make_session_factory(create_engine_from_url())()
    today = date.today()

    # 1) Черновик: два товара, расчет прогноза еще не запускался
    ensure_promo(
        session, "Весенние скидки на кондитерские изделия",
        today + timedelta(days=30), today + timedelta(days=44),
        PromoStatus.DRAFT.value,
        [(3001, 20.0), (3002, 25.0)],
    )

    # 2) Завершенная акция с экспортированными заказами (план-факт)
    ensure_promo(
        session, "Новогодние скидки",
        today - timedelta(days=40), today - timedelta(days=25),
        PromoStatus.APPROVED.value,
        [(1001, 15.0), (2001, 25.0)],
        forecasts=[(1105, 391, 1572), (515, 223, 738)],
    )


if __name__ == "__main__":
    main()
