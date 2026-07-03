# Project Structure

```
project/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # точка входа FastAPI, создание схемы БД
│   │   ├── config.py            # настройки из переменных окружения
│   │   ├── database.py          # engine, сессии SQLAlchemy
│   │   ├── models.py            # ORM: User, Project, Artifact, GeneratedFile
│   │   ├── schemas.py           # Pydantic DTO
│   │   ├── security.py          # PBKDF2-хэши, JWT
│   │   ├── deps.py              # зависимости: сессия БД, текущий пользователь
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py          # /api/auth: register, login, me
│   │   │   └── projects.py      # /api/projects: CRUD, run, artifacts, download
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── engine.py        # TemplateEngine + LLMEngine (генерация)
│   │       ├── verifier.py      # проверка сгенерированного кода
│   │       ├── pipeline.py      # оркестрация 6 фаз
│   │       └── packaging.py     # сборка ZIP
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_projects.py
│   │   └── test_pipeline.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx              # маршрутизация + auth-контекст
│   │   ├── api.js               # HTTP-клиент
│   │   ├── pages/
│   │   │   ├── Auth.jsx         # вход / регистрация
│   │   │   ├── Dashboard.jsx    # список проектов + создание
│   │   │   └── Project.jsx      # фазы, артефакты, файлы, скачивание
│   │   └── styles.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
├── docs/                        # VISION, ROADMAP, ARCHITECTURE, STRUCTURE, API, DEPLOYMENT, DATABASE
└── README.md
```
