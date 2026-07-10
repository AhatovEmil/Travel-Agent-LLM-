# Deployment — Travel Agent

Установка на ПК: [INSTALL.md](../INSTALL.md).

## Docker Compose

```bash
cp .env.example .env
# задайте JWT_SECRET и LLM_API_KEY (DeepSeek)
docker compose up --build -d
```

- Frontend: http://localhost:3000
- API / Swagger: http://localhost:8000/docs

## Env

| Переменная | Обязательна | Описание |
|---|---|---|
| `JWT_SECRET` | да (прод) | Секрет JWT |
| `LLM_API_KEY` | да | Ключ DeepSeek |
| `LLM_BASE_URL` | нет | По умолчанию `https://api.deepseek.com/v1` |
| `LLM_MODEL` | нет | `deepseek-chat` |
| `DATABASE_URL` | нет | SQLite локально; в compose — Postgres |

## Прод-чеклист

- [ ] Сильный `JWT_SECRET`
- [ ] HTTPS перед nginx/backend
- [ ] Бэкап Postgres volume
