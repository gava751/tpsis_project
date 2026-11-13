/** Панель управления ML-моделями (UC-7): версии моделей, обучение
 *  с весами категорий (backtesting), метрики точности. Роль «Аналитик». */
import { useCallback, useEffect, useState } from "react";
import { api, ApiError, type ModelInfo } from "../api";

const CATEGORIES = ["Фреш", "Бакалея", "Кондитерские изделия"];

export default function ModelsPage() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [weights, setWeights] = useState<Record<string, number>>({ "Фреш": 1.5 });
  const [category, setCategory] = useState<string>("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api.models()
      .then(setModels)
      .catch(e => setError(e instanceof ApiError ? e.message : "Ошибка загрузки"));
  }, []);

  useEffect(() => { load(); }, [load]);

  async function train() {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const result = await api.train(category || null, weights);
      setInfo(`Обучена модель ${result.version}: MAPE ${result.mape}, WAPE ${result.wape} — сохранена как активная версия`);
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Сбой обучения");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {error && <div className="alert">{error}</div>}
      {info && <div className="alert success">{info}</div>}

      <div className="card">
        <b>Тестовое обучение модели (backtesting)</b>
        <p className="chip">
          Шаг 3–5 сценария UC-7: изменение весов признаков, обучение на накопленной
          истории и оценка метрик точности. Новая версия сохраняется в реестр моделей
          и используется при последующих расчетах прогнозов.
        </p>
        <div className="metrics-grid" style={{ maxWidth: 640 }}>
          <div className="field">
            <label>Товарная категория модели</label>
            <select value={category} onChange={e => setCategory(e.target.value)}>
              <option value="">Все категории (единая модель)</option>
              {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        </div>
        <b style={{ display: "block", margin: "10px 0 8px" }}>Веса категорий признаков</b>
        <div className="metrics-grid" style={{ maxWidth: 640 }}>
          {CATEGORIES.map(c => (
            <div className="field" key={c}>
              <label>{c}</label>
              <input type="number" step="0.1" min="0.1" max="3"
                     value={weights[c] ?? 1}
                     onChange={e => setWeights({ ...weights, [c]: +e.target.value })} />
              <div className="hint">Влияние категории на обучение (0.1–3.0)</div>
            </div>
          ))}
        </div>
        <button className="btn" disabled={busy} onClick={train}>
          {busy ? <><span className="progress" style={{ borderTopColor: "#fff" }} /> Обучение...</>
                : "Обучить модель"}
        </button>
      </div>

      <table className="data">
        <thead>
          <tr><th>Версия</th><th>Дата обучения</th><th>Категория</th>
              <th>MAPE, %</th><th>WAPE, %</th><th>Статус</th></tr>
        </thead>
        <tbody>
          {models.length === 0 && (
            <tr><td colSpan={6} className="chip">Моделей пока нет — выполните расчет прогноза</td></tr>
          )}
          {models.map((m, i) => (
            <tr key={m.version}>
              <td><b>{m.version}</b></td>
              <td>{m.trained_at.replace("T", " ").slice(0, 19)}</td>
              <td>{m.category ?? "Все категории"}</td>
              <td>{(m.mape * 100).toFixed(2)}</td>
              <td>{(m.wape * 100).toFixed(2)}</td>
              <td>{i === 0
                ? <span className="badge approved">Активная</span>
                : <span className="badge draft">Архив</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
