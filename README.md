# Travel Agent

ИИ-агент для планирования поездок: мастер вопросов → план по дням, бюджет и чеклист (DeepSeek).

**Установка с нуля:** [INSTALL.md](INSTALL.md)

## Быстрый старт

1. Ключ DeepSeek в `backend/.env` (см. `.env.example`)
2. Двойной клик **`start.bat`**
3. Откройте http://localhost:5173

## Возможности

- Мастер: куда → срок → бюджет → интересы
- 4 фазы: Brief, Itinerary, Budget, Checklist
- Читаемый текст на сайте (без сырого `####` / `**`)
- Скачивание плана `.md` / **PDF**
- Чат «?» — уточняющие вопросы по готовому плану
- Docker Compose, автотесты, Swagger

## Docker

```bash
cp .env.example .env   # заполните LLM_API_KEY
docker compose up --build
```

- Frontend: http://localhost:3000
- API: http://localhost:8000/docs

## Документация

- [INSTALL.md](INSTALL.md) — установка
- [docs/API.md](docs/API.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## Тесты

```bash
cd backend
pytest
```
