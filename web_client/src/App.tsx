/** Корневой компонент SPA: аутентификация, боковая навигация, маршруты экранов. */
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import type { ReactNode } from "react";
import { api, type User } from "./api";
import LoginPage from "./pages/LoginPage";
import PromoListPage from "./pages/PromoListPage";
import PromoCreatePage from "./pages/PromoCreatePage";
import ForecastPage from "./pages/ForecastPage";
import PlanFactPage from "./pages/PlanFactPage";
import ModelsPage from "./pages/ModelsPage";

function Shell({ user, children }: { user: User; children: ReactNode }) {
  const navigate = useNavigate();
  const isAnalyst = user.role === "analyst";

  return (
    <div className="app-shell">
      <nav className="sidebar">
        <div className="logo">Santa Promo<br />Predictor</div>
        <NavLink to="/" end>Промоакции</NavLink>
        <NavLink to="/promos/new">Новая акция</NavLink>
        {isAnalyst && <NavLink to="/models">Панель ML-моделей</NavLink>}
        <div className="role-badge">
          {user.login} — {user.role === "analyst"
            ? "Руководитель отдела аналитики"
            : "Категорийный менеджер"}
          <div style={{ marginTop: 8 }}>
            <a href="/login" onClick={e => {
              e.preventDefault();
              api.logout();
              navigate("/login");
            }} style={{ color: "#fff" }}>Выйти</a>
          </div>
        </div>
      </nav>
      <div className="main-area">{children}</div>
    </div>
  );
}

function Screen({ title, children }: { title: string; children: ReactNode }) {
  return (
    <>
      <div className="topbar"><h1>{title}</h1></div>
      <div className="page">{children}</div>
    </>
  );
}

export default function App() {
  // Подписка на маршрут заставляет App перерисоваться после navigate(),
  // что гарантирует повторное чтение учетной записи из localStorage
  useLocation();
  const user = api.currentUser();

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      {user ? (
        <>
          <Route path="/" element={
            <Shell user={user}><Screen title="Список промоакций"><PromoListPage user={user} /></Screen></Shell>} />
          <Route path="/promos/new" element={
            <Shell user={user}><Screen title="Новая промоакция"><PromoCreatePage /></Screen></Shell>} />
          <Route path="/promos/:id/forecast" element={
            <Shell user={user}><Screen title="Таблица прогноза"><ForecastPage /></Screen></Shell>} />
          <Route path="/promos/:id/plan-fact" element={
            <Shell user={user}><Screen title="Отчет план-факт"><PlanFactPage /></Screen></Shell>} />
          <Route path="/models" element={
            <Shell user={user}><Screen title="Панель управления ML-моделями"><ModelsPage /></Screen></Shell>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </>
      ) : (
        <Route path="*" element={<Navigate to="/login" replace />} />
      )}
    </Routes>
  );
}
