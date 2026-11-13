/** Экран авторизации (UC-1): проверка учетных данных через каталог AD. */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError, type User } from "../api";

export default function LoginPage() {
  const navigate = useNavigate();
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const token = await api.login(login, password);
      const user: User = { login: token.login, role: token.role as User["role"] };
      api.saveSession(token.access_token, user);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Сервер недоступен");
      setPassword("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center",
      justifyContent: "center", background: "var(--primary-dark)",
    }}>
      <form onSubmit={submit} className="card" style={{ width: 380, padding: 28 }}>
        <h2 style={{ margin: "0 0 4px" }}>Santa Promo Predictor</h2>
        <p className="chip" style={{ margin: "0 0 20px" }}>
          Вход по учетной записи корпоративного каталога
        </p>
        {error && <div className="alert">{error}</div>}
        <div className="field">
          <label>Логин</label>
          <input value={login} autoFocus
                 onChange={e => setLogin(e.target.value)} />
        </div>
        <div className="field">
          <label>Пароль</label>
          <input type="password" value={password}
                 onChange={e => setPassword(e.target.value)} />
        </div>
        <button className="btn" style={{ width: "100%" }} disabled={busy || !login || !password}>
          {busy ? <><span className="progress" style={{ borderTopColor: "#fff" }} /> Проверка...</> : "Войти"}
        </button>
        <p className="hint chip" style={{ marginTop: 14 }}>
          Демо-доступ: manager / manager, analyst / analyst
        </p>
      </form>
    </div>
  );
}
