@echo off
REM Quick Start Script for DrAssistent
REM Assumes installation is complete

echo Starting DrAssistent...
echo.

REM Check if virtual environment exists
if not exist venv\Scripts\python.exe (
    echo Virtual environment not found!
    echo Please run install.bat first to set up the environment.
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if Docker is running
docker ps >nul 2>&1
if errorlevel 1 (
    echo Docker is not running. Starting database...
    cd backend
    docker-compose up -d db
    timeout /t 5 /nobreak >nul
    cd ..
)

REM Navigate to backend
cd backend

REM Check if .env exists
if not exist .env (
    echo Warning: .env file not found!
    echo Please create backend\.env file with your configuration.
    pause
)

REM Start the application
echo.
echo ========================================
echo Starting FastAPI Application
echo ========================================
echo API will be available at: http://localhost:8000
echo API docs at: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
