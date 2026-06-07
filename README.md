# QIWI Wallet Personal API — тестовый фреймворк

Фреймворк автоматизированного тестирования [QIWI Wallet Personal API](https://developer.qiwi.com/ru/qiwi-wallet-personal/#intro) на Python 3.12+, pytest, requests и Playwright.

## Структура проекта

```
test_project/
├── api/                          # API-клиент и конфигурация
│   ├── client.py                 # HTTP-обёртка (requests)
│   ├── config.py                 # Настройки из .env
│   ├── models.py                 # Модели запросов (PaymentRequest и др.)
│   └── exceptions.py             # Исключения клиента
├── helpers/                      # Вспомогательные утилиты
│   ├── assertions.py             # Проверки статус-кодов, баланса, платежа
│   ├── mock_client.py            # Детерминированный mock-клиент
│   ├── payment_id.py             # Генерация id платежа по документации
│   └── schema_validator.py       # Валидация JSON Schema (request + response)
├── schemas/                      # JSON Schema по документации API
│   ├── payments_list.json        # Ответ: список платежей
│   ├── payments_list_request.json
│   ├── balance_accounts.json     # Ответ: счета и баланс
│   ├── balance_accounts_request.json
│   ├── payment_request.json      # Тело POST-запроса платежа
│   ├── payment_info.json         # Ответ: созданный платёж
│   ├── transaction.json          # Ответ: статус транзакции
│   ├── transaction_request.json
│   └── error_response.json       # Ответ: ошибки API
├── tests/
│   ├── conftest.py               # Фикстуры pytest
│   ├── fixtures/
│   │   └── mock_responses.json   # Эталонные ответы для mock-режима
│   ├── api/
│   │   ├── test_service_health.py
│   │   ├── test_balance.py
│   │   ├── test_payment_create.py
│   │   └── test_payment_execute.py
│   └── playwright/
│       ├── conftest.py
│       └── test_docs_smoke.py    # Smoke-проверка документации в браузере
├── postman/
│   └── QIWI_Wallet_Personal_API.postman_collection.json
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── pyproject.toml
└── README.md
```

## Быстрый старт

### 1. Установка зависимостей

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e ".[playwright]"
playwright install chromium webkit   # Chrome и Safari (WebKit) для Playwright-тестов
```

### 2. Настройка окружения

```bash
copy .env.example .env
```

Заполните переменные:

| Переменная | Описание |
|---|---|
| `QIWI_API_TOKEN` | Bearer-токен API |
| `QIWI_WALLET` | Номер кошелька без `+` (например `79991234567`) |
| `QIWI_PAYMENT_RECIPIENT` | Получатель P2P-платежа (провайдер 99) |
| `QIWI_MOCK_MODE` | `true` — без реальных HTTP-запросов |

> По документации QIWI выпуск OAuth-токенов прекращён. Для live-тестов нужен действующий токен.

### 3. Запуск тестов

```bash
# Все mock-тесты без реального API (рекомендуется для CI)
pytest -m "not integration" -v

# Только smoke (happy-path)
pytest -m smoke -v

# Негативные и расширенные сценарии
pytest -m "regression and not integration" -v

# Параллельный запуск (pytest-xdist, безопасен для mock-режима)
pytest -m "not integration" -n auto -v

# Live API (нужны QIWI_API_TOKEN и QIWI_WALLET)
pytest -m integration -v

# E2E-сценарий платежа
pytest -m e2e -v

# Playwright — проверка доступности документации (Chrome + Safari)
pytest tests/playwright/ -v -m "not integration"

# Только Playwright smoke в одном браузере (CLI pytest-playwright)
pytest -m playwright -v --browser chromium

# Параллельный запуск Playwright (xdist-safe, function-scoped фикстуры)
pytest tests/playwright/ -v -m "not integration" -n auto

# HTML-отчёт
pytest --html=report.html --self-contained-html
```

## Docker

Однокомандный запуск mock-сьюта в контейнере:

```bash
# Сборка и запуск полного mock-набора (параллельно, -n auto)
docker compose up --build qiwi-api-tests

# Только smoke
docker compose run --rm qiwi-api-tests-smoke

# Только regression (без integration)
docker compose run --rm qiwi-api-tests-regression
```

Альтернатива без compose:

```bash
docker build -t qiwi-wallet-api-tests .
docker run --rm -e QIWI_MOCK_MODE=true qiwi-wallet-api-tests
```

По умолчанию контейнер использует `QIWI_MOCK_MODE=true` и не требует реальных credentials.

## Параллелизация (pytest-xdist)

Фреймворк совместим с `pytest-xdist`:

- Фикстуры `settings`, `schema_validator`, `mock_responses` — `scope="session"` (изолированы по воркеру)
- `qiwi_client` и `mock_qiwi_client` — `scope="function"` (без общего mutable state)
- Mock-клиент не использует сеть и безопасен для `-n auto`

```bash
pytest -m "not integration" -n auto -v
```

## Валидация запросов и ответов

Каждый API-тест проверяет:

1. **Request** — JSON Schema для исходящего payload (тело POST или параметры GET)
2. **Response** — JSON Schema для тела ответа
3. **HTTP status** — явная проверка через `assert_status_code`

Пример для платежа:

- Request: `payment_request.json` (поля `id`, `sum`, `paymentMethod`, `fields`)
- Response: `payment_info.json` (статус 200, `transaction.state.code == Accepted`)

## Выбранные проверки и обоснование

### 1. Доступность сервиса (Service Health)

**Эндпоинт:** `GET /payment-history/v2/persons/{wallet}/payments?rows=10`

**Почему этот эндпоинт:**
- Требует авторизации — проверяет и API, и токен
- Возвращает стабильную структуру `data[]` (PaymentHistoryItem)
- Лёгкий запрос (10 записей) — подходит для smoke/health-check
- Отклонение схемы ответа от документации = признак деградации сервиса

**Проверки:** HTTP 200, JSON Schema `payments_list.json`, наличие массива `data`.

**Негативные сценарии:** невалидный формат кошелька, отсутствие/невалидный Bearer-токен.

### 2. Проверка баланса

**Эндпоинт:** `GET /funding-sources/v2/persons/{wallet}/accounts`

**Почему:** официальный метод получения балансов; содержит `accounts[].alias` и `balance.amount`.

**Ключевая бизнес-проверка:** баланс `qw_wallet_rub` (RUB) **строго > 0** — без средств невозможно провести тестовый платёж на 1 ₽.

**Негативные сценарии:** невалидный кошелёк, ошибка авторизации.

### 3. Создание платежа (1 ₽)

**Эндпоинт:** `POST /sinap/api/v2/terms/99/payments`

**Почему провайдер 99:** документированный P2P-перевод на QIWI Кошелёк; минимальная сумма 1 ₽ подходит для тестов.

**Проверки:**
- Тело запроса соответствует `payment_request.json`
- Ответ соответствует `payment_info.json`
- `transaction.state.code == "Accepted"` — платёж принят к проведению

**Негативные сценарии:** отсутствие обязательных полей, неверный тип `sum.amount` (строка вместо числа), отсутствие авторизации.

### 4. Исполнение платежа

В QIWI Personal API создание и приём платежа происходят одним POST-запросом (`Accepted`). Финальный статус проверяется отдельно:

**Эндпоинт:** `GET /payment-history/v2/transactions/{transactionId}?type=OUT`

**Проверки:**
- Статус `SUCCESS` или `WAITING` (платёж в обработке)
- Статус `ERROR` — провал теста

**Негативные сценарии:** невалидный `transactionId`, ошибка авторизации.

## Маркеры pytest

| Маркер | Назначение |
|---|---|
| `smoke` | Быстрые happy-path проверки (mock, без сети) |
| `regression` | Негативные сценарии и расширенная валидация |
| `integration` | Запросы к реальному API (skip без credentials) |
| `e2e` | Сквозной сценарий создания и верификации платежа |
| `playwright` | Браузерная проверка документации |
| `mock` | Тесты на фикстурных ответах |

## Postman

Импортируйте `postman/QIWI_Wallet_Personal_API.postman_collection.json`.

Коллекция содержит:
- Health: список платежей, профиль
- Balance: список счетов, RUB-баланс с timeout
- Payments: создание P2P на 1 ₽, проверка транзакции, расчёт комиссии

Переменные коллекции: `base_url`, `api_token`, `wallet`, `payment_recipient`, `transaction_id`.

## Playwright

Используется для инфраструктурной проверки: документация доступна, содержит ключевые разделы (Bearer auth, payment-history, funding-sources, sinap payments). Не заменяет API-тесты, но даёт ранний сигнал при изменении портала разработчиков.

### Фикстуры браузера

Фикстуры определены в `tests/playwright/conftest.py` и автоматически подключаются к тестам в этой директории:

| Фикстура | Описание |
|---|---|
| `browser_engine` | Параметризована по `chromium` (Chrome) и `webkit` (Safari). Каждый тест запускается дважды. |
| `browser_page` | Кортеж `(page, browser_engine)` — рекомендуемая фикстура для smoke-тестов документации. |
| `browser_context_page` | Создаёт context + page через `playwright_instance` для выбранного движка. |
| `playwright_instance` | Session-scoped драйвер Playwright (алиас pytest-playwright `playwright`). |
| `browser_type_launch_args` | `headless=True` для всех браузеров. |

> **Соответствие браузеров:** Playwright использует движок `chromium` для Chrome и `webkit` для Safari (WebKit). Это не нативный Safari/macOS, а кроссплатформенный WebKit-движок Playwright.

Пример теста с мультибраузерной фикстурой:

```python
@pytest.mark.playwright
def test_docs_page_loads(browser_page, settings):
    page, browser_engine = browser_page  # "chromium" (Chrome) или "webkit" (Safari)
    page.goto(settings.docs_url, wait_until="domcontentloaded")
    assert "edge.qiwi.com" in page.content(), f"Failed in {browser}"
```

Запуск только в Chrome или Safari:

```bash
pytest tests/playwright/ -v --browser chromium
pytest tests/playwright/ -v --browser webkit
```

Если `pytest-playwright` не установлен, тесты с маркером `playwright` автоматически пропускаются (`pytest.skip`).

## Примечания

- Live-тесты корректно **пропускаются** (`pytest.skip`), если API недоступен или токен отклонён
- Mock-режим (`QIWI_MOCK_MODE=true`) позволяет прогонять сценарии без сети
- Схемы основаны на официальной документации QIWI Wallet Personal API
- Негативные mock-тесты детерминированы через `helpers/mock_client.py` и `mock_responses.json`
