# LLM Consulting System

Проект двухсервисной системы LLM-консультаций:

- `auth_service` — сервис авторизации на FastAPI;
- `bot_service` — Telegram-бот на aiogram, который принимает вопросы пользователя и отправляет их в LLM через очередь задач.

Пользователь сначала регистрируется в Auth Service и получает JWT. Затем он передаёт этот токен Telegram-боту. После успешной проверки токена бот принимает вопросы и отправляет их в обработку через Celery.

## Архитектура

Проект разделён на два независимых сервиса.

### Auth Service

Auth Service отвечает за работу с пользователями:

- регистрацию
- логин
- хеширование паролей
- выпуск JWT
- получение профиля текущего пользователя по токену

Минимальные endpoint-ы:

```text
POST /auth/register
POST /auth/login
GET  /auth/me
GET  /health
```

JWT создаётся только в Auth Service.

В токен добавляются поля:

```text
sub
role
iat
exp
```

### Bot Service

Bot Service отвечает за Telegram-бота и LLM-сценарий:

- принимает JWT через команду `/token <JWT>`
- проверяет подпись и срок действия JWT
- сохраняет JWT в Redis по Telegram user_id
- проверяет наличие токена перед обработкой обычных сообщений
- отправляет LLM-запрос в Celery
- возвращает пользователю ответ модели

Bot Service не регистрирует пользователей, не создаёт JWT и не обращается к базе данных Auth Service.

В Bot Service есть два entrypoint-а:

- `app.main:app` — служебное FastAPI-приложение с `/health`
- `app.bot.run_bot` — запуск Telegram-бота в polling-режиме

В демонстрации используется запуск Telegram-бота через `app.bot.run_bot`.

## Общая схема работы

```text
Пользователь
  |
Auth Service выдаёт JWT
  |
Telegram bot принимает /token <JWT>
  |
Redis хранит JWT по telegram_user_id
  |
Telegram bot принимает обычный вопрос
  |
RabbitMQ передаёт задачу Celery
  |
Celery worker вызывает OpenRouter
  |
Celery worker отправляет ответ пользователю в Telegram через aiogram.Bot
```

Запрос к LLM не выполняется напрямую в Telegram handler. Handler только проверяет доступ и публикует задачу. Долгая операция выполняется Celery worker-ом.

## Стек

- Python 3.12
- FastAPI
- Pydantic / pydantic-settings
- SQLAlchemy async
- SQLite
- JWT через python-jose
- passlib / bcrypt
- aiogram
- Celery
- RabbitMQ
- Redis
- OpenRouter
- httpx
- uv
- pytest
- ruff
- Docker Compose

## Структура проекта

```text
llm-consulting-system/
├── auth_service/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   ├── usecases/
│   │   └── main.py
│   ├── tests/
│   ├── .env.example
│   ├── pyproject.toml
│   ├── pytest.ini
│   └── uv.lock
├── bot_service/
│   ├── app/
│   │   ├── bot/
│   │   ├── core/
│   │   ├── infra/
│   │   ├── services/
│   │   ├── tasks/
│   │   └── main.py
│   ├── tests/
│   ├── .env.example
│   ├── pyproject.toml
│   ├── pytest.ini
│   └── uv.lock
├── docs/
│   └── images/
├── docker-compose.yml
├── .gitignore
└── README.md
```

## Переменные окружения

В каждом сервисе есть файл `.env.example`. Для локального запуска нужно создать `.env` на его основе:

```bash
cp auth_service/.env.example auth_service/.env
cp bot_service/.env.example bot_service/.env
```

Реальные `.env` не добавляются в Git.

В `auth_service/.env` нужно проверить настройки JWT и путь к SQLite-базе:

- `JWT_SECRET`
- `JWT_ALG`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `SQLITE_PATH`

В `bot_service/.env` нужно заполнить токены и настройки внешних сервисов:

- `TELEGRAM_BOT_TOKEN`
- `OPENROUTER_API_KEY`
- `REDIS_URL`
- `RABBITMQ_URL`
- `OPENROUTER_MODEL`

`JWT_SECRET` и `JWT_ALG` должны совпадать в обоих сервисах: Auth Service использует их для выпуска JWT, Bot Service — для проверки JWT.

В `.env.example` для Bot Service указаны адреса `redis` и `rabbitmq`, которые подходят для запуска внутри Docker-сети:

```env
REDIS_URL=redis://redis:6379/0
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672//
```

При локальном запуске Python-сервисов через `uv` можно использовать опубликованные порты Docker:

```env
REDIS_URL=redis://localhost:6379/0
RABBITMQ_URL=amqp://guest:guest@localhost:5672//
```

## Установка зависимостей

### Auth Service

```bash
cd auth_service
uv sync
```

### Bot Service

```bash
cd bot_service
uv sync
```

## Запуск проекта

### 1. Redis и RabbitMQ

Из корня проекта:

```bash
docker compose up -d redis rabbitmq
```

Проверка:

```bash
docker compose ps
```

RabbitMQ Management UI:

```text
http://localhost:15672
```

Логин и пароль:

```text
guest / guest
```

### 2. Auth Service

```bash
cd auth_service
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger:

```text
http://localhost:8000/docs
```

Проверка health endpoint:

```bash
curl http://localhost:8000/health
```

### 3. Celery worker

```bash
cd bot_service
uv run celery -A app.infra.celery_app.celery_app worker --loglevel=info
```

Worker обрабатывает задачу:

```text
app.tasks.llm_tasks.llm_request
```

### 4. Telegram bot

```bash
cd bot_service
uv run python -m app.bot.run_bot
```

## Пользовательский сценарий

1. Пользователь регистрируется в Auth Service через Swagger
2. Пользователь логинится через `/auth/login`
3. Auth Service возвращает JWT
4. Пользователь отправляет Telegram-боту команду:

```text
/token <JWT>
```

5. Бот валидирует JWT и сохраняет его в Redis
6. Пользователь отправляет обычный вопрос
7. Бот отправляет задачу в Celery через `llm_request.delay(...)`
8. Celery worker получает задачу из RabbitMQ
9. Worker вызывает OpenRouter
10. Worker отправляет ответ пользователю в Telegram через `aiogram.Bot`

## Тестирование

### Auth Service

```bash
cd auth_service
uv run pytest
uv run ruff check app tests
```

Покрыты:

- хеширование и проверка пароля
- создание и декодирование JWT
- регистрация
- логин
- `/auth/me`
- негативные сценарии: повторная регистрация, неверный пароль, отсутствие или некорректный токен

### Bot Service

```bash
cd bot_service
uv run pytest
uv run ruff check app tests
```

Покрыты:

- валидация JWT
- обработчик `/token <JWT>`
- обработка обычного сообщения без токена
- обработка обычного сообщения с валидным токеном
- вызов `llm_request.delay(...)` без реального RabbitMQ
- OpenRouter client через `respx`
- Celery task с замоканными OpenRouter и отправкой сообщения в Telegram

В unit/mock-тестах не используются реальные Redis, RabbitMQ, Telegram и OpenRouter. Для этого применяются `fakeredis`, `respx` и мокинг зависимостей.

## Демонстрация работы

### Регистрация пользователя

![Swagger register](docs/images/swagger_register.png)

### Логин

JWT на скриншоте скрыт.

![Swagger login](docs/images/swagger_login.png)

### Получение профиля `/auth/me`

JWT в заголовке скрыт.

![Swagger me](docs/images/swagger_me.png)

### Передача JWT Telegram-боту

JWT на скриншоте скрыт.

![Telegram token saved](docs/images/telegram_token_saved.png)

### Ответ от LLM в Telegram

![Telegram LLM response](docs/images/telegram_llm_response.png)

### RabbitMQ

![RabbitMQ queues](docs/images/rabbitmq_queues.png)

### Celery worker

![Celery worker task](docs/images/celery_worker_task.png)

### Тесты Auth Service

![Auth tests](docs/images/auth_tests.png)

### Тесты Bot Service

![Bot tests](docs/images/bot_tests.png)

## Ограничения и допущения

- Для учебного проекта используется общий `JWT_SECRET` и алгоритм `HS256`
- Auth Service использует SQLite
- Bot Service не обращается к базе данных Auth Service
- Redis используется для хранения JWT, связанного с Telegram user_id
- RabbitMQ используется как broker Celery
- Redis также используется как result backend Celery
- Запрос к LLM не выполняется напрямую в Telegram handler
- OpenRouter-модель задаётся через `OPENROUTER_MODEL` и может быть заменена при необходимости
