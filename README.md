# Travel Agent

ИИ-агент для планирования поездок: мастер вопросов → план по дням, бюджет, чеклист и режим «на месте» (DeepSeek).

## Живой сайт

**https://ai-travel-assistant.ru**

Регистрация, сборка поездки, PDF, режимы «План / На месте / Воспоминания», Street Smart, ссылка для друзей.  
FAQ: https://ai-travel-assistant.ru/#/faq

Open-source код — здесь; продакшен — VPS (Docker + Caddy + HTTPS).

## Возможности

- Мастер: куда → срок + дата → бюджет → интересы
- 4 фазы: Brief, Itinerary, Budget, Checklist
- Слоты по времени, успеваемость пешком, погода от даты старта
- Ссылки на жильё и билеты (главные страницы сервисов)
- Режим «Я на месте» + перестройка дня
- **ОС поездки**: План / На месте / Воспоминания
- Street Smart: фразы, ловушки, вкус, квест дня
- Совместная ссылка `#/share/...` с голосами
- Чат «?», экспорт PDF / `.md`
- **Лимит генераций** + покупка через Telegram-бота и Tribute
- Docker Compose, автотесты, лимит LLM, кэш геокодинга

---

## Лимит генераций и оплата

### Как это видит пользователь

1. В шапке сайта счётчик, например `5/5` или `5/5 · TG`.
2. Нажал на счётчик → окно «Лимит генераций».
3. **Сначала** привязка Telegram (кнопка Login Widget). Без неё кнопки оплаты скрыты.
4. **После привязки** появляются пакеты → «Купить в боте».
5. Бот присылает ссылку Tribute (карта / СБП).
6. После оплаты кредиты начисляются на аккаунт автоматически.

**Что считается генерацией:** только полный запуск плана (`POST /api/trips/{id}/run`).  
Чат, Street Smart, пересборка дня из лимита **не** списываются (остаётся часовой rate-limit LLM).

| Источник | Сколько | Сгорает |
|----------|---------|---------|
| Бесплатно | 5 в календарный месяц (UTC) | да, с новым месяцем |
| Купленные кредиты | пакеты 10 / 30 / 100 | нет |

Пакеты по умолчанию: **10 → 299 ₽**, **30 → 699 ₽**, **100 → 1990 ₽**.

### Схема (для разработчика)

```text
Сайт: привязка Telegram (Login Widget)
   ↓
Бот /start или /buy → ссылки Tribute
   ↓
Оплата в мини-приложении Tribute
   ↓
Webhook → наш backend → credit_balance
```

Если оплатили **до** привязки TG, платёж лежит в `pending_credits` и зачислится при привязке (или при следующем `GET /api/auth/me`).

---

## Настройка оплаты (прод)

`.env` на сервере **не обновляется через git pull** — переменные дописываете вручную. Шаблон: [`.env.example`](.env.example).

### 1. Telegram-бот (@BotFather)

1. Создайте бота, сохраните токен.
2. **Login Widget** → домен сайта, например `ai-travel-assistant.ru` (без `https://`).
3. Выключите **Restrict bot usage**, если бот должен быть доступен всем.
4. В `.env`:

```env
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_BOT_USERNAME=TravelAgentPay_bot
```

5. Webhook бота:

```bash
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=https://ai-travel-assistant.ru/api/billing/telegram/webhook"
```

Команды бота: `/start`, `/buy`, `/buy10`, `/buy30`, `/buy100`.

### 2. Tribute (инфопродукты)

1. В @tribute создайте 3 digital-продукта в **RUB** (10 / 30 / 100 генераций).
2. **Ещё → API / Tribute Shop API**:
   - API Key → `TRIBUTE_API_KEY`
   - Webhook URL → `https://ai-travel-assistant.ru/api/billing/tribute/webhook`
3. Id и ссылки продуктов (пример из API `GET https://tribute.tg/api/v1/products`):

```env
TRIBUTE_API_KEY=...
TRIBUTE_PRODUCT_10=137719
TRIBUTE_PRODUCT_30=137720
TRIBUTE_PRODUCT_100=137722
TRIBUTE_LINK_10=https://t.me/tribute/app?startapp=pzPh
TRIBUTE_LINK_30=https://t.me/tribute/app?startapp=pzPi
TRIBUTE_LINK_100=https://t.me/tribute/app?startapp=pzPk
```

4. Пересоздайте backend:

```bash
docker compose up -d --force-recreate backend
```

Проверка webhook:

```bash
curl -sS https://ai-travel-assistant.ru/api/billing/tribute/webhook
# ожидается {"ok":true,...}
```

### 3. Ручное начисление (запасной вариант)

```env
ADMIN_CREDIT_TOKEN=длинный_секрет
```

```bash
curl -X POST https://ai-travel-assistant.ru/api/admin/credits \
  -H "X-Admin-Token: $ADMIN_CREDIT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@mail.ru","amount":10}'
```

### 4. Диагностика, если кредиты не пришли

```bash
docker compose logs backend --tail=200 | grep -i tribute

docker compose exec db psql -U travel -d travel -c \
  "SELECT id, status, credits, telegram_id, product_id, user_id FROM tribute_payments ORDER BY id DESC LIMIT 5;"

docker compose exec db psql -U travel -d travel -c \
  "SELECT id, telegram_id, credits, claimed_at FROM pending_credits ORDER BY id DESC LIMIT 5;"
```

- `pending` — TG ещё не привязан к аккаунту на сайте  
- `credited` — уже начислено  
- `bad signature` в логах — неверный `TRIBUTE_API_KEY`  
- пусто в `tribute_payments` — webhook не дошёл

---

## Секреты — важно

**Не коммитьте `.env` и файлы с ключами.**

В Git только [`.env.example`](.env.example).  
Рабочие ключи: локально `backend/.env` / корневой `.env`, на сервере — тот же корневой `.env` для Compose.

## Локальный запуск

Подробно: [INSTALL.md](INSTALL.md).

1. Скопируйте `.env.example` → `backend/.env` (и при Docker — в корневой `.env`)
2. Минимум: `LLM_API_KEY`, `JWT_SECRET`
3. **Windows:** `start.bat`  
   Или: backend `uvicorn` `:8000`, frontend `npm run dev` `:5173`
4. http://localhost:5173

### Docker

```bash
cp .env.example .env
# LLM_API_KEY, JWT_SECRET, POSTGRES_PASSWORD
# на своём домене: SITE_ADDRESS и CORS_ORIGINS
docker compose up --build -d
```

- Сайт: http://localhost  
- Health: http://localhost/api/health  
- Прод: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## Документация

- [INSTALL.md](INSTALL.md) — установка с нуля  
- [docs/API.md](docs/API.md)  
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)  
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## Тесты

```bash
cd backend
pytest
```

## Лицензия

[MIT](LICENSE) — можно использовать, менять и развивать форки. Прод-ключи и данные пользователей в репозиторий не входят.
