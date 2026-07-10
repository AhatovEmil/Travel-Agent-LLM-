# Deployment — Travel Agent

## Docker Compose

```bash
cp .env.example .env
# задайте JWT_SECRET и LLM_API_KEY (DeepSeek)
docker compose up --build -d
```

Сервисы: `db` (Postgres), `backend` (:8000), `frontend` (:3000).

## Без Docker

Backend: `uvicorn app.main:app --host 0.0.0.0 --port 8000`  
Frontend: `npm run build` + nginx с прокси `/api` на backend.

## Env

| Переменная | Обязательна | Описание |
|---|---|---|
| `JWT_SECRET` | да (прод) | Секрет JWT |
| `LLM_API_KEY` | да | Ключ DeepSeek |
| `LLM_BASE_URL` | нет | По умолчанию `https://api.deepseek.com/v1` |
| `LLM_MODEL` | нет | `deepseek-chat` |
| `DATABASE_URL` | нет | SQLite локально; в compose — Postgres |
