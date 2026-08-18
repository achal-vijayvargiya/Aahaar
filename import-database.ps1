# Database Import Script for Windows PowerShell
# Imports data from local PostgreSQL database to Docker container

param(
    [string]$LocalDbHost = "localhost",
    [int]$LocalDbPort = 5432,
    [string]$LocalDbUser = "postgres",
    [string]$LocalDbName = "drassistent",
    [string]$DockerContainer = "drassistent-db",
    [string]$DockerDbName = "drassistent",
    [string]$DockerDbUser = "postgres",
    [ValidateSet("plain", "custom")]
    [string]$DumpFormat = "plain"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Green
Write-Host "Database Import Script" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Backup file name with timestamp
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
if ($DumpFormat -eq "custom") {
    $BackupFile = "backup_$timestamp.dump"
} else {
    $BackupFile = "backup_$timestamp.sql"
}

# Check if Docker container is running
Write-Host "[1/5] Checking Docker container..." -ForegroundColor Yellow
$containerRunning = docker ps --filter "name=$DockerContainer" --format "{{.Names}}" | Select-String -Pattern $DockerContainer
if (-not $containerRunning) {
    Write-Host "Error: Docker container '$DockerContainer' is not running!" -ForegroundColor Red
    Write-Host "Start it with: docker-compose up -d db" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ Docker container is running" -ForegroundColor Green
Write-Host ""

# Check if pg_dump is available
Write-Host "[2/5] Checking pg_dump availability..." -ForegroundColor Yellow
try {
    $null = Get-Command pg_dump -ErrorAction Stop
    Write-Host "✓ pg_dump is available" -ForegroundColor Green
} catch {
    Write-Host "Error: pg_dump is not found in PATH!" -ForegroundColor Red
    Write-Host "Please install PostgreSQL client tools or add them to PATH" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Export from local database
Write-Host "[3/5] Exporting from local database..." -ForegroundColor Yellow
Write-Host "Source: $LocalDbHost:$LocalDbPort/$LocalDbName" -ForegroundColor Cyan

if ($DumpFormat -eq "custom") {
    $env:PGPASSWORD = Read-Host "Enter password for $LocalDbUser" -AsSecureString | ConvertFrom-SecureString -AsPlainText
    pg_dump -h $LocalDbHost -p $LocalDbPort -U $LocalDbUser -d $LocalDbName -F c -f $BackupFile
} else {
    $env:PGPASSWORD = Read-Host "Enter password for $LocalDbUser" -AsSecureString | ConvertFrom-SecureString -AsPlainText
    pg_dump -h $LocalDbHost -p $LocalDbPort -U $LocalDbUser -d $LocalDbName -f $BackupFile
}

if (-not (Test-Path $BackupFile)) {
    Write-Host "Error: Backup file was not created!" -ForegroundColor Red
    exit 1
}

$backupSize = (Get-Item $BackupFile).Length / 1MB
Write-Host "✓ Backup created: $BackupFile ($([math]::Round($backupSize, 2)) MB)" -ForegroundColor Green
Write-Host ""

# Copy to Docker container
Write-Host "[4/5] Copying backup to Docker container..." -ForegroundColor Yellow
docker cp $BackupFile "${DockerContainer}:/tmp/$BackupFile"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to copy backup to container!" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Backup copied to container" -ForegroundColor Green
Write-Host ""

# Import into Docker database
Write-Host "[5/5] Importing into Docker database..." -ForegroundColor Yellow
Write-Host "This may take a while depending on database size..." -ForegroundColor Cyan
Write-Host ""

if ($DumpFormat -eq "custom") {
    docker exec -i $DockerContainer pg_restore -U $DockerDbUser -d $DockerDbName -c "/tmp/$BackupFile"
} else {
    docker exec -i $DockerContainer psql -U $DockerDbUser -d $DockerDbName -f "/tmp/$BackupFile"
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Import failed!" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Import completed successfully!" -ForegroundColor Green
Write-Host ""

# Cleanup
Write-Host "Cleaning up..." -ForegroundColor Yellow
docker exec $DockerContainer rm -f "/tmp/$BackupFile"
Remove-Item $BackupFile -Force
Write-Host "✓ Cleanup completed" -ForegroundColor Green
Write-Host ""

# Verify import
Write-Host "Verifying import..." -ForegroundColor Yellow
docker exec -i $DockerContainer psql -U $DockerDbUser -d $DockerDbName -c @"
SELECT 
    schemaname,
    tablename,
    n_live_tup as row_count
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC
LIMIT 10;
"@

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Import completed successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
