# Database Schema — AI Technical Founder

СУБД: PostgreSQL 16 (в Docker) / SQLite (локально и в тестах). ORM — SQLAlchemy 2.
Схема создаётся автоматически при старте приложения (`Base.metadata.create_all`);
миграции Alembic — в Future Scope.

## Диаграмма

```
users 1 ──── * projects 1 ──── * artifacts
                        1 ──── * generated_files
```

## users

| Колонка | Тип | Ограничения |
|---|---|---|
| id | INTEGER | PK |
| email | VARCHAR(255) | UNIQUE, NOT NULL, INDEX |
| password_hash | VARCHAR(512) | NOT NULL — PBKDF2-HMAC-SHA256, 200k итераций, соль |
| created_at | TIMESTAMP TZ | DEFAULT now (UTC) |

## projects

| Колонка | Тип | Ограничения |
|---|---|---|
| id | INTEGER | PK |
| owner_id | INTEGER | FK → users.id, NOT NULL, INDEX |
| name | VARCHAR(255) | NOT NULL |
| idea | TEXT | NOT NULL |
| status | VARCHAR(32) | `draft` / `running` / `completed` / `failed` |
| current_phase | VARCHAR(32) | текущая фаза конвейера или пустая строка |
| error | TEXT | текст ошибки при `failed` |
| created_at | TIMESTAMP TZ | DEFAULT now (UTC) |
| updated_at | TIMESTAMP TZ | автообновление при изменении |

Удаление проекта каскадно удаляет его артефакты и файлы (cascade `all, delete-orphan`
на уровне ORM).

## artifacts

Markdown-документы, созданные фазами конвейера.

| Колонка | Тип | Ограничения |
|---|---|---|
| id | INTEGER | PK |
| project_id | INTEGER | FK → projects.id, NOT NULL, INDEX |
| phase | VARCHAR(32) | vision / roadmap / architecture / structure / code / verify |
| title | VARCHAR(255) | NOT NULL |
| content | TEXT | NOT NULL — markdown |
| created_at | TIMESTAMP TZ | DEFAULT now (UTC) |

## generated_files

Файлы сгенерированной кодовой базы (фаза `code`).

| Колонка | Тип | Ограничения |
|---|---|---|
| id | INTEGER | PK |
| project_id | INTEGER | FK → projects.id, NOT NULL, INDEX |
| path | VARCHAR(512) | относительный путь в проекте, например `app/main.py` |
| content | TEXT | содержимое файла |

## Изоляция данных

Каждый запрос к проекту проверяет `owner_id == current_user.id`; чужие проекты
возвращают `404`, чтобы не раскрывать факт их существования.
