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
- `POST /api/trips/{id}/phases/rerun` — `{phase}` перегенерировать одну фазу (`202`)
- `POST /api/trips/{id}/chat` — `{message}` изменить план (переписывает itinerary, `202`)
- `POST /api/trips/{id}/ask` — `{message}` уточняющий вопрос (синхронно, история сохраняется)
- `GET /api/trips/{id}/messages` — история Q&A-чата
- `GET /api/trips/{id}/artifacts` — артефакты фаз
- `GET /api/trips/{id}/extras` — дни (карточки), точки карты, погода
- `GET /api/trips/{id}/export` — скачать план `.md` (только `completed`)
- `GET /api/trips/{id}/export.pdf` — скачать план PDF (только `completed`)

Статусы: `draft | running | completed | failed`.  
Фазы: `brief | itinerary | budget | checklist`.

`extras` возвращает:
```json
{
  "destination": "Батуми",
  "days_count": 5,
  "days": [{"title": "День 1 — …", "content": "…"}],
  "center": {"name": "…", "lat": 0, "lon": 0},
  "places": [{"name": "…", "lat": 0, "lon": 0}],
  "weather": [{"date": "YYYY-MM-DD", "temp_max": 28, "temp_min": 20, "label": "Ясно"}]
}
```

## Health

- `GET /api/health` → `{status, service}`
