# Как поставить Travel Agent

Это не «enterprise deployment guide», а обычная инструкция: что скачать, куда ткнуть, куда вписать ключ.

Работает на **Windows** и **macOS**. Ниже — оба варианта.

---

## Зачем вообще DeepSeek

Агент сам поездки не выдумывает из воздуха — он ходит в нейросеть DeepSeek. Без ключа сайт откроется, а «Спланировать» выдаст ошибку. Ключ платный, но копеечный: доллар-два на счету хватает надолго.

---

## Шаг 1. Поставьте Python и Node

### Windows

Откройте PowerShell и выполните по очереди:

```powershell
winget install -e --id Python.Python.3.12
winget install -e --id OpenJS.NodeJS.LTS
```

Потом **закройте PowerShell и откройте новый** — иначе он не увидит свежие программы.

Проверка:

```powershell
py --version
npm --version
```

### macOS

Откройте **Terminal** (Программы → Утилиты → Терминал).

Если есть Homebrew (если нет — поставьте с [brew.sh](https://brew.sh)):

```bash
brew install python@3.12 node
```

Без Homebrew можно скачать установщики с [python.org](https://www.python.org/downloads/) и [nodejs.org](https://nodejs.org/) (LTS).

Проверка:

```bash
python3 --version
npm --version
```

Если обе команды ответили версией — ок, идём дальше.

---

## Шаг 2. Возьмите ключ DeepSeek

1. Зайдите на [platform.deepseek.com](https://platform.deepseek.com) и зарегистрируйтесь.
2. Слева найдите **API Keys**, создайте ключ, скопируйте его (начинается с `sk-`).
3. Пополните баланс на пару долларов в **Top up** — иначе после пары запросов упрётесь в «нет денег».

Ключ никому не отправляйте и не коммитьте в git. Он живёт только у вас в `.env`.

---

## Шаг 3. Положите ключ в проект

### Windows

```powershell
cd C:\Users\Admin\Desktop\project
copy .env.example backend\.env
notepad backend\.env
```

### macOS

```bash
cd ~/Desktop/project   # или куда вы положили папку
cp .env.example backend/.env
open -e backend/.env   # откроется в TextEdit; можно nano backend/.env
```

В файле должно получиться примерно так (свой ключ вместо примера):

```
JWT_SECRET=change-me-in-production
LLM_API_KEY=sk-сюда_ваш_ключ
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
LLM_MODEL_FALLBACKS=deepseek-reasoner
```

Сохранили — закрыли редактор.

---

## Шаг 4. Запустите

### Windows

Самый ленивый способ: дважды кликнуть **`start.bat`** в папке проекта.

Он поднимет два окна (backend и frontend) и откроет браузер на http://localhost:5173.

Пока пользуетесь сайтом — эти два окна не закрывайте. Надоело — закройте их или Ctrl+C в каждом.

Если `start.bat` ругается на отсутствие `.env` или ключа — вернитесь к шагу 3.

### macOS

`start.bat` на Mac не работает — запускаем двумя терминалами.

**Терминал 1 — backend:**

```bash
cd ~/Desktop/project/backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --port 8000
```

**Терминал 2 — frontend:**

```bash
cd ~/Desktop/project/frontend
npm install
npm run dev
```

Откройте в браузере: http://localhost:5173

Окна терминалов не закрывайте, пока пользуетесь сайтом. Остановить — Ctrl+C в каждом.

`npm install` и `pip install` нужны только в первый раз (или после обновления зависимостей).

---

## Шаг 5. Попробуйте поездку

1. Зарегистрируйтесь на сайте (любой email/пароль — это локальный аккаунт).
2. Пройдите мастер: куда едете, на сколько дней, **дата начала**, бюджет, что любите.
3. Подождите минуту-две, пока крутятся фазы.
4. Откройте план по дням — слоты, карта, погода.
5. Если надо — «Скачать PDF» или «.md». Ссылку для друзей можно скопировать с страницы поездки.

Цены и адреса от нейросети — ориентир, перед реальной поездкой перепроверьте.

---

## Если что-то сломалось

**«LLM_API_KEY не задан»** — ключ пустой или backend запущен не из той папки. Проверьте `backend/.env` и перезапустите backend.

**Ошибка про баланс / 402** — на DeepSeek кончились деньги, пополните.

**Порт 5173 занят** — где-то уже висит старый `npm run dev`. Закройте лишний процесс и запустите снова.

**Windows: py или npm «не найдены»** — новое окно PowerShell после установки из шага 1.

**Mac: `python3` / `npm` «command not found»** — Python/Node не в PATH. Переустановите через Homebrew и откройте **новый** Terminal.

**PDF не скачивается / ошибка шрифта (чаще на Mac)** — в `backend/.env` добавьте путь к шрифту с кириллицей, например:

```
PDF_FONT_PATH=/System/Library/Fonts/Supplemental/Arial Unicode.ttf
```

Потом перезапустите backend.

---

## Если вы разработчик и хотите руками

### Windows

```powershell
cd backend
py -m pip install -r requirements.txt
py -m uvicorn app.main:app --port 8000
```

Второе окно:

```powershell
cd frontend
npm install
npm run dev
```

Тесты: `cd backend` → `py -m pytest`.

### macOS

```bash
cd backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --port 8000
```

Второе окно:

```bash
cd frontend
npm install
npm run dev
```

Тесты: `cd backend` → `python3 -m pytest`.

### Docker (Windows и Mac)

Скопируйте `.env.example` в `.env` в корне проекта, впишите `LLM_API_KEY` и при желании смените `JWT_SECRET`, затем:

```bash
docker compose up --build
```

Сайт: **http://localhost** (Caddy на порту 80). Проверка API: http://localhost/api/health.

Для выкладки на VPS с доменом и HTTPS — [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
