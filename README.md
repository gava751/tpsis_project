# Santa Promo Predictor

Программное средство прогнозирования продаж акционных товаров розничной сети
ООО «Санта Ритейл» (вариант 17 индивидуального задания).

Состав репозитория:

| Компонент | Назначение | Порт по умолчанию |
|---|---|---|
| `server_app` | Серверное приложение REST API (FastAPI + Uvicorn): варианты использования UC-1…UC-7, интеграция с ML-сервисом и ERP | 8000 |
| `ml_service` | Вычислительное ядро машинного обучения (FastAPI + CatBoost): обучение моделей (backtesting) и расчет baseline/uplift | 8001 |
| `erp_mock` | Заглушка корпоративной ERP-системы: история продаж (UC-8), факт продаж (UC-6), прием заказов (UC-9) | 8002 |
| `db/init.sql` | DDL-скрипт создания БД MySQL (структура ЛР7) | — |
| `seed.py` | Наполнение справочников БД данными из ERP | — |
| `tests/` | Модульные тесты бизнес-логики (pytest) | — |

## Стек технологий (ЛР5)

Python 3.11+, FastAPI, Uvicorn, SQLAlchemy 2.0, MySQL, Pydantic v2, PyJWT,
httpx, CatBoost, pytest. Автодокументация API — OpenAPI/Swagger (`/docs`).

## Архитектура серверного приложения (ЛР8)

Слои: `controller` → `service` → `repository` → СУБД, интеграции
(`integration`: фасад ML-сервиса, шлюз ERP, экспортёров). Использованы
паттерны «Стратегия» (Standard/FreshForecastStrategy), «Фасад»
(MlServiceFacade), «Репозиторий» и шаблон внедрения зависимостей DI.

## Установка и запуск

1. Создать виртуальное окружение и установить зависимости:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements\requirements-server.txt
pip install -r requirements\requirements-ml.txt
pip install -r requirements\requirements-erp.txt
pip install -r requirements\requirements-dev.txt
```

2. Настроить подключение к БД и адреса сервисов (скопировать
`.env.example` в `.env`). По умолчанию используется MySQL
(база `santa_promo`, пользователь `santa`); для быстрого старта
без MySQL укажите `DB_URL=sqlite:///./santa_promo.db`.

3. Наполнить справочники:

```bash
python seed.py
```

4. Запустить три компонента (в отдельных терминалах, из корня репозитория):

```bash
# 1) Заглушка ERP
uvicorn app.main:app --app-dir erp_mock --port 8002

# 2) ML-сервис
uvicorn main:app --app-dir ml_service --port 8001

# 3) Серверное приложение
uvicorn app.main:app --app-dir server_app --port 8000
```

5. Открыть документацию API: <http://127.0.0.1:8000/docs>.

## Учетные записи (UC-1, заглушка Active Directory)

| Логин | Пароль | Роль |
|---|---|---|
| `manager` | `manager` | Категорийный менеджер |
| `analyst` | `analyst` | Руководитель отдела аналитики (UC-7) |

## Быстрый сценарий проверки (UC-2 → UC-5)

1. `POST /api/v1/auth/login` → получить JWT-токен.
2. `POST /api/v1/promos` → создать акцию (дата старта не менее чем через
   14 дней, скидка ≤ 50 %).
3. `POST /api/v1/promos/{id}/forecast` → расчет прогноза (ML-сервис
   обучается на истории при первом запуске).
4. `PUT /api/v1/forecasts/corrections` → ручная корректировка с причиной.
5. `POST /api/v1/promos/{id}/approval` → утверждение и экспорт в ERP.

## Тесты

```bash
pytest tests -v
```

Тесты используют SQLite in-memory и тестовых двойников интеграций —
внешние сервисы для запуска не требуются.
