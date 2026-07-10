# Travel Agent

ИИ-агент для планирования поездок: мастер вопросов → план по дням, бюджет, чеклист и режим «на месте» (DeepSeek).

## Живой сайт

Всё из этого репозитория уже развёрнуто и работает онлайн:

**https://ai-travel-assistant.ru**

Там можно зарегистрироваться, собрать поездку, скачать PDF, открыть режимы «План / На месте / Воспоминания», Street Smart и ссылку для друзей. FAQ: https://ai-travel-assistant.ru/#/faq

Open-source код — здесь; продакшен крутится на VPS (Docker + Caddy + HTTPS).

## Возможности

- Мастер: куда → срок + дата → бюджет → интересы
- 4 фазы: Brief, Itinerary, Budget, Checklist
- Слоты по времени, успеваемость пешком, погода от даты старта
- Deep links: жильё и билеты
- Режим «Я на месте» + перестройка дня (опоздание / дождь)
- **ОС поездки**: План / На месте / Воспоминания — брифинг, вечерний чекин, дневник
- Street Smart: фразы, ловушки, вкус, квест дня, arrival
- Совместная ссылка `#/share/...` с голосами
- Чат «?», экспорт PDF / `.md`
- Docker Compose, автотесты, лимит LLM, кэш геокодинга

## Секреты — важно

**Не коммитьте `.env` и любые файлы с ключами.**

В Git допускается только шаблон [`.env.example`](.env.example) (без реальных `LLM_API_KEY` / `JWT_SECRET`).  
Рабочие ключи храните локально в `backend/.env` или корневом `.env` и на сервере — они в [`.gitignore`](.gitignore).

## Локальный запуск

Подробно: [INSTALL.md](INSTALL.md).

Кратко:

1. Скопируйте `.env.example` → `backend/.env` (и при Docker — в корневой `.env`)
2. Заполните минимум:
   - `LLM_API_KEY` — ключ [DeepSeek](https://platform.deepseek.com)
   - `JWT_SECRET` — любая длинная случайная строка
3. **Windows:** `start.bat`  
   **Или вручную:** backend `uvicorn` на `:8000`, frontend `npm run dev` на `:5173`
4. Откройте http://localhost:5173

### Docker (локально / как на проде)

```bash
cp .env.example .env
# заполните LLM_API_KEY, JWT_SECRET
# на своём домене: SITE_ADDRESS и CORS_ORIGINS
docker compose up --build -d
```

- Сайт: http://localhost  
- Health: http://localhost/api/health  
- Выкладка на VPS: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

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
