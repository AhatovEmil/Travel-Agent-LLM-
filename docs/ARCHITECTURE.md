# Architecture — Travel Agent

## Стек

- **Backend:** FastAPI (Python)
- **Frontend:** React + Vite
- **БД:** PostgreSQL (Docker) / SQLite (локально и тесты)
- **Auth:** JWT + PBKDF2
- **LLM:** DeepSeek (`https://api.deepseek.com/v1`, модель `deepseek-chat`)
- **Docker:** compose (db + backend + frontend/nginx)
- **Swagger:** `/docs`

## Компоненты

```
[React SPA] --HTTP--> [FastAPI]
                         |-- auth (JWT)
                         |-- trips CRUD
                         |-- travel pipeline (background)
                         |       `-- TravelEngine -> DeepSeek
                         `-- SQLAlchemy --> PostgreSQL / SQLite
```

## Конвейер (4 фазы)

| Фаза | Артефакт |
|------|----------|
| brief | Уточнённое ТЗ поездки |
| itinerary | План по дням |
| budget | Разбивка бюджета |
| checklist | Чеклист вещей и подготовки |

Статусы поездки: `draft → running → completed | failed`.

## Модель данных

- **users**: id, email, password_hash, created_at
- **trips**: id, owner_id, name, brief, status, current_phase, error, timestamps
- **artifacts**: id, trip_id, phase, title, content, created_at

## Безопасность

- Все эндпоинты trips требуют JWT и фильтр по `owner_id`.
- `LLM_API_KEY` только из env, не в репозитории.
