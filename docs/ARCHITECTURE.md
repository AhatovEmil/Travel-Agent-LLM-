# Architecture — AI Technical Founder

## Выбор стека (плюсы/минусы)

### Backend: **FastAPI** (выбран)
- **FastAPI (Python)** — ✅ быстрый старт, нативный async, Swagger из коробки, лучшая
  экосистема для LLM-интеграций (основная логика продукта — генерация). ❌ слабее типизация,
  чем в Java.
- Spring Boot — ✅ enterprise-надёжность, Liquibase. ❌ медленнее итерации, тяжёлая JVM,
  LLM-экосистема беднее. Для MVP избыточен.
- Node (Nest/Express) — ✅ один язык с фронтом. ❌ экосистема LLM/данных слабее Python.

### Frontend: **React + Vite** (выбран)
- React — крупнейшая экосистема, простая модель для SPA-дашборда. Next.js избыточен
  (SSR/SEO не нужны для кабинета), Vue — вкусовая альтернатива без преимуществ здесь.

### База данных: **PostgreSQL** (в Docker), SQLite для тестов
Доступ через SQLAlchemy — движок меняется одной переменной `DATABASE_URL`.
Схема создаётся автоматически при старте (`create_all`); Alembic-миграции — в Future Scope.

### Авторизация: **JWT** (PyJWT) + PBKDF2-хэши паролей (stdlib `hashlib`)
PBKDF2 вместо bcrypt осознанно: нет нативных зависимостей → надёжная сборка на любой ОС.

### Кэш/очередь: **Redis не используется в MVP**
Конвейер выполняется в фоне внутри процесса API (`BackgroundTasks`). Для MVP с одним
инстансом этого достаточно; Redis + worker — Future Scope при росте нагрузки.

### Docker: да (compose: postgres + backend + frontend/nginx)
### Swagger: да (автоматически, `/docs`)

## Компоненты

```
[React SPA] --HTTP/JSON--> [FastAPI]
                              |-- auth (JWT)
                              |-- projects CRUD
                              |-- pipeline runner (background)
                              |       |-- AgentEngine (интерфейс)
                              |       |     |-- TemplateEngine (офлайн, по умолчанию)
                              |       |     `-- LLMEngine (OpenAI-совместимый, по ключу)
                              |       `-- Verifier (синтакс-проверка файлов)
                              |-- packaging (ZIP)
                              `-- SQLAlchemy --> PostgreSQL / SQLite
```

## Конвейер агента (6 фаз)

| # | Фаза | Артефакт |
|---|------|----------|
| 1 | vision | Project Vision (MD) |
| 2 | roadmap | Roadmap (MD) |
| 3 | architecture | Выбор стека + схема (MD) |
| 4 | structure | Дерево файлов проекта (MD) |
| 5 | code | Файлы сгенерированного проекта (FastAPI CRUD-приложение под домен идеи) |
| 6 | verify | Отчёт проверки: синтаксис всех .py, полнота набора файлов |

Статусы проекта: `draft → running → completed | failed` (+ `current_phase`).

## Модель данных

- **users**: id, email (unique), password_hash, created_at
- **projects**: id, owner_id→users, name, idea, status, current_phase, error, created_at, updated_at
- **artifacts**: id, project_id→projects, phase, title, content, created_at
- **generated_files**: id, project_id→projects, path, content

## Безопасность

- Все эндпоинты проектов требуют JWT; каждый запрос фильтруется по `owner_id`.
- Пароли: PBKDF2-HMAC-SHA256, 200k итераций, случайная соль.
- Секрет JWT и параметры БД — только через переменные окружения.
