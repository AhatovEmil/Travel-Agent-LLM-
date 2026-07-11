# Deployment — Travel Agent

Локальная установка без Docker: [INSTALL.md](../INSTALL.md).

## Docker Compose (рекомендуется для VPS)

Один вход через **Caddy**: HTTP/HTTPS на портах 80/443. Frontend и backend снаружи не торчат.

```mermaid
flowchart LR
  User[Browser] --> Caddy
  Caddy -->|"/"| Frontend
  Caddy -->|"/api"| Backend
  Backend --> Postgres
```

### 1. VPS и DNS

1. Арендуйте VPS (Timeweb, Selectel, Hetzner и т.п.) с Ubuntu 22.04+.
2. Установите Docker: https://docs.docker.com/engine/install/
3. Привяжите домен: A-запись `@` (и при желании `www`) → IP сервера.
4. Откройте порты **80** и **443** в firewall.

### 2. Код и `.env`

```bash
git clone <ваш-репозиторий> travel-agent
cd travel-agent
cp .env.example .env
nano .env
```

Обязательно задайте:

| Переменная | Пример | Зачем |
|---|---|---|
| `JWT_SECRET` | `openssl rand -hex 32` | подпись сессий (≥32 символов) |
| `POSTGRES_PASSWORD` | сильный пароль | БД (compose без fallback) |
| `LLM_API_KEY` | `sk-…` | DeepSeek |
| `SITE_ADDRESS` | `travel.example.com` | домен для Caddy / HTTPS |
| `CORS_ORIGINS` | `https://travel.example.com` | CORS (не `*` на проде) |
| `ENVIRONMENT` | `production` | жёсткие проверки секретов |

Локально без домена: `SITE_ADDRESS=localhost`, `CORS_ORIGINS=http://localhost,https://localhost`.  
Для локального Docker без строгих проверок: `ENVIRONMENT=development`.

```bash
# сгенерировать секрет
openssl rand -hex 32
```

### 3. Запуск

```bash
docker compose up --build -d
```

Проверка:

- Сайт: `https://ваш-домен` (или `http://localhost`)
- Health: `https://ваш-домен/api/health` → `{"status":"ok"}`
- Логи: `docker compose logs -f caddy backend`
- В production `/docs` и `/openapi.json` отключены

### 4. Прод-чеклист

- [ ] Сильный `JWT_SECRET` (≥32) и `POSTGRES_PASSWORD` (не дефолты)
- [ ] `CORS_ORIGINS` = ваш HTTPS-домен (без `*`)
- [ ] `ENVIRONMENT=production`
- [ ] DNS указывает на VPS, порты 80/443 открыты; SSH по ключу
- [ ] При необходимости `REGISTRATION_ENABLED=false`
- [ ] Бэкап volume `pgdata` (и при желании `caddy_data`)
- [ ] Ключ DeepSeek с балансом

### Env (справка)

| Переменная | Обязательна | Описание |
|---|---|---|
| `JWT_SECRET` | да | Секрет JWT (≥32 в production) |
| `POSTGRES_PASSWORD` | да (compose) | Пароль Postgres |
| `LLM_API_KEY` | да | Ключ DeepSeek |
| `SITE_ADDRESS` | да | Хост для Caddy |
| `CORS_ORIGINS` | да (прод) | Разрешённые origin |
| `ENVIRONMENT` | нет | `production` / `development` |
| `REGISTRATION_ENABLED` | нет | `false` — закрыть регистрацию |
| `LLM_BASE_URL` | нет | По умолчанию DeepSeek |
| `LLM_MODEL` | нет | `deepseek-chat` |
| `DATABASE_URL` | нет | В compose задаётся автоматически (Postgres) |

### Безопасность (что уже включено)

- Проверка `JWT_SECRET` / CORS при `ENVIRONMENT=production`
- Rate limit на login/register и публичные share-эндпоинты
- Security headers в Caddy (HSTS, nosniff, frame deny)
- Отзыв share-ссылки (`DELETE /api/trips/{id}/share`)
- OpenAPI `/docs` выключен в production

### Обновление

```bash
git pull
docker compose up --build -d
```
