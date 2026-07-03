# Deployment Guide — AI Technical Founder

## Вариант 1: Docker Compose (рекомендуется)

Требования: Docker 24+ с плагином compose.

```bash
cp .env.example .env
# отредактируйте .env: обязательно задайте надёжный JWT_SECRET
docker compose up --build -d
```

Поднимаются три сервиса:

| Сервис | Образ | Порт | Назначение |
|---|---|---|---|
| `db` | postgres:16-alpine | — | БД (volume `pgdata`) |
| `backend` | build ./backend | 8000 | FastAPI API |
| `frontend` | build ./frontend | 3000 | nginx: статика SPA + прокси `/api` на backend |

Проверка:

```bash
curl http://localhost:8000/api/health
# {"status":"ok","service":"AI Technical Founder"}
```

Логи и остановка:

```bash
docker compose logs -f backend
docker compose down            # данные БД сохраняются в volume
docker compose down -v         # полное удаление вместе с данными
```

## Вариант 2: без Docker

Backend:

```bash
cd backend
pip install -r requirements.txt
# по умолчанию SQLite; для PostgreSQL:
# set DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Frontend (production-сборка):

```bash
cd frontend
npm install
npm run build      # статика в frontend/dist
```

Раздайте `dist/` любым веб-сервером и проксируйте `/api/` на backend
(пример конфигурации — `frontend/nginx.conf`).

## Переменные окружения backend

| Переменная | Обязательна | Описание |
|---|---|---|
| `JWT_SECRET` | да (в проде) | Секрет подписи токенов |
| `DATABASE_URL` | нет | По умолчанию SQLite `aitf.db` |
| `LLM_API_KEY` | нет | Включает LLM-режим генерации документов |
| `LLM_BASE_URL`, `LLM_MODEL` | нет | Параметры OpenAI-совместимого провайдера |
| `CORS_ORIGINS` | нет | В проде укажите конкретные домены вместо `*` |

## Чек-лист продакшена

- [ ] `JWT_SECRET` — случайная строка 32+ символов.
- [ ] `CORS_ORIGINS` — только реальные домены фронтенда.
- [ ] PostgreSQL с бэкапами (volume `pgdata` или управляемая БД).
- [ ] TLS-терминация (reverse proxy перед nginx/backend).
- [ ] Смена пароля `aitf_password` в `docker-compose.yml` для внешней БД.
