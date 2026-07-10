# API — Travel Agent

Базовый URL: `http://localhost:8000`. Swagger: `/docs`.

## Auth

- `POST /api/auth/register` — `{email, password}` → `{access_token}`
- `POST /api/auth/login` — то же
- `GET /api/auth/me` — текущий пользователь (Bearer)

## Trips

Все эндпоинты (кроме share) требуют `Authorization: Bearer <token>`.

- `POST /api/trips` — `{name, brief, start_date?}` → поездка (`draft`)
- `GET /api/trips` — список своих поездок
- `GET /api/trips/{id}` — детали
- `DELETE /api/trips/{id}` — удаление
- `POST /api/trips/{id}/run` — запуск агента (`202`). Без `LLM_API_KEY` → `503`
- `POST /api/trips/{id}/phases/rerun` — `{phase}` перегенерировать одну фазу (`202`)
- `POST /api/trips/{id}/chat` — `{message}` изменить план (переписывает itinerary, `202`)
- `POST /api/trips/{id}/ask` — `{message}` уточняющий вопрос (синхронно)
- `GET /api/trips/{id}/messages` — история Q&A-чата
- `GET /api/trips/{id}/artifacts` — артефакты фаз
- `GET /api/trips/{id}/extras` — дни, слоты, карта, погода, deep links, успеваемость
- `GET /api/trips/{id}/live?lat=&lon=` — «я на месте»: текущий/следующий слот
- `POST /api/trips/{id}/live/adjust` — `{reason: late|rain|custom, message?}` перестроить сегодняшний день (`202`)
- `POST /api/trips/{id}/recover` — сбросить зависший `running` → `failed` (после рестарта сервера)
- `POST /api/trips/{id}/share` — выдать `share_token` и путь `#/share/...`
- `GET /api/trips/{id}/votes` — голоса друзей
- `POST /api/trips/{id}/rebuild-from-votes` — пересобрать itinerary по голосам (`202`)
- `GET /api/trips/{id}/export` — `.md`
- `GET /api/trips/{id}/export.pdf` — PDF

## Share (без JWT)

- `GET /api/share/{token}` — публичный план + агрегаты голосов
- `POST /api/share/{token}/votes` — `{voter, day_index, slot_key, value: want|skip}`

Статусы: `draft | running | completed | failed`.  
Фазы: `brief | itinerary | budget | checklist`.

При старте сервера все `running` помечаются `failed` («Прервано перезапуском…»).  
LLM-операции ограничены `LLM_RATE_LIMIT_PER_HOUR` (по умолчанию 20/час на пользователя) → `429`.

## Health

- `GET /api/health` → `{status, service}`
