@echo off
REM DrAssistent Installation Batch Script for Windows
REM This script can run without PowerShell execution policy restrictions

echo ========================================
echo DrAssistent Installation Script
echo ========================================
echo.

REM Check Python
echo [1/7] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed!
    echo Please download and install Python 3.11+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)
python --version
echo Python found!
echo.

REM Check Docker
echo [2/7] Checking Docker installation...
docker --version >nul 2>&1
if errorlevel 1 (
    echo Docker is not installed!
    echo Please download and install Docker Desktop from https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)
docker --version
echo Docker found!
echo.

REM Create virtual environment
echo [3/7] Creating virtual environment...
if exist venv (
    echo Virtual environment already exists. Removing old one...
    rmdir /s /q venv
)
python -m venv venv
if errorlevel 1 (
    echo Error creating virtual environment!
    pause
    exit /b 1
)
echo Virtual environment created!
echo.

REM Activate and upgrade pip
echo [4/7] Upgrading pip...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 (
    echo Error upgrading pip!
    pause
    exit /b 1
)
echo Pip upgraded!
echo.

REM Install dependencies
echo [5/7] Installing Python dependencies...
echo This may take 10-20 minutes, please be patient...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error installing dependencies!
    echo Try running: pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
    pause
    exit /b 1
)
echo Dependencies installed!
echo.

REM Start database
echo [6/7] Starting PostgreSQL database...
cd backend
docker-compose up -d db
if errorlevel 1 (
    echo Error starting database!
    echo Trying manual docker command...
    docker run -d --name drassistent-db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=drassistent -p 5432:5432 -v postgres_data:/var/lib/postgresql/data postgres:15-alpine
)
echo Waiting for database to start...
timeout /t 10 /nobreak >nul
cd ..
echo Database started!
echo.

REM Create .env file
echo [7/7] Creating environment file...
cd backend
if exist .env (
    echo .env file already exists. Skipping creation.
) else (
    (
        echo DATABASE_URL=postgresql://postgres:postgres@localhost:5432/drassistent
        echo POSTGRES_USER=postgres
        echo POSTGRES_PASSWORD=postgres
        echo POSTGRES_DB=drassistent
        echo API_V1_PREFIX=/api/v1
        echo PROJECT_NAME=DrAssistent API
        echo DEBUG=True
        echo ENVIRONMENT=development
        echo SECRET_KEY=your-secret-key-here-change-in-production
        echo ALGORITHM=HS256
        echo ACCESS_TOKEN_EXPIRE_MINUTES=30
        echo OPENROUTER_API_KEY=sk-or-v1-placeholder-get-from-openrouter-ai
        echo DIET_PLAN_MODEL=anthropic/claude-3.5-sonnet
        echo DIET_PLAN_TEMPERATURE=0.7
        echo FOOD_ENRICHMENT_MODEL=qwen/qwen-2.5-72b-instruct
        echo FOOD_ENRICHMENT_TEMPERATURE=0.3
        echo LOG_LEVEL=INFO
        echo LOG_FILE=logs/app.log
    ) > .env
    echo .env file created!
    echo IMPORTANT: Please update OPENROUTER_API_KEY in backend\.env with your actual API key!
)
cd ..
echo.

echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Update backend\.env with your OpenRouter API key
echo 2. Run: venv\Scripts\activate.bat
echo 3. Run: cd backend
echo 4. Run: python -m alembic upgrade head
echo 5. Run: uvicorn app.main:app --reload
echo.
echo API will be available at: http://localhost:8000
echo API docs at: http://localhost:8000/docs
echo.
pause
