# API Reference — AI Technical Founder

Базовый URL: `http://localhost:8000`. Интерактивная документация: `/docs` (Swagger UI).

Все эндпоинты, кроме `/api/health` и `/api/auth/*`, требуют заголовок
`Authorization: Bearer <token>`.

## Health

| Метод | Путь | Ответ |
|---|---|---|
| GET | `/api/health` | `{"status": "ok", "service": "AI Technical Founder"}` |

## Auth

### POST `/api/auth/register` → 201

```json
{ "email": "founder@example.com", "password": "secret123" }
```

Ответ: `{ "access_token": "...", "token_type": "bearer" }`.
Ошибки: `409` — email уже занят, `422` — пароль короче 6 символов.

### POST `/api/auth/login` → 200

Тело как у register. Ошибка `401` — неверные учётные данные.

### GET `/api/auth/me` → 200

Ответ: `{ "id": 1, "email": "...", "created_at": "..." }`.

## Projects

### POST `/api/projects` → 201

```json
{ "name": "Маркетплейс одежды", "idea": "Хочу сделать маркетплейс одежды с заказами" }
```

`idea` — от 10 до 10000 символов. Проект создаётся в статусе `draft`.

### GET `/api/projects` → 200

Список проектов текущего пользователя (новые первыми).

### GET `/api/projects/{id}` → 200

Объект проекта:

```json
{
  "id": 1, "name": "...", "idea": "...",
  "status": "draft | running | completed | failed",
  "current_phase": "vision | roadmap | architecture | structure | code | verify",
  "error": "", "created_at": "...", "updated_at": "..."
}
```

`404` — проект не существует или принадлежит другому пользователю.

### DELETE `/api/projects/{id}` → 204

Удаляет проект вместе с артефактами и файлами.

### POST `/api/projects/{id}/run` → 202

Запускает конвейер агента в фоне. `409` — конвейер уже выполняется.
Повторный запуск завершённого проекта очищает прошлые результаты.

### GET `/api/projects/{id}/artifacts` → 200

Массив артефактов фаз:

```json
[{ "id": 1, "phase": "vision", "title": "Project Vision", "content": "# ...", "created_at": "..." }]
```

### GET `/api/projects/{id}/files` → 200

Массив сгенерированных файлов: `[{ "id": 1, "path": "app/main.py", "content": "..." }]`.

### GET `/api/projects/{id}/download` → 200

ZIP-архив (`application/zip`): документы фаз в `docs/`, файлы кода — по своим путям.
`409` — проект ещё не в статусе `completed`.

## Типовой сценарий

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"f@e.com","password":"secret123"}' | jq -r .access_token)

ID=$(curl -s -X POST localhost:8000/api/projects \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"Shop","idea":"Хочу сделать маркетплейс одежды"}' | jq -r .id)

curl -s -X POST localhost:8000/api/projects/$ID/run -H "Authorization: Bearer $TOKEN"

# ...дождаться status=completed...
curl -s localhost:8000/api/projects/$ID -H "Authorization: Bearer $TOKEN" | jq .status

curl -s -o project.zip localhost:8000/api/projects/$ID/download -H "Authorization: Bearer $TOKEN"
```
