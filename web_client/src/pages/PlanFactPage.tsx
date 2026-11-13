/** Экран «Отчет план-факт» (UC-6): метрики MAPE/WAPE, диаграмма план/факт,
 *  таблица отклонений. Положительные отклонения — зеленые, отрицательные — красные. */
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { Chart } from "chart.js/auto";
import { api, ApiError, type PlanFactResponse } from "../api";

export default function PlanFactPage() {
  const { id } = useParams();
  const idPromo = Number(id);
  const [report, setReport] = useState<PlanFactResponse | null>(null);
  const [error, setError] = useState("");
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    api.planFact(idPromo)
      .then(setReport)
      .catch(e => setError(e instanceof ApiError ? e.message : "Ошибка загрузки"));
  }, [idPromo]);

  useEffect(() => {
    if (!report || !canvasRef.current) return;
    const labels = report.rows.map(r => `${r.product_name.slice(0, 14)}… / №${r.id_store}`);
    const chart = new Chart(canvasRef.current, {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "План (заказ), шт", data: report.rows.map(r => r.plan_qty),
            backgroundColor: "#1E5AA8" },
          { label: "Факт (продажи), шт", data: report.rows.map(r => r.fact_qty),
            backgroundColor: "#2E9E4F" },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { y: { beginAtZero: true } },
      },
    });
    return () => chart.destroy();
  }, [report]);

  if (error) return <div className="alert">{error}</div>;
  if (!report) return <p><span className="progress" /> Загрузка отчета...</p>;

  return (
    <>
      <div className="stat-grid">
        <div className="stat-card">
          <div className="label">Точность модели MAPE</div>
          <div className="num" style={{ color: "var(--primary)" }}>{report.metrics.mape} %</div>
        </div>
        <div className="stat-card">
          <div className="label">Точность модели WAPE</div>
          <div className="num" style={{ color: "var(--primary)" }}>{report.metrics.wape} %</div>
        </div>
        <div className="stat-card">
          <div className="label">Позиций в акции</div>
          <div className="num">{report.rows.length}</div>
        </div>
        <div className="stat-card">
          <div className="label">Суммарное отклонение</div>
          <div className="num" style={{ color: "var(--text)" }}>
            {report.rows.reduce((s, r) => s + r.deviation_qty, 0)} шт
          </div>
        </div>
      </div>

      <div className="card">
        <b>План / факт по товарным позициям, шт</b>
        <div style={{ height: 300, marginTop: 14 }}>
          <canvas ref={canvasRef} />
        </div>
      </div>

      <table className="data">
        <thead>
          <tr><th>Товар</th><th>Магазин</th><th>План, шт</th><th>Факт, шт</th>
              <th>Отклонение, шт</th><th>Отклонение, %</th><th>Отклонение, р.</th></tr>
        </thead>
        <tbody>
          {report.rows.map(row => (
            <tr key={`${row.id_product}-${row.id_store}`}>
              <td>{row.product_name}</td>
              <td className="chip">{row.store_address}</td>
              <td>{row.plan_qty}</td>
              <td>{row.fact_qty}</td>
              <td className={row.deviation_qty >= 0 ? "cell-ok" : "cell-error"}>
                {row.deviation_qty > 0 ? `+${row.deviation_qty}` : row.deviation_qty}
              </td>
              <td>{row.deviation_pct > 0 ? `+${row.deviation_pct}` : row.deviation_pct}</td>
              <td className={row.deviation_amount >= 0 ? "cell-ok" : "cell-error"}>
                {row.deviation_amount > 0 ? "+" : ""}
                {row.deviation_amount.toFixed(2)} р.
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="chip" style={{ marginTop: 12 }}>
        Акция «{report.promo_name}» · факт продаж получен из ERP-системы (UC-6, шаг 2)
      </p>
    </>
  );
}
