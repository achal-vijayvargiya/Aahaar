# DrAssistent Installation Script for Windows
# This script installs all required dependencies for the DrAssistent platform

param(
    [switch]$SkipDocker,
    [switch]$SkipPython,
    [switch]$SkipDatabase,
    [string]$PythonVersion = "3.11"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DrAssistent Installation Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Function to check if a command exists
function Test-Command {
    param($CommandName)
    $null = Get-Command $CommandName -ErrorAction SilentlyContinue
    return $?
}

# Function to check Python version
function Test-PythonVersion {
    if (Test-Command python) {
        $version = python --version 2>&1 | Out-String
        Write-Host "Found Python: $version" -ForegroundColor Green
        $majorVersion = (python -c "import sys; print(sys.version_info.major)" 2>&1)
        $minorVersion = (python -c "import sys; print(sys.version_info.minor)" 2>&1)
        if ($majorVersion -eq 3 -and $minorVersion -ge 11) {
            return $true
        }
    }
    return $false
}

# Function to install Python
function Install-Python {
    Write-Host "`n[1/6] Installing Python $PythonVersion..." -ForegroundColor Yellow
    
    $pythonUrl = "https://www.python.org/ftp/python/${PythonVersion}.0/python-${PythonVersion}.0-amd64.exe"
    $installerPath = "$env:TEMP\python-installer.exe"
    
    Write-Host "Downloading Python installer..." -ForegroundColor Cyan
    try {
        Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath -UseBasicParsing
        Write-Host "Installing Python (this may take a few minutes)..." -ForegroundColor Cyan
        Start-Process -FilePath $installerPath -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_test=0" -Wait
        Remove-Item $installerPath -Force
        
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        
        Write-Host "Python installed successfully!" -ForegroundColor Green
    } catch {
        Write-Host "Error installing Python: $_" -ForegroundColor Red
        Write-Host "Please install Python $PythonVersion manually from https://www.python.org/downloads/" -ForegroundColor Yellow
        exit 1
    }
}

# Function to install Docker Desktop
function Install-DockerDesktop {
    Write-Host "`n[2/6] Installing Docker Desktop..." -ForegroundColor Yellow
    
    if (Test-Command docker) {
        Write-Host "Docker is already installed!" -ForegroundColor Green
        docker --version
        return
    }
    
    $dockerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
    $installerPath = "$env:TEMP\docker-installer.exe"
    
    Write-Host "Downloading Docker Desktop installer..." -ForegroundColor Cyan
    try {
        Invoke-WebRequest -Uri $dockerUrl -OutFile $installerPath -UseBasicParsing
        Write-Host "Installing Docker Desktop (this will require a restart)..." -ForegroundColor Cyan
        Write-Host "Please follow the installation wizard and restart your computer when prompted." -ForegroundColor Yellow
        Start-Process -FilePath $installerPath -Wait
        
        Write-Host "`nDocker Desktop installer launched. Please complete the installation and restart your computer." -ForegroundColor Yellow
        Write-Host "After restart, run this script again with -SkipDocker flag to continue." -ForegroundColor Yellow
        exit 0
    } catch {
        Write-Host "Error downloading Docker Desktop: $_" -ForegroundColor Red
        Write-Host "Please download and install Docker Desktop manually from https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
        exit 1
    }
}

# Function to verify Docker is running
function Test-DockerRunning {
    if (-not (Test-Command docker)) {
        return $false
    }
    
    try {
        docker ps 2>&1 | Out-Null
        return $true
    } catch {
        return $false
    }
}

# Function to setup PostgreSQL database
function Setup-PostgreSQL {
    Write-Host "`n[3/6] Setting up PostgreSQL database..." -ForegroundColor Yellow
    
    if (-not (Test-DockerRunning)) {
        Write-Host "Docker is not running. Please start Docker Desktop and try again." -ForegroundColor Red
        return $false
    }
    
    Write-Host "Creating PostgreSQL container..." -ForegroundColor Cyan
    
    # Check if container already exists
    $existingContainer = docker ps -a --filter "name=drassistent-db" --format "{{.Names}}" 2>&1
    if ($existingContainer -eq "drassistent-db") {
        Write-Host "PostgreSQL container already exists. Starting it..." -ForegroundColor Yellow
        docker start drassistent-db
    } else {
        Write-Host "Creating new PostgreSQL container..." -ForegroundColor Cyan
        docker run -d `
            --name drassistent-db `
            -e POSTGRES_USER=postgres `
            -e POSTGRES_PASSWORD=postgres `
            -e POSTGRES_DB=drassistent `
            -p 5432:5432 `
            -v postgres_data:/var/lib/postgresql/data `
            postgres:15-alpine
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Error creating PostgreSQL container" -ForegroundColor Red
            return $false
        }
    }
    
    Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Cyan
    $maxAttempts = 30
    $attempt = 0
    while ($attempt -lt $maxAttempts) {
        $result = docker exec drassistent-db pg_isready -U postgres 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "PostgreSQL is ready!" -ForegroundColor Green
            return $true
        }
        Start-Sleep -Seconds 2
        $attempt++
        Write-Host "." -NoNewline -ForegroundColor Gray
    }
    
    Write-Host "`nPostgreSQL did not become ready in time. Please check Docker logs." -ForegroundColor Yellow
    return $false
}

# Function to create virtual environment
function Setup-VirtualEnvironment {
    Write-Host "`n[4/6] Setting up Python virtual environment..." -ForegroundColor Yellow
    
    $venvPath = "venv"
    
    if (Test-Path $venvPath) {
        Write-Host "Virtual environment already exists. Removing old one..." -ForegroundColor Yellow
        Remove-Item -Path $venvPath -Recurse -Force
    }
    
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv $venvPath
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error creating virtual environment" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & "$venvPath\Scripts\Activate.ps1"
    
    Write-Host "Upgrading pip..." -ForegroundColor Cyan
    python -m pip install --upgrade pip
    
    Write-Host "Virtual environment created successfully!" -ForegroundColor Green
}

# Function to install Python dependencies
function Install-PythonDependencies {
    Write-Host "`n[5/6] Installing Python dependencies..." -ForegroundColor Yellow
    
    if (-not (Test-Path "venv\Scripts\python.exe")) {
        Write-Host "Virtual environment not found. Please run the script from the beginning." -ForegroundColor Red
        exit 1
    }
    
    $venvPython = "venv\Scripts\python.exe"
    
    Write-Host "Installing requirements (this may take several minutes)..." -ForegroundColor Cyan
    
    # Install requirements.txt
    if (Test-Path "requirements.txt") {
        Write-Host "Installing from requirements.txt..." -ForegroundColor Cyan
        & $venvPython -m pip install -r requirements.txt
    } elseif (Test-Path "backend\requirements.txt") {
        Write-Host "Installing from backend/requirements.txt..." -ForegroundColor Cyan
        & $venvPython -m pip install -r backend\requirements.txt
    } else {
        Write-Host "No requirements.txt found!" -ForegroundColor Red
        exit 1
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error installing dependencies. Please check the error messages above." -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Dependencies installed successfully!" -ForegroundColor Green
}

# Function to create .env file
function Setup-EnvironmentFile {
    Write-Host "`n[6/6] Setting up environment configuration..." -ForegroundColor Yellow
    
    $envPath = "backend\.env"
    $envTemplate = @"
# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/drassistent
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=drassistent

# API Configuration
API_V1_PREFIX=/api/v1
PROJECT_NAME=DrAssistent API
DEBUG=True
ENVIRONMENT=development

# Security
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OpenRouter AI Configuration
# Get your API key from https://openrouter.ai/
OPENROUTER_API_KEY=sk-or-v1-placeholder-get-from-openrouter-ai
DIET_PLAN_MODEL=anthropic/claude-3.5-sonnet
DIET_PLAN_TEMPERATURE=0.7
FOOD_ENRICHMENT_MODEL=qwen/qwen-2.5-72b-instruct
FOOD_ENRICHMENT_TEMPERATURE=0.3

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
"@
    
    if (Test-Path $envPath) {
        Write-Host ".env file already exists. Skipping creation." -ForegroundColor Yellow
        Write-Host "Please verify your .env file contains the correct configuration." -ForegroundColor Cyan
    } else {
        Write-Host "Creating .env file..." -ForegroundColor Cyan
        Set-Content -Path $envPath -Value $envTemplate
        Write-Host ".env file created at $envPath" -ForegroundColor Green
        Write-Host "IMPORTANT: Please update OPENROUTER_API_KEY in $envPath with your actual API key!" -ForegroundColor Yellow
    }
}

# Function to run database migrations
function Run-DatabaseMigrations {
    Write-Host "`nRunning database migrations..." -ForegroundColor Yellow
    
    if (-not (Test-Path "backend\alembic.ini")) {
        Write-Host "Alembic configuration not found. Skipping migrations." -ForegroundColor Yellow
        return
    }
    
    Push-Location backend
    
    try {
        $venvPython = "..\venv\Scripts\python.exe"
        Write-Host "Running Alembic migrations..." -ForegroundColor Cyan
        & $venvPython -m alembic upgrade head
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Database migrations completed successfully!" -ForegroundColor Green
        } else {
            Write-Host "Warning: Database migrations may have failed. Please check the output above." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "Error running migrations: $_" -ForegroundColor Yellow
    } finally {
        Pop-Location
    }
}

# Main installation flow
Write-Host "Starting installation process..." -ForegroundColor Cyan
Write-Host ""

# Step 1: Check/Install Python
if (-not $SkipPython) {
    if (-not (Test-PythonVersion)) {
        Write-Host "Python $PythonVersion or higher is required but not found." -ForegroundColor Yellow
        $installPython = Read-Host "Do you want to install Python $PythonVersion? (Y/N)"
        if ($installPython -eq "Y" -or $installPython -eq "y") {
            Install-Python
            Write-Host "Please restart your terminal and run this script again." -ForegroundColor Yellow
            exit 0
        } else {
            Write-Host "Python installation skipped. Please install Python $PythonVersion manually." -ForegroundColor Yellow
            exit 1
        }
    }
} else {
    Write-Host "Skipping Python check..." -ForegroundColor Yellow
}

# Step 2: Check/Install Docker
if (-not $SkipDocker) {
    if (-not (Test-Command docker)) {
        Write-Host "Docker Desktop is not installed." -ForegroundColor Yellow
        $installDocker = Read-Host "Do you want to install Docker Desktop? (Y/N)"
        if ($installDocker -eq "Y" -or $installDocker -eq "y") {
            Install-DockerDesktop
        } else {
            Write-Host "Docker installation skipped. You can install it later." -ForegroundColor Yellow
        }
    } else {
        Write-Host "Docker is installed!" -ForegroundColor Green
        docker --version
    }
} else {
    Write-Host "Skipping Docker check..." -ForegroundColor Yellow
}

# Step 3: Setup PostgreSQL
if (-not $SkipDatabase) {
    if (Test-DockerRunning) {
        Setup-PostgreSQL
    } else {
        Write-Host "Docker is not running. Skipping database setup." -ForegroundColor Yellow
        Write-Host "Please start Docker Desktop and run: docker-compose up -d db" -ForegroundColor Cyan
    }
} else {
    Write-Host "Skipping database setup..." -ForegroundColor Yellow
}

# Step 4: Setup Virtual Environment
Setup-VirtualEnvironment

# Step 5: Install Python Dependencies
Install-PythonDependencies

# Step 6: Setup Environment File
Setup-EnvironmentFile

# Step 7: Run Database Migrations
if (Test-DockerRunning) {
    $runMigrations = Read-Host "`nDo you want to run database migrations now? (Y/N)"
    if ($runMigrations -eq "Y" -or $runMigrations -eq "y") {
        Run-DatabaseMigrations
    }
}

# Final instructions
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Update backend\.env with your OpenRouter API key" -ForegroundColor White
Write-Host "2. Activate the virtual environment: .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "3. Navigate to backend directory: cd backend" -ForegroundColor White
Write-Host "4. Run the application: uvicorn app.main:app --reload" -ForegroundColor White
Write-Host ""
Write-Host "Or use Docker Compose:" -ForegroundColor Yellow
Write-Host "  cd backend" -ForegroundColor White
Write-Host "  docker-compose up" -ForegroundColor White
Write-Host ""
Write-Host "Database will be available at: localhost:5432" -ForegroundColor Cyan
Write-Host "API will be available at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "API docs at: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
