# Backend (FastAPI) — «Умный склад»

Этот backend реализует требования кейса «Умный склад» (РТК ИТ): приём телеметрии от роботов, запись истории инвентаризации, real‑time обновления через WebSocket, загрузка CSV, экспорт в Excel, простая авторизация JWT для пользователей и роботов, а также блок предиктивной аналитики.
> Архитектура слоистая: **API → services → repo → db**, DI через `dependency-injector`. Все публичные эндпойнты задокументированы в Swagger (`/docs`).

---

## Содержание
- [Технологии](#технологии)
- [Структура проекта](#структура-проекта)
- [Быстрый старт локально](#быстрый-старт-локально)
- [Запуск в Docker / Compose](#запуск-в-docker--compose)
- [Переменные окружения](#переменные-окружения)
- [Модели БД](#модели-бд)
- [Авторизация](#авторизация)
- [Основные эндпойнты (REST + WS)](#основные-эндпойнты-rest--ws)
- [Импорт CSV](#импорт-csv)
- [Экспорт Excel](#экспорт-excel)
- [WebSocket уведомления](#websocket-уведомления)
- [DI и транзакции](#di-и-транзакции)
- [Тесты и Makefile](#тесты-и-makefile)

---

## Технологии

- **Python**
- **FastAPI**
- **SQLAlchemy**
- **PostgreSQL 15**
- **dependency-injector** (DI контейнер)
- **Pydantic v2**
- **Uvicorn**
- **structlog** (логирование)
- **OpenPyXL** (экспорт Excel)
- **pytest**, **pytest-asyncio**, **httpx** (тесты)
- **WebSocket** (реал‑тайм уведомления)

---

## Структура проекта

```
back/
  main.py                      # сборка FastAPI-приложения, lifespan (создание схем)
  requirements.txt
  Dockerfile
  Dockerfile.test
  Makefile
  pytest.ini
  .env                         # локальные значения (dev)

  app/
    api/                       # HTTP/WS роутеры
      health.py                # GET /ping
      user.py                  # /auth (создание, логин, /me)
      robot.py                 # /robots (регистрация, ingest телеметрии)
      inventory.py             # /api/inventory (история с фильтрами)
      import_csv.py            # POST /api/inventory/import
      export.py                # GET /api/export/excel?ids=...
      dashboard.py             # GET /api/dashboard/current
      ai.py                    # POST /api/ai/predict (заглушка)
      ws.py                    # WS /ws/notifications

    core/                      # конфигурация, безопасность, DI, middleware
      settings.py
      container.py
      security.py              # пароли/хэши/JWT (user/robot)
      middleware.py            # AuthMiddleware для user
      robot_middleware.py      # RobotAuthMiddleware для роботов
      exeptions.py

    db/
      base.py                  # SQLAlchemy модели (Users, Robots, Product, InventoryHistory, AiPrediction)
      session.py               # engine + sessionmaker

    repo/                      # репозитории (работа с БД)
      user.py, robot.py, product.py, inventory.py

    services/                  # доменная логика
      auth.py, robot.py, history.py, dashboard.py,
      import_inventory.py, export_service.py, ai.py

    schemas/                   # Pydantic-модели запросов/ответов
      user.py, robot.py, product.py, inventory.py,
      request.py, token.py, dashboard.py, ai.py, import_inventory.py

    utils/
      deps.py

    ws/
      auth_ws.py               # проверка Bearer-токена в WS
      connection_manager.py
      notifier.py              # отправка унифицированных сообщений

  robot_emulator/
    emulator.py                # симулятор роботов (опционально)
    Dockerfile                 # образ эмулятора
```

---

## Быстрый старт локально

1) Установите зависимости:
```bash
cd back
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2) Поднимите PostgreSQL (любой способ). Пример через compose из корня репо:
```bash
docker compose up -d postgres
```
По умолчанию БД доступна на `localhost:5432`, имя БД `app_db`, пользователь `app_user`, пароль `app_pass` (см. ваш compose).

3) Настройте `.env` (см. раздел ниже). Для разработки достаточно значения по умолчанию.

4) Запустите приложение:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Проверка живости:
```bash
curl http://localhost:8000/ping
# {"status":"ok"}
```
Документация API: `http://localhost:8000/docs`

---

## Запуск в Docker / Compose


Запуск docker:
```bash
docker compose up -d --build
```

Пример сервиса в `docker-compose.yaml` (фрагмент):
```yaml
backend:
  build: ./back
  environment:
    PYTHONPATH: /app
    POSTGRES_HOST: postgres
    POSTGRES_PORT: 5432
    POSTGRES_USER: app_user
    POSTGRES_PASSWORD: app_pass
    POSTGRES_DB: app_db
    ASYNC_DATABASE_URL: postgresql+asyncpg://app_user:app_pass@postgres:5432/app_db
    ACCESS_TOKEN_EXPIRE_MINUTES: 30
    PASSWORD_MIN_LENGTH: 8
    SECRET_KEY: super-secret
  depends_on:
    postgres:
      condition: service_healthy
  ports:
    - "8000:8000"
  command: uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Переменные окружения

Минимальный набор для запуска (см. `app/core/settings.py`):

```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=app_db
POSTGRES_USER=app_user
POSTGRES_PASSWORD=app_pass

# строка подключения (локально — psycopg, в контейнере — asyncpg)
ASYNC_DATABASE_URL=postgresql+psycopg://app_user:app_pass@localhost:5432/app_db

# Auth
SECRET_KEY=dev-secret
ACCESS_TOKEN_EXPIRE_MINUTES=1440
PASSWORD_MIN_LENGTH=8
ALGORITHM=HS256

# Опционально
ISSUER=um-sklad
AUDIENCE=um-sklad-clients
```

> В продакшене используйте `postgresql+asyncpg://...` и реальные секреты.

---

## Модели БД

Определены в `app/db/base.py` и автоматически создаются при старте (см. `lifespan` в `main.py`):

- **Users** — сотрудники (email, пароль, роль).
- **Robots** — роботы (robot_id, статус, заряд, зона/ряд/полка, last_update).
- **Product** — справочник товаров (id, name, category, min/optimal).
- **InventoryHistory** — история сканирований (robot_id, product_id, quantity, zone/row/shelf, status, scanned_at).
- **AiPrediction** — прогнозы ИИ (product_id, days_until_stockout, recommended_order, confidence).

---

## Авторизация

### Пользователь
- `POST /auth/create` — создать пользователя.
- `POST /auth/login` — получить **JWT** вида `{ "token": "<...>" }`.
- `GET /auth/me` — контекст текущего пользователя по токену.

Мидлвара `AuthMiddleware` закрывает защищённые пути, требуя `Authorization: Bearer <user_token>`.

### Робот
- `POST /robots/register` — регистрация робота и выдача **robot‑token**.
- `POST /robots/ingest` — загрузка телеметрии и сканов. Доступ только с `Authorization: Bearer <robot_token>` (см. `RobotAuthMiddleware`).

---

## Основные эндпойнты (REST + WS)

### Health
```
GET /ping                           # {"status":"ok"}
```

### Auth
```
POST /auth/create
POST /auth/login
GET  /auth/me
```

### Роботы
```
GET  /robots/all                    # список роботов
POST /robots/register               # регистрация, выдача robot-token
POST /robots/ingest                 # телеметрия + сканы (robot-token обязателен)
```

Пример регистрации робота:
```bash
curl -X POST http://localhost:8000/robots/register \
  -H "Content-Type: application/json" \
  -d '{"robot_id":"RB-001","status":"online","battery_level":95,"location":{"zone":"A","row":1,"shelf":2}}'
```

### Исторические данные
```
GET /api/inventory/history
  ?from=2025-10-01T00:00:00Z
  &to=2025-11-01T00:00:00Z
  &zones=A,B
  &statuses=found,missing
  &limit=50&offset=0
  &sort_by=ts&sort_dir=desc
```

### Дашборд (текущее состояние)
```
GET /api/dashboard/current
```

### Прогноз
```
POST /api/ai/predict
{
  "period_days": 7
}
```

### Экспорт Excel
```
GET /api/export/excel?ids=1,2,3
```

### WebSocket
```
WS /ws/notifications                # требуется Authorization: Bearer <USER_TOKEN>
```

---

## Импорт CSV

Эндпойнт: `POST /api/inventory/import` (multipart/form-data, поле `file`)

Поддержка валидации строк через `InventoryImportService` и `InventoryImportRow`. Возвращает количество успешных/ошибочных строк и список ошибок с номерами строк.

Пример:
```bash
curl -X POST http://localhost:8000/api/inventory/import \
  -H "Authorization: Bearer <USER_TOKEN>" \
  -F "file=@/path/to/data.csv"
```

Ожидаемые поля строки (см. `app/schemas/import_inventory.py`):
- `robot_id`, `product_id`, `quantity` (int)
- `zone`, `row` (int), `shelf` (int)
- `status` (`OK|LOW_STOCK|CRITICAL`)
- `scanned_at` (ISO‑8601)

---

## Экспорт Excel

Эндпойнт: `GET /api/export/excel?ids=1,2,3`

Сервис `ExportService` формирует файл `inventory_export.xlsx` и отдаёт как `StreamingResponse` с корректным `Content-Disposition`.

---

## WebSocket уведомления

Маршрут: `WS /ws/notifications`  
Аутентификация: заголовок `Authorization: Bearer <USER_TOKEN>` обрабатывается в `ws/auth_ws.py`.  
Менеджер подключений: `ws/connection_manager.py`.  
Нормализация сообщений для фронта: `ws/notifier.py` (`type: robot_update | inventory_alert`).

Пример (wscat):
```bash
wscat -c "ws://localhost:8000/ws/notifications" -H "Authorization: Bearer <USER_TOKEN>"
```

---

## DI и транзакции

- Контейнер: `app/core/container.py`
- Сессия БД (`AsyncSession`) создаётся в контейнере и пробрасывается в **repo**.
- **Правило**: репозитории не делают `commit()` — только `flush()` и возврат сущностей. Транзакции контролируются на уровне **service**.

---

## Тесты и Makefile

Запуск тестов:
```bash
pytest               # все
pytest -q tests/test_api_endpoints.py::test_ping
```

Удобные цели (см. `Makefile`):
```bash
make test
make test-unit
make test-integration
make test-cov
make test-file FILE=tests/test_services_history.py
make test-func FUNC=test_process_robot_data
make clean-test
```

Для интеграционных тестов требуется доступная БД.

