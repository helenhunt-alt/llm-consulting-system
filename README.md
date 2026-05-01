# LLM Consulting System

Учебный итоговый проект: двухсервисная система LLM-консультаций.

## Архитектура

Проект состоит из двух независимых сервисов:

- `auth_service` — FastAPI-сервис для регистрации, логина и выпуска JWT.
- `bot_service` — Telegram-бот, который валидирует JWT и отправляет LLM-запросы в очередь.

## Инфраструктура

В проекте используются:

- Redis — хранение JWT, привязанного к Telegram user_id, и backend для Celery.
- RabbitMQ — брокер задач Celery.
- Celery — фоновая обработка LLM-запросов.
- OpenRouter — внешний LLM API.

## Быстрый запуск инфраструктуры

```bash
docker compose up -d redis rabbitmq
```

RabbitMQ Management UI:

```bash
http://localhost:15672
```

Логин и пароль:

```bash
guest / guest
```

Текущий статус
Проект находится в разработке.