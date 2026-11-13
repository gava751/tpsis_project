/** Экран «Список промоакций»: сводка портфеля акций и статусные бейджи. */
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type Promo, type User } from "../api";

const STATUS_LABELS: Record<string, string> = {
  DRAFT: "Черновик", APPROVED: "Утверждена",
};

function statusBadge(status: string) {
  const label = STATUS_LABELS[status] ?? status;
  const cls = status === "APPROVED" ? "badge approved" : "badge draft";
  return <span className={cls}>{label}</span>;
}

export default function PromoListPage({ user }: { user: User }) {
  const navigate = useNavigate();
  const [promos, setPromos] = useState<Promo[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listPromos()
      .then(setPromos)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const drafts = promos.filter(p => p.status === "DRAFT").length;
  const approved = promos.filter(p => p.status !== "DRAFT").length;
  const skuCount = new Set(promos.flatMap(p => p.products.map(x => x.id_product))).size;

  return (
    <>
      {error && <div className="alert">{error}</div>}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="label">Всего промоакций</div>
          <div className="num">{promos.length}</div>
        </div>
        <div className="stat-card">
          <div className="label">В работе (черновики)</div>
          <div className="num" style={{ color: "var(--primary)" }}>{drafts}</div>
        </div>
        <div className="stat-card">
          <div className="label">Утверждено</div>
          <div className="num" style={{ color: "var(--success)" }}>{approved}</div>
        </div>
        <div className="stat-card">
          <div className="label">Товаров в акциях</div>
          <div className="num">{skuCount}</div>
        </div>
      </div>

      <div className="toolbar">
        <span className="chip">Портфель промоакций торговой сети</span>
        <span className="spacer" />
        <button className="btn" onClick={() => navigate("/promos/new")}>
          + Новая акция
        </button>
      </div>

      <table className="data">
        <thead>
          <tr>
            <th>Акция</th><th>Период</th><th>Товаров</th>
            <th>Механика</th><th>Статус</th><th style={{ width: 210 }}>Действия</th>
          </tr>
        </thead>
        <tbody>
          {loading && (
            <tr><td colSpan={6}><span className="progress" /> Загрузка...</td></tr>
          )}
          {!loading && promos.length === 0 && (
            <tr><td colSpan={6} className="chip">Промоакций пока нет — создайте первую</td></tr>
          )}
          {promos.map(promo => (
            <tr key={promo.id_promo}>
              <td><b>{promo.promo_name}</b></td>
              <td>{promo.start_date} … {promo.end_date}</td>
              <td>{promo.products.length}</td>
              <td className="chip">
                {promo.products.map(p =>
                  `${p.product_name.slice(0, 18)}… −${p.discount_percent}%`).join(", ")}
              </td>
              <td>{statusBadge(promo.status)}</td>
              <td>
                {promo.status === "DRAFT" && (
                  <Link className="plain" to={`/promos/${promo.id_promo}/forecast`}>
                    Прогноз
                  </Link>
                )}
                {promo.status !== "DRAFT" && (
                  <Link className="plain" to={`/promos/${promo.id_promo}/plan-fact`}>
                    План-факт
                  </Link>
                )}
                {" · "}
                <Link className="plain" to={`/promos/${promo.id_promo}/forecast`}>
                  Открыть
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="chip" style={{ marginTop: 12 }}>
        Роль: {user.role === "analyst" ? "руководитель отдела аналитики — доступна панель ML-моделей"
          : "категорийный менеджер — планирование и утверждение акций"}
      </p>
    </>
  );
}
