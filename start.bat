@echo off
chcp 65001 >nul
title Travel Agent
cd /d "%~dp0"

echo.
echo  === Travel Agent ===
echo.

if not exist "backend\.env" (
  echo  [!] Нет файла backend\.env
  echo      Скопируйте .env.example в backend\.env и вставьте LLM_API_KEY DeepSeek.
  echo.
  pause
  exit /b 1
)

findstr /C:"LLM_API_KEY=sk-" "backend\.env" >nul 2>&1
if errorlevel 1 (
  findstr /R /C:"LLM_API_KEY=.\+" "backend\.env" >nul 2>&1
  if errorlevel 1 (
    echo  [!] В backend\.env пустой LLM_API_KEY — агент не сможет планировать.
    echo      Получите ключ: https://platform.deepseek.com
    echo.
  )
)

where py >nul 2>&1
if errorlevel 1 (
  echo  [!] Python не найден. Установите: winget install Python.Python.3.12
  pause
  exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
  echo  [!] Node.js / npm не найден. Установите: winget install OpenJS.NodeJS.LTS
  pause
  exit /b 1
)

if not exist "frontend\node_modules\" (
  echo  Устанавливаю зависимости frontend...
  pushd frontend
  call npm install
  if errorlevel 1 (
    echo  [!] npm install не удался
    popd
    pause
    exit /b 1
  )
  popd
)

echo  Запускаю backend на :8000 ...
start "Travel Agent Backend" cmd /k "cd /d "%~dp0backend" && py -m uvicorn app.main:app --port 8000"

timeout /t 2 /nobreak >nul

echo  Запускаю frontend на :5173 ...
start "Travel Agent Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

timeout /t 3 /nobreak >nul
start "" "http://localhost:5173"

echo.
echo  Готово. Откройте http://localhost:5173
echo  Окна Backend и Frontend не закрывайте, пока пользуетесь сайтом.
echo  Чтобы остановить — закройте оба окна или Ctrl+C в каждом.
echo  Подробнее: INSTALL.md
echo.
pause
