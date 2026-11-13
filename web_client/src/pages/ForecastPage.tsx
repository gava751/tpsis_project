/** Экран «Таблица прогноза» (UC-3…UC-5).
 *
 * Цветовая индикация (UI-2): желтый — ручная корректировка, зеленый — расчет,
 * красный — нарушение лимита. FR4-1: сохранение корректировки заблокировано
 * без причины. FR5-1: диалог подтверждения перед утверждением заказа.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import type { ColumnDef } from "@tanstack/react-table";
import { flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { api, ApiError, type CatalogProduct, type ForecastRow } from "../api";

const REASONS = ["ограничение склада", "риск недовоза", "ожидание сверхспроса"];

export default function ForecastPage() {
  const { id } = useParams();
  const idPromo = Number(id);
  const [rows, setRows] = useState<ForecastRow[]>([]);
  const [promoStatus, setPromoStatus] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [calculating, setCalculating] = useState(false);
  const [approving, setApproving] = useState(false);
  const [analogModal, setAnalogModal] = useState<{ productId: number } | null>(null);
  const [catalog, setCatalog] = useState<CatalogProduct[]>([]);
  const [edit, setEdit] = useState<{ row: ForecastRow; qty: number; reason: string } | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await api.getForecast(idPromo);
      setRows(data.rows);
      setPromoStatus(data.promo_status);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) setInfo("Для акции прогноз еще не рассчитан");
      else setError(e instanceof ApiError ? e.message : "Ошибка загрузки");
    }
  }, [idPromo]);

  useEffect(() => {
    load();
    api.products().then(setCatalog).catch(() => undefined);
  }, [load]);

  // ------------------------------------------------------------ UC-3
  async function runForecast(analogs: Record<string, number> = {}) {
    setCalculating(true);
    setError("");
    setInfo("");
    try {
      const data = await api.runForecast(idPromo, analogs);
      setRows(data.rows);
      setPromoStatus(data.promo_status);
      setInfo("Расчет прогноза завершен: результаты приведены к квантам поставки (BR-2)");
    } catch (e) {
      if (e instanceof ApiError && e.code === "INSUFFICIENT_HISTORY") {
        setAnalogModal(analogModalState(e.message));
      } else {
        setError(e instanceof ApiError ? e.message : "Ошибка расчета");
      }
    } finally {
      setCalculating(false);
    }
  }

  function analogModalState(message: string) {
    // FR3-2: извлекаем идентификатор товара-новинки из сообщения системы
    const match = /Для товара (\d+)/.exec(message);
    return { productId: match ? Number(match[1]) : 0 };
  }

  async function runForecastWithAnalog(analogId: number) {
    const productId = analogModal?.productId;
    setAnalogModal(null);
    if (!productId) return runForecast();
    return runForecast({ [String(productId)]: analogId });
  }

  // ------------------------------------------------------------ UC-4
  async function saveCorrection() {
    if (!edit) return;
    try {
      const data = await api.correct([{ id_forecast: edit.row.id_forecast,
        final_order_qty: edit.qty, correction_reason: edit.reason }]);
      setRows(data.rows);
      setInfo("Корректировка сохранена; ячейка помечена маркером ручного изменения");
      setEdit(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка сохранения");
    }
  }

  // ------------------------------------------------------------ UC-5 + UC-9
  async function approve() {
    setApproving(true);
    setError("");
    try {
      const result = await api.approve(idPromo);
      const failed = result.rows.filter(r => r.erp_status !== "OK");
      setPromoStatus(result.promo_status);
      setInfo(failed.length === 0
        ? "Заказ утвержден и экспортирован в ERP-систему (документы «Заказ поставщику» созданы)"
        : `Экспорт в ERP: ${failed.length} строк с ошибкой — ${failed[0].reason}`);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка утверждения");
    } finally {
      setApproving(false);
    }
  }

  const columns = useMemo<ColumnDef<ForecastRow>[]>(() => [
    { accessorKey: "product_name", header: "Товар" },
    { accessorKey: "category", header: "Категория" },
    { accessorKey: "store_address", header: "Магазин" },
    { accessorKey: "baseline_qty", header: "Baseline, шт" },
    { accessorKey: "uplift_qty", header: "Uplift, шт",
      cell: info => "+" + (info.getValue() as number) },
    {
      accessorKey: "final_order_qty",
      header: "Заказ, шт",
      cell: info => {
        const row = info.row.original;
        const editable = row.status === "CALCULATED" || row.status === "CORRECTED";
        return (
          <span
            onClick={() => editable && promoStatus === "DRAFT"
              ? setEdit({ row, qty: row.final_order_qty, reason: row.correction_reason ?? "" })
              : undefined}
            style={{ cursor: editable && promoStatus === "DRAFT" ? "pointer" : "default" }}
          >
            {row.final_order_qty}
            {row.is_corrected && " ✎"}
          </span>
        );
      },
    },
    { accessorKey: "status", header: "Статус" },
    {
      accessorKey: "correction_reason",
      header: "Причина",
      cell: info => (info.getValue() as string | null) ?? "—",
    },
  ], [promoStatus]);

  const table = useReactTable({ data: rows, columns, getCoreRowModel: getCoreRowModel() });

  const editableRows = rows.filter(r => r.status === "CALCULATED" || r.status === "CORRECTED");
  const correctedCount = rows.filter(r => r.is_corrected).length;

  return (
    <>
      {error && <div className="alert">{error}</div>}
      {info && <div className="alert success">{info}</div>}

      <div className="toolbar">
        <span className="chip">Статус акции: <b>{promoStatus === "DRAFT" ? "Черновик" : promoStatus}</b></span>
        <span className="spacer" />
        {promoStatus === "DRAFT" && (
          <>
            <button className="btn" onClick={() => runForecast()} disabled={calculating}>
              {calculating ? <><span className="progress" style={{ borderTopColor: "#fff" }} /> Идет расчет...</>
                           : "Рассчитать прогноз"}
            </button>
            <button className="btn success" onClick={() => setApproving(true)}
                    disabled={approving || editableRows.length === 0}>
              Утвердить заказ
            </button>
          </>
        )}
      </div>

      <table className="data">
        <thead>
          {table.getHeaderGroups().map(hg => (
            <tr key={hg.id}>
              {hg.headers.map(header => (
                <th key={header.id}>
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr><td colSpan={8} className="chip">
              {info ?? "Строк прогноза нет — запустите расчет"}
            </td></tr>
          )}
          {table.getRowModel().rows.map(row => (
            <tr key={row.id}>
              {row.getVisibleCells().map(cell => {
                const r = cell.row.original;
                const isQty = cell.column.id === "final_order_qty";
                const cls = isQty && r.is_corrected ? "cell-warn"
                  : isQty && (r.status === "CALCULATED" || r.status === "CORRECTED" || r.status === "EXPORTED") ? "cell-ok"
                  : r.status === "ERROR" ? "cell-error" : "";
                return (
                  <td key={cell.id} className={cls}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      <div className="legend">
        <span className="l-ok">Рассчитанный объем заказа</span>
        <span className="l-warn">Ячейка скорректирована вручную (✎)</span>
        <span className="l-error">Ошибка расчета</span>
        <span>Итого изменено вручную позиций: {correctedCount}</span>
      </div>

      {/* FR5-1: подтверждение утверждения заказа перед экспортом в ERP */}
      {approving && (
        <div className="modal-backdrop">
          <div className="modal">
            <h3>Утверждение объемов заказа</h3>
            <p>Объемы будут зафиксированы, акция переведена в статус «Утверждена»,
               а утвержденные заказы переданы в ERP-систему (UC-9).</p>
            <div className="modal-actions">
              <button className="btn secondary" onClick={() => setApproving(false)}>Отмена</button>
              <button className="btn success" onClick={approve}>Подтвердить</button>
            </div>
          </div>
        </div>
      )}

      {/* UC-4: корректировка с обязательной причиной (FR4-1) */}
      {edit && (
        <div className="modal-backdrop">
          <div className="modal">
            <h3>Корректировка объема заказа</h3>
            <p className="chip">{edit.row.product_name} · магазин №{edit.row.id_store}</p>
            <div className="field">
              <label>Итоговый объем, шт</label>
              <input type="number" min={0} value={edit.qty}
                     onChange={e => setEdit({ ...edit, qty: +e.target.value })} />
            </div>
            <div className="field">
              <label>Причина корректировки (обязательно)</label>
              <select value={edit.reason}
                      onChange={e => setEdit({ ...edit, reason: e.target.value })}>
                <option value="">— выберите причину —</option>
                {REASONS.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div className="modal-actions">
              <button className="btn secondary" onClick={() => setEdit(null)}>Отмена</button>
              {/* FR4-1: сохранение недоступно без указания причины */}
              <button className="btn" disabled={edit.reason.trim().length === 0}
                      onClick={saveCorrection}>
                Сохранить
              </button>
            </div>
          </div>
        </div>
      )}

      {/* BR-3: выбор товара-аналога для новинки */}
      {analogModal && (
        <div className="modal-backdrop">
          <div className="modal">
            <h3>Товар-новинка: недостаточно истории продаж</h3>
            <p className="chip">
              Для товара {analogModal.productId || "—"} накоплено менее 30 дней
              наблюдений (BR-3). Выберите товар-аналог из справочника.
            </p>
            <div className="field">
              <label>Товар-аналог</label>
              <select defaultValue="" onChange={e => e.target.value && runForecastWithAnalog(+e.target.value)}>
                <option value="">— выберите аналог —</option>
                {catalog.filter(p => p.id_product !== analogModal.productId).map(p => (
                  <option key={p.id_product} value={p.id_product}>
                    {p.name} ({p.category})
                  </option>
                ))}
              </select>
            </div>
            <div className="modal-actions">
              <button className="btn secondary" onClick={() => setAnalogModal(null)}>Отмена</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
