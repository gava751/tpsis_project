/** Клиент REST API серверного приложения (формат JSON, JWT из localStorage). */

const API_BASE = "/api/v1";
const TOKEN_KEY = "spp_token";

export interface User { login: string; role: "manager" | "analyst"; }

export interface PromoProduct {
  id_promo_prod: number;
  id_product: number;
  product_name: string;
  category: string;
  discount_percent: number;
}

export interface Promo {
  id_promo: number;
  promo_name: string;
  start_date: string;
  end_date: string;
  status: string;
  products: PromoProduct[];
}

export interface CatalogProduct {
  id_product: number;
  name: string;
  category: string;
  base_price: number;
  pack_qty: number;
}

export interface ForecastRow {
  id_forecast: number;
  id_promo_prod: number;
  id_product: number;
  product_name: string;
  category: string;
  id_store: number;
  store_address: string;
  baseline_qty: number;
  uplift_qty: number;
  final_order_qty: number;
  status: string;
  is_corrected: boolean;
  correction_reason: string | null;
}

export interface ForecastResponse {
  id_promo: number;
  promo_status: string;
  rows: ForecastRow[];
}

export interface PlanFactRow {
  id_product: number;
  product_name: string;
  id_store: number;
  store_address: string;
  plan_qty: number;
  fact_qty: number;
  deviation_qty: number;
  deviation_pct: number;
  deviation_amount: number;
}

export interface PlanFactResponse {
  id_promo: number;
  promo_name: string;
  rows: PlanFactRow[];
  metrics: { mape: number; wape: number };
}

export interface ModelInfo {
  version: string;
  trained_at: string;
  category: string | null;
  mape: number;
  wape: number;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

function headers(withAuth = true): Record<string, string> {
  const result: Record<string, string> = { "Content-Type": "application/json" };
  const token = localStorage.getItem(TOKEN_KEY);
  if (withAuth && token) result["Authorization"] = `Bearer ${token}`;
  return result;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: headers(),
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (response.status === 401) {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem("spp_user");
    window.location.href = "/login";
    throw new ApiError(401, "NOT_AUTHENTICATED", "Сессия истекла, войдите заново");
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload as { code?: string; message?: string; detail?: unknown };
    if (typeof detail?.detail === "string") {
      throw new ApiError(response.status, "ML_ERROR", detail.detail);
    }
    if (Array.isArray(detail?.detail)) {
      throw new ApiError(response.status, "VALIDATION_ERROR",
        "Проверьте корректность заполнения полей формы");
    }
    throw new ApiError(
      response.status,
      detail?.code ?? "ERROR",
      detail?.message ?? "Ошибка выполнения запроса",
    );
  }
  return payload as T;
}

export const api = {
  login: (login: string, password: string) =>
    request<{ access_token: string; login: string; role: string }>(
      "POST", "/auth/login", { login, password }),

  listPromos: () => request<Promo[]>("GET", "/promos"),
  getPromo: (id: number) => request<Promo>("GET", `/promos/${id}`),
  createPromo: (payload: {
    promo_name: string; start_date: string; end_date: string;
    products: { id_product: number; discount_percent: number }[];
  }) => request<Promo>("POST", "/promos", payload),

  products: () => request<CatalogProduct[]>("GET", "/catalog/products"),

  runForecast: (idPromo: number, analogProducts: Record<string, number>) =>
    request<ForecastResponse>("POST", `/promos/${idPromo}/forecast`,
      { analog_products: analogProducts }),
  getForecast: (idPromo: number) =>
    request<ForecastResponse>("GET", `/promos/${idPromo}/forecast`),
  correct: (corrections: { id_forecast: number; final_order_qty: number;
                           correction_reason: string }[]) =>
    request<ForecastResponse>("PUT", "/forecasts/corrections", { corrections }),
  approve: (idPromo: number) =>
    request<{ promo_status: string; rows: { erp_status: string; reason: string | null }[] }>(
      "POST", `/promos/${idPromo}/approval`, { confirmed: true }),

  planFact: (idPromo: number) => request<PlanFactResponse>("GET", `/promos/${idPromo}/plan-fact`),

  models: () => request<ModelInfo[]>("GET", "/models"),
  train: (category: string | null, categoryWeights: Record<string, number>) =>
    request<ModelInfo & { activated: boolean }>("POST", "/models/train",
      { category, category_weights: categoryWeights }),

  saveSession(token: string, user: User) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem("spp_user", JSON.stringify(user));
  },
  currentUser(): User | null {
    const raw = localStorage.getItem("spp_user");
    return raw ? (JSON.parse(raw) as User) : null;
  },
  logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem("spp_user");
  },
};
