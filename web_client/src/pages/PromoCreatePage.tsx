/** Экран «Новая промоакция» (UC-2): валидация BR-1 (14 дней) и BR-4 (скидка 50 %). */
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError, type CatalogProduct } from "../api";

interface DraftItem {
  id_product: number;
  discount_percent: number;
}

const MAX_DISCOUNT = 50;

export default function PromoCreatePage() {
  const navigate = useNavigate();
  const [catalog, setCatalog] = useState<CatalogProduct[]>([]);
  const [name, setName] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [items, setItems] = useState<DraftItem[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.products().then(setCatalog).catch(e => setError(e.message));
  }, []);

  function toggleProduct(id: number) {
    setItems(prev => prev.some(i => i.id_product === id)
      ? prev.filter(i => i.id_product !== id)
      : [...prev, { id_product: id, discount_percent: 15 }]);
  }

  function setDiscount(id: number, value: number) {
    setItems(prev => prev.map(i => i.id_product === id ? { ...i, discount_percent: value } : i));
  }

  const minStart = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() + 14); // BR-1: не позднее чем за 14 дней
    return d.toISOString().slice(0, 10);
  }, []);

  const discountInvalid = (item: DraftItem) =>
    item.discount_percent > MAX_DISCOUNT || item.discount_percent <= 0;

  const canSave = name.trim().length > 0 && startDate && endDate
    && items.length > 0 && items.every(i => !discountInvalid(i))
    && (!endDate || !startDate || endDate > startDate);

  async function submit() {
    setBusy(true);
    setError("");
    try {
      const promo = await api.createPromo({
        promo_name: name,
        start_date: startDate,
        end_date: endDate,
        products: items,
      });
      navigate(`/promos/${promo.id_promo}/forecast`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Сервер недоступен");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {error && <div className="alert">{error}</div>}
      <div className="card" style={{ maxWidth: 720 }}>
        <div className="field">
          <label>Название акции</label>
          <input value={name} placeholder="Например, «Майские скидки 2026»"
                 onChange={e => setName(e.target.value)} />
        </div>
        <div className="metrics-grid">
          <div className="field">
            <label>Дата начала</label>
            <input type="date" value={startDate} min={minStart}
                   onChange={e => setStartDate(e.target.value)} />
            <div className="hint">Не ранее {minStart} — за 14 дней до старта (BR-1)</div>
          </div>
          <div className="field">
            <label>Дата окончания</label>
            <input type="date" value={endDate}
                   onChange={e => setEndDate(e.target.value)} />
            <div className="hint">Должна быть позже даты начала</div>
          </div>
        </div>
      </div>

      <div className="card">
        <b>Товары акции и механика «скидка %»</b>
        <p className="chip">Скидка не более 50 % (бизнес-правило BR-4)</p>
        <table className="data">
          <thead>
            <tr><th style={{ width: 40 }}></th><th>Товар</th><th>Категория</th>
                <th>Цена</th><th>Скидка, %</th><th>Заказ кратен</th></tr>
          </thead>
          <tbody>
            {catalog.map(p => {
              const item = items.find(i => i.id_product === p.id_product);
              const bad = item ? discountInvalid(item) : false;
              return (
                <tr key={p.id_product}>
                  <td>
                    <input type="checkbox" checked={!!item}
                           onChange={() => toggleProduct(p.id_product)} />
                  </td>
                  <td>{p.name}</td>
                  <td><span className="chip">{p.category}</span></td>
                  <td>{p.base_price.toFixed(2)} р.</td>
                  <td style={{ minWidth: 150 }}>
                    {item && (
                      <>
                        <input type="number" min={1} max={50}
                               className={bad ? "invalid" : ""}
                               value={item.discount_percent}
                               onChange={e => setDiscount(p.id_product, +e.target.value)} />
                        {bad && (
                          <div className="error-text">
                            Превышен маркетинговый лимит {MAX_DISCOUNT} %
                          </div>
                        )}
                      </>
                    )}
                  </td>
                  <td className="chip">упаковка × {p.pack_qty}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="toolbar">
        <span className="chip">
          {items.length > 0
            ? `Выбрано товаров: ${items.length}`
            : "Отметьте товары, участвующие в акции"}
        </span>
        <span className="spacer" />
        <button className="btn success" disabled={!canSave || busy} onClick={submit}>
          {busy ? <><span className="progress" style={{ borderTopColor: "#fff" }} /> Сохранение...</>
                : "Сохранить акцию"}
        </button>
      </div>
    </>
  );
}
