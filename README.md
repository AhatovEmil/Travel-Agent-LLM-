# AI Technical Founder

ИИ-агент — технический сооснователь: принимает бизнес-идею текстом и превращает её
в готовый MVP-проект «под ключ». Конвейер из 6 фаз — Vision → Roadmap → Architecture →
Structure → Code → Verify — на выходе отдаёт документы и запускаемую кодовую базу
(FastAPI + Docker + тесты + README), которую можно скачать одним ZIP-архивом.

## Возможности

- Регистрация и вход (JWT).
- Создание проекта: название + описание идеи на естественном языке.
- Автоматический конвейер агента с отслеживанием прогресса по фазам в реальном времени.
- Просмотр артефактов каждой фазы (markdown-документы, файлы кода).
- Скачивание сгенерированного проекта одним ZIP.
- Два режима генерации:
  - **template** (по умолчанию) — детерминированный офлайн-движок, работает без ключей и сети;
  - **llm** — улучшает документы через любой OpenAI-совместимый API (задайте `LLM_API_KEY`).
- Swagger-документация, Docker Compose, автотесты.

## Быстрый старт (Docker)

```bash
cp .env.example .env   # при желании укажите JWT_SECRET и LLM_API_KEY
docker compose up --build
```

- Frontend: http://localhost:3000
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs

## Запуск без Docker (разработка)

Backend (Python 3.11+):

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

По умолчанию используется SQLite (`aitf.db`); для PostgreSQL задайте `DATABASE_URL`.

Frontend (Node 20+):

```bash
cd frontend
npm install
npm run dev
```

Vite-дев-сервер на http://localhost:5173 проксирует `/api` на `localhost:8000`.

## Тесты

```bash
cd backend
pytest
```

Покрытие: авторизация, CRUD проектов и изоляция пользователей, полный прогон конвейера
с проверкой артефактов и ZIP-архива, движок генерации и верификатор.

## Как это работает

1. Пользователь описывает идею и запускает конвейер (`POST /api/projects/{id}/run`).
2. Конвейер выполняется в фоне; фазы и статус (`draft → running → completed | failed`)
   доступны через polling.
3. Движок генерации извлекает доменные сущности из текста идеи (маркетплейс → product,
   order; блог → post, comment; …) и строит под них CRUD-приложение на FastAPI.
4. Фаза Verify проверяет результат: полнота набора файлов, синтаксис всех `.py`,
   отсутствие TODO/FIXME. Только после успешной проверки проект получает статус
   `completed` и становится доступен для скачивания.

## Структура репозитория

```
backend/    FastAPI: auth, проекты, конвейер агента, генерация, упаковка ZIP
frontend/   React + Vite SPA: дашборд, страница проекта, прогресс фаз
docs/       VISION, ROADMAP, ARCHITECTURE, STRUCTURE, API, DEPLOYMENT, DATABASE
docker-compose.yml   PostgreSQL + backend + frontend (nginx)
```

Подробности: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/API.md](docs/API.md),
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md), [docs/DATABASE.md](docs/DATABASE.md).

## Конфигурация (переменные окружения)

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./aitf.db` | Строка подключения SQLAlchemy |
| `JWT_SECRET` | `change-me-in-production` | Секрет подписи JWT (смените в проде!) |
| `JWT_EXPIRES_MINUTES` | `1440` | Время жизни токена |
| `LLM_API_KEY` | пусто | Ключ OpenAI-совместимого API; пусто = офлайн-движок |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | Базовый URL LLM-провайдера |
| `LLM_MODEL` | `gpt-4o-mini` | Модель LLM |
| `CORS_ORIGINS` | `*` | Разрешённые origin через запятую |
