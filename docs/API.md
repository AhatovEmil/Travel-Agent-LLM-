# API — Travel Agent

Базовый URL: `http://localhost:8000`. Swagger: `/docs`.

## Auth

- `POST /api/auth/register` — `{email, password}` → `{access_token}`
- `POST /api/auth/login` — то же
- `GET /api/auth/me` — текущий пользователь (Bearer)

## Trips

Все эндпоинты требуют `Authorization: Bearer <token>`.

- `POST /api/trips` — `{name, brief}` → поездка (`draft`)
- `GET /api/trips` — список своих поездок
- `GET /api/trips/{id}` — детали
- `DELETE /api/trips/{id}` — удаление
- `POST /api/trips/{id}/run` — запуск агента (`202`). Без `LLM_API_KEY` → `503`
- `GET /api/trips/{id}/artifacts` — артефакты фаз

Статусы: `draft | running | completed | failed`.  
Фазы: `brief | itinerary | budget | checklist`.

## Health

- `GET /api/health` → `{status, service}`
