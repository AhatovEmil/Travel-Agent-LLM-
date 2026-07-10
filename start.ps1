# Travel Agent — запуск одной командой (PowerShell)
# Использование: .\start.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host " === Travel Agent ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path "backend\.env")) {
  Write-Host "[!] Нет backend\.env — скопируйте .env.example и добавьте LLM_API_KEY" -ForegroundColor Red
  exit 1
}

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
  Write-Host "[!] Python (py) не найден" -ForegroundColor Red
  exit 1
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  Write-Host "[!] npm не найден" -ForegroundColor Red
  exit 1
}

if (-not (Test-Path "frontend\node_modules")) {
  Write-Host "Устанавливаю frontend зависимости..."
  Push-Location frontend
  npm install
  Pop-Location
}

Write-Host "Backend :8000 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; py -m uvicorn app.main:app --port 8000"

Start-Sleep -Seconds 2

Write-Host "Frontend :5173 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev"

Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "Откройте http://localhost:5173" -ForegroundColor Green
Write-Host "Не закрывайте окна Backend и Frontend. Подробнее: INSTALL.md"
Write-Host ""
