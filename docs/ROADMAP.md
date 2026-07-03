# Roadmap — AI Technical Founder MVP

Каждый пункт — отдельная задача. Порядок соблюдается.

1. **Backend-каркас** — FastAPI, конфигурация, подключение БД (PostgreSQL / SQLite).
2. **Модели данных** — User, Project, Artifact, GeneratedFile.
3. **Авторизация** — регистрация, логин, JWT, защита эндпоинтов.
4. **CRUD проектов** — создание, список, детали, удаление; изоляция по владельцу.
5. **Конвейер агента** — 6 фаз (Vision, Roadmap, Architecture, Structure, Code, Verify),
   фоновое выполнение, статусы.
6. **Движок генерации** — template-движок (офлайн) + опциональный LLM-провайдер.
7. **Упаковка** — сборка ZIP из сгенерированных файлов, эндпоинт скачивания.
8. **Frontend** — React: логин/регистрация, дашборд, страница проекта с фазами и
   артефактами, кнопка скачивания.
9. **Docker** — Dockerfile для backend и frontend, docker-compose с PostgreSQL.
10. **Тесты** — pytest: auth, проекты, полный прогон конвейера, скачивание ZIP.
11. **Документация** — README, API.md, ARCHITECTURE.md, DEPLOYMENT.md, DATABASE.md, Swagger.
