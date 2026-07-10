# Travel Agent

ИИ-агент для планирования поездок: вы описываете куда и на сколько едете,
агент через DeepSeek собирает **Brief**, **план по дням**, **бюджет** и **чеклист**.

## Возможности

- Регистрация и вход (JWT)
- Создание поездки свободным текстом
- Конвейер из 4 фаз с прогрессом в UI
- DeepSeek LLM (ключ обязателен)
- Docker Compose, автотесты, Swagger

## Подключение DeepSeek

1. Зарегистрируйтесь на https://platform.deepseek.com
2. Создайте API Key и пополните баланс ($1–2 хватит надолго)
3. Создайте `backend/.env`:

```
JWT_SECRET=change-me-in-production
LLM_API_KEY=sk-ваш_ключ
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
LLM_MODEL_FALLBACKS=deepseek-reasoner
```

## Быстрый старт (Docker)

```bash
cp .env.example .env
# заполните LLM_API_KEY
docker compose up --build
```

- Frontend: http://localhost:3000
- API / Swagger: http://localhost:8000/docs

## Локальная разработка

Backend:

```bash
cd backend
pip install -r requirements.txt
# создайте .env с LLM_API_KEY
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Откройте http://localhost:5173

## Тесты

```bash
cd backend
pytest
```

## Как пользоваться

1. Зарегистрируйтесь на сайте
2. Создайте поездку: «Батуми, 5 дней, 50 тыс ₽, море и еда»
3. Дождитесь фаз Brief → Itinerary → Budget → Checklist
4. Читайте артефакты на странице поездки

Цены и адреса от ИИ — **ориентир**, проверяйте перед поездкой.

## API

См. [docs/API.md](docs/API.md). Архитектура: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
