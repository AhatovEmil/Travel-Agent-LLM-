"""Движки генерации артефактов и кода.

TemplateEngine — детерминированный, работает без сети: извлекает доменные сущности
из текста идеи и генерирует запускаемое FastAPI CRUD-приложение.

LLMEngine — использует OpenAI-совместимый API, если задан LLM_API_KEY; при любой
ошибке провайдера конвейер откатывается на TemplateEngine, чтобы результат был всегда.
"""

import json
import re

import httpx

from ..config import settings

# Ключевые слова -> доменные сущности сгенерированного приложения.
DOMAIN_HINTS = {
    "маркетплейс": ["product", "order"],
    "магазин": ["product", "order"],
    "shop": ["product", "order"],
    "marketplace": ["product", "order"],
    "одежд": ["product", "order"],
    "блог": ["post", "comment"],
    "blog": ["post", "comment"],
    "задач": ["task"],
    "todo": ["task"],
    "трекер": ["task"],
    "врач": ["appointment"],
    "запис": ["appointment"],
    "booking": ["appointment"],
    "бронирован": ["appointment"],
    "финанс": ["transaction"],
    "бюджет": ["transaction"],
    "курс": ["course", "lesson"],
    "обучен": ["course", "lesson"],
    "доставк": ["order"],
    "чат": ["message"],
    "форум": ["post", "comment"],
}

ENTITY_FIELDS = {
    "product": [("title", "str"), ("description", "str"), ("price", "float")],
    "order": [("product_id", "int"), ("quantity", "int"), ("status", "str")],
    "post": [("title", "str"), ("body", "str")],
    "comment": [("post_id", "int"), ("text", "str")],
    "task": [("title", "str"), ("done", "bool")],
    "appointment": [("client_name", "str"), ("datetime_iso", "str"), ("status", "str")],
    "transaction": [("amount", "float"), ("category", "str"), ("note", "str")],
    "course": [("title", "str"), ("description", "str")],
    "lesson": [("course_id", "int"), ("title", "str"), ("content", "str")],
    "message": [("author", "str"), ("text", "str")],
    "item": [("title", "str"), ("description", "str")],
}

PY_DEFAULTS = {"str": '""', "int": "0", "float": "0.0", "bool": "False"}

# Демо-интерфейс, встраиваемый в каждый сгенерированный проект (страница "/").
# Плейсхолдеры __TITLE__ и __CONFIG__ заменяются при генерации.
UI_HTML_TEMPLATE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
body { margin: 0; font-family: system-ui, sans-serif; background: #f4f5f7; color: #1d2330; }
header { background: #101828; color: #fff; padding: 20px 28px; }
header h1 { margin: 0 0 4px; font-size: 22px; }
header a { color: #9dc0ff; }
header p { margin: 0; color: #c7cdd8; font-size: 14px; }
main { max-width: 960px; margin: 24px auto; padding: 0 16px; display: grid; gap: 24px; }
section { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 1px 4px rgba(16,24,40,.08); }
h2 { margin-top: 0; text-transform: capitalize; }
form { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 14px; }
input[type=text], input[type=number] { padding: 8px 10px; border: 1px solid #cdd3de; border-radius: 8px; }
label.check { display: flex; align-items: center; gap: 6px; }
button { padding: 8px 14px; border: 0; border-radius: 8px; background: #2f6bff; color: #fff; cursor: pointer; }
button.del { background: #e8ebf0; color: #b3261e; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #eef0f4; }
.muted { color: #667085; }
</style>
</head>
<body>
<header>
<h1>__TITLE__</h1>
<p>MVP сгенерирован AI Technical Founder · <a href="/docs">Swagger API</a></p>
</header>
<main id="app"></main>
<script>
const ENTITIES = __CONFIG__;
const app = document.getElementById('app');

function makeInput(field) {
  if (field.type === 'bool') {
    const label = document.createElement('label');
    label.className = 'check';
    const box = document.createElement('input');
    box.type = 'checkbox';
    box.name = field.name;
    label.append(box, document.createTextNode(field.name));
    return label;
  }
  const input = document.createElement('input');
  input.name = field.name;
  if (field.type === 'int') { input.type = 'number'; input.step = '1'; }
  else if (field.type === 'float') { input.type = 'number'; input.step = '0.01'; }
  else { input.type = 'text'; }
  input.placeholder = field.name;
  input.required = field.type === 'str';
  return input;
}

function readValue(field, form) {
  const el = form.elements[field.name];
  if (field.type === 'bool') return el.checked;
  if (field.type === 'int') return parseInt(el.value || '0', 10);
  if (field.type === 'float') return parseFloat(el.value || '0');
  return el.value;
}

async function refresh(entity) {
  const rows = await (await fetch('/' + entity.name + 's')).json();
  const tbody = document.getElementById('tbody-' + entity.name);
  tbody.textContent = '';
  for (const row of rows) {
    const tr = document.createElement('tr');
    for (const col of ['id'].concat(entity.fields.map(f => f.name))) {
      const td = document.createElement('td');
      td.textContent = String(row[col]);
      tr.append(td);
    }
    const td = document.createElement('td');
    const del = document.createElement('button');
    del.className = 'del';
    del.textContent = 'Удалить';
    del.onclick = async () => {
      await fetch('/' + entity.name + 's/' + row.id, { method: 'DELETE' });
      refresh(entity);
    };
    td.append(del);
    tr.append(td);
    tbody.append(tr);
  }
  if (!rows.length) {
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.colSpan = entity.fields.length + 2;
    td.className = 'muted';
    td.textContent = 'Пока пусто — добавьте первую запись выше.';
    tr.append(td);
    tbody.append(tr);
  }
}

for (const entity of ENTITIES) {
  const section = document.createElement('section');
  const h2 = document.createElement('h2');
  h2.textContent = entity.name + 's';
  section.append(h2);

  const form = document.createElement('form');
  for (const field of entity.fields) form.append(makeInput(field));
  const submit = document.createElement('button');
  submit.textContent = 'Добавить';
  form.append(submit);
  form.onsubmit = async (event) => {
    event.preventDefault();
    const payload = {};
    for (const field of entity.fields) payload[field.name] = readValue(field, form);
    await fetch('/' + entity.name + 's', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    form.reset();
    refresh(entity);
  };
  section.append(form);

  const table = document.createElement('table');
  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  for (const col of ['id'].concat(entity.fields.map(f => f.name), [''])) {
    const th = document.createElement('th');
    th.textContent = col;
    headRow.append(th);
  }
  thead.append(headRow);
  const tbody = document.createElement('tbody');
  tbody.id = 'tbody-' + entity.name;
  table.append(thead, tbody);
  section.append(table);

  app.append(section);
  refresh(entity);
}
</script>
</body>
</html>
"""


def detect_entities(idea: str) -> list[str]:
    lowered = idea.lower()
    entities: list[str] = []
    for keyword, ents in DOMAIN_HINTS.items():
        if keyword in lowered:
            for ent in ents:
                if ent not in entities:
                    entities.append(ent)
    return entities or ["item"]


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "mvp-app"


class TemplateEngine:
    """Генерация без внешних зависимостей — гарантированный результат."""

    name = "template"

    def generate_vision(self, project_name: str, idea: str) -> str:
        entities = ", ".join(detect_entities(idea))
        return f"""# Project Vision — {project_name}

## Business Goal
Быстро проверить бизнес-идею: «{idea.strip()}» — с минимальными затратами,
получив работающий прототип с REST API.

## Target Audience
Ранние пользователи продукта и команда основателей, проверяющие спрос.

## MVP Scope
- REST API (FastAPI) с CRUD для ключевых сущностей: {entities}
- Веб-интерфейс для работы с данными (страница /)
- Автодокументация Swagger (/docs)
- Хранилище SQLite (без внешних сервисов)
- Docker-образ и docker-compose
- Автотесты (pytest)

## Future Scope
- Авторизация пользователей (JWT)
- PostgreSQL и миграции
- Платежи / уведомления (по домену идеи)
"""

    def generate_roadmap(self, project_name: str, idea: str) -> str:
        entities = detect_entities(idea)
        steps = ["Каркас FastAPI-приложения", "Модели данных и хранилище"]
        steps += [f"CRUD API для «{e}»" for e in entities]
        steps += ["Тесты pytest", "Dockerfile и docker-compose", "README и документация"]
        lines = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))
        return f"# Roadmap — {project_name}\n\n{lines}\n"

    def generate_architecture(self, project_name: str, idea: str) -> str:
        entities = ", ".join(detect_entities(idea))
        return f"""# Architecture — {project_name}

- **Backend:** FastAPI (Python) — быстрый старт, Swagger из коробки.
- **База:** SQLite через SQLAlchemy (для MVP; PostgreSQL — future scope).
- **Сущности:** {entities}
- **Контейнеризация:** Docker + docker-compose.
- **Тесты:** pytest + httpx TestClient.

```
[Client] -> [FastAPI: routers -> services -> SQLAlchemy] -> [SQLite]
```
"""

    def generate_structure(self, project_name: str, idea: str) -> str:
        entities = detect_entities(idea)
        slug = slugify(project_name)
        routers = "\n".join(f"│   │   ├── {e}s.py" for e in entities)
        return f"""# Structure — {project_name}

```
{slug}/
├── app/
│   ├── main.py
│   ├── ui.py            # веб-интерфейс (страница /)
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── routers/
{routers}
├── tests/
│   └── test_api.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```
"""

    def generate_code(self, project_name: str, idea: str) -> dict[str, str]:
        """Возвращает {путь: содержимое} запускаемого FastAPI-проекта."""
        project_name = project_name.strip()
        entities = detect_entities(idea)
        files: dict[str, str] = {}

        files["requirements.txt"] = (
            "fastapi==0.115.6\nuvicorn[standard]==0.34.0\nsqlalchemy==2.0.36\n"
            "pydantic==2.10.4\npytest==8.3.4\nhttpx==0.28.1\n"
        )

        files["app/__init__.py"] = ""
        files["app/database.py"] = '''from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

engine = create_engine("sqlite:///./app.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
'''

        model_defs, schema_defs, router_files, router_imports, router_includes = [], [], {}, [], []
        for entity in entities:
            cls = entity.capitalize()
            fields = ENTITY_FIELDS[entity]
            model_cols = "\n".join(
                f"    {fname}: Mapped[{ftype}] = mapped_column(default={PY_DEFAULTS[ftype]})"
                for fname, ftype in fields
            )
            model_defs.append(
                f'class {cls}(Base):\n    __tablename__ = "{entity}s"\n\n'
                f"    id: Mapped[int] = mapped_column(primary_key=True)\n{model_cols}\n"
            )
            schema_fields = "\n".join(f"    {fname}: {ftype}" for fname, ftype in fields)
            schema_defs.append(
                f"class {cls}Create(BaseModel):\n{schema_fields}\n\n\n"
                f"class {cls}Out({cls}Create):\n"
                "    model_config = ConfigDict(from_attributes=True)\n\n    id: int\n"
            )
            router_imports.append(f"from .routers import {entity}s")
            router_includes.append(f"app.include_router({entity}s.router)")
            router_files[f"app/routers/{entity}s.py"] = f'''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import {cls}
from ..schemas import {cls}Create, {cls}Out

router = APIRouter(prefix="/{entity}s", tags=["{entity}s"])


@router.get("", response_model=list[{cls}Out])
def list_{entity}s(db: Session = Depends(get_db)):
    return db.scalars(select({cls})).all()


@router.post("", response_model={cls}Out, status_code=201)
def create_{entity}(payload: {cls}Create, db: Session = Depends(get_db)):
    obj = {cls}(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{{item_id}}", response_model={cls}Out)
def get_{entity}(item_id: int, db: Session = Depends(get_db)):
    obj = db.get({cls}, item_id)
    if obj is None:
        raise HTTPException(404, "{cls} not found")
    return obj


@router.put("/{{item_id}}", response_model={cls}Out)
def update_{entity}(item_id: int, payload: {cls}Create, db: Session = Depends(get_db)):
    obj = db.get({cls}, item_id)
    if obj is None:
        raise HTTPException(404, "{cls} not found")
    for key, value in payload.model_dump().items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{{item_id}}", status_code=204)
def delete_{entity}(item_id: int, db: Session = Depends(get_db)):
    obj = db.get({cls}, item_id)
    if obj is None:
        raise HTTPException(404, "{cls} not found")
    db.delete(obj)
    db.commit()
'''

        files["app/models.py"] = (
            "from sqlalchemy.orm import Mapped, mapped_column\n\n"
            "from .database import Base\n\n\n" + "\n\n".join(model_defs)
        )
        files["app/schemas.py"] = (
            "from pydantic import BaseModel, ConfigDict\n\n\n" + "\n\n".join(schema_defs)
        )
        files["app/routers/__init__.py"] = ""
        files.update(router_files)

        ui_config = [
            {"name": e, "fields": [{"name": f, "type": t} for f, t in ENTITY_FIELDS[e]]}
            for e in entities
        ]
        ui_html = UI_HTML_TEMPLATE.replace("__TITLE__", project_name).replace(
            "__CONFIG__", json.dumps(ui_config, ensure_ascii=False)
        )
        files["app/ui.py"] = (
            '"""Демо-интерфейс проекта (страница /). Сгенерировано автоматически."""\n\n'
            'HTML = """' + ui_html + '"""\n'
        )

        imports_block = "\n".join(router_imports)
        includes_block = "\n".join(router_includes)
        files["app/main.py"] = f'''from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .database import Base, engine
from .ui import HTML as UI_HTML
{imports_block}

Base.metadata.create_all(bind=engine)

app = FastAPI(title="{project_name}")

{includes_block}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home() -> str:
    return UI_HTML


@app.get("/health")
def health():
    return {{"status": "ok"}}
'''

        first = entities[0]
        first_fields = ENTITY_FIELDS[first]
        payload = {f: {"str": "test", "int": 1, "float": 9.99, "bool": True}[t] for f, t in first_fields}
        files["tests/test_api.py"] = f'''from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {{"status": "ok"}}


def test_home_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "AI Technical Founder" in response.text


def test_crud_{first}():
    payload = {json.dumps(payload)}
    created = client.post("/{first}s", json=payload)
    assert created.status_code == 201
    item_id = created.json()["id"]
    assert client.get(f"/{first}s/{{item_id}}").status_code == 200
    assert client.delete(f"/{first}s/{{item_id}}").status_code == 204
'''

        files["Dockerfile"] = (
            "FROM python:3.12-slim\nWORKDIR /app\nCOPY requirements.txt .\n"
            "RUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\n"
            'CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]\n'
        )
        files["docker-compose.yml"] = (
            "services:\n  api:\n    build: .\n    ports:\n      - \"8000:8000\"\n"
        )
        entity_list = "\n".join(f"- `/{e}s` — CRUD для {e}" for e in entities)
        files["README.md"] = f"""# {project_name}

MVP, сгенерированный AI Technical Founder по идее:

> {idea.strip()}

## Запуск

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

или через Docker:

```bash
docker compose up --build
```

## Интерфейс

Откройте http://localhost:8000/ — готовая веб-страница с формами и таблицами
для работы с данными (порт зависит от параметра `--port` при запуске).

## API

Swagger: http://localhost:8000/docs

{entity_list}

## Тесты

```bash
pytest
```
"""
        return files


class LLMEngine(TemplateEngine):
    """Улучшает текстовые артефакты через LLM; код остаётся детерминированным,
    чтобы гарантировать запускаемость. При ошибке провайдера — молча откат к шаблону."""

    name = "llm"

    def _complete(self, prompt: str) -> str | None:
        try:
            response = httpx.post(
                f"{settings.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Ты — технический сооснователь. Отвечай кратким Markdown-документом на русском.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.4,
                },
                timeout=60,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception:
            return None

    def generate_vision(self, project_name: str, idea: str) -> str:
        result = self._complete(
            f"Составь Project Vision (Business Goal, Target Audience, MVP Scope, Future Scope) "
            f"для проекта «{project_name}». Идея: {idea}"
        )
        return result or super().generate_vision(project_name, idea)

    def generate_roadmap(self, project_name: str, idea: str) -> str:
        result = self._complete(
            f"Составь пошаговый roadmap разработки MVP для проекта «{project_name}». Идея: {idea}"
        )
        return result or super().generate_roadmap(project_name, idea)

    def generate_architecture(self, project_name: str, idea: str) -> str:
        result = self._complete(
            f"Опиши архитектуру MVP (FastAPI + SQLite + Docker) для проекта «{project_name}». Идея: {idea}"
        )
        return result or super().generate_architecture(project_name, idea)


def get_engine() -> TemplateEngine:
    if settings.llm_api_key:
        return LLMEngine()
    return TemplateEngine()
