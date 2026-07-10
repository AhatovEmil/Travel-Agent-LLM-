# Travel Agent

ИИ-агент для планирования поездок: мастер вопросов → план по дням, бюджет и чеклист (DeepSeek).

**Установка с нуля:** [INSTALL.md](INSTALL.md)

## Быстрый старт

1. Ключ DeepSeek в `backend/.env` (см. `.env.example`)
2. Двойной клик **`start.bat`**
3. Откройте http://localhost:5173

## Возможности

- Мастер: куда → срок + дата → бюджет → интересы
- 4 фазы: Brief, Itinerary, Budget, Checklist
- Слоты по времени, успеваемость пешком, погода от даты старта
- Deep links: Яндекс.Карты / Booking / Aviasales
- Режим «Я на месте» + перестройка дня (опоздание / дождь)
- Совместная ссылка `#/share/...` с голосами и пересборкой
- Чат «?» — уточняющие вопросы; PDF / `.md` экспорт
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
