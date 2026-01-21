# Quick Start Script for DrAssistent
# Assumes all dependencies are already installed

Write-Host "Starting DrAssistent..." -ForegroundColor Cyan

# Check if virtual environment exists
if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run install.ps1 first to set up the environment." -ForegroundColor Yellow
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& "venv\Scripts\Activate.ps1"

# Check if Docker is running
$dockerRunning = docker ps 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker is not running. Starting Docker containers..." -ForegroundColor Yellow
    Push-Location backend
    docker-compose up -d db
    Pop-Location
    Start-Sleep -Seconds 5
}

# Navigate to backend
Push-Location backend

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "Warning: .env file not found!" -ForegroundColor Yellow
    Write-Host "Please create backend\.env file with your configuration." -ForegroundColor Yellow
}

# Run the application
Write-Host "Starting FastAPI application..." -ForegroundColor Green
Write-Host "API will be available at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "API docs at: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Pop-Location
