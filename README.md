# Travel Agent

ИИ-агент для планирования поездок: мастер вопросов → план по дням, бюджет и чеклист (DeepSeek).

**Установка с нуля:** [INSTALL.md](INSTALL.md)

## Быстрый старт

1. Ключ DeepSeek в `backend/.env` (см. `.env.example`)
2. **Windows:** двойной клик `start.bat`  
   **macOS:** два терминала — `uvicorn` на `:8000` и `npm run dev` (подробно в [INSTALL.md](INSTALL.md))
3. Откройте http://localhost:5173

## Возможности

- Мастер: куда → срок + дата → бюджет → интересы
- 4 фазы: Brief, Itinerary, Budget, Checklist
- Слоты по времени, успеваемость пешком, погода от даты старта
- Deep links: жильё (Booking / Островок / Я.Путешествия / Суточно) и билеты (Aviasales / Я.Авиа / Туту)
- Режим «Я на месте» + перестройка дня (опоздание / дождь)
- **ОС поездки**: режимы План / На месте / Воспоминания — утренний брифинг, вечерний чекин, дневник
- Street Smart: фразы, ловушки, вкус, квест дня, arrival
- Совместная ссылка `#/share/...` с голосами и пересборкой
- Чат «?» — уточняющие вопросы; PDF / `.md` экспорт
- Защита от зависших `running`, лимит LLM/час, кэш геокодинга
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
