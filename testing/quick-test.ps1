# Quick Test Entry Script (PowerShell)
# Simplified testing interface for the API

$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "FastAPI Quick Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Docker not running" }
} catch {
    Write-Host "Docker is not running!" -ForegroundColor Red
    Write-Host "Please start Docker Desktop or the Docker service" -ForegroundColor Yellow
    exit 1
}

# Check if .env exists
if (-not (Test-Path .env)) {
    Write-Host "No .env file found!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please choose a database configuration:" -ForegroundColor Yellow
    Write-Host "1) PostgreSQL (recommended for testing)" -ForegroundColor Gray
    Write-Host "2) Neo4j" -ForegroundColor Gray
    Write-Host "3) Exit and configure manually" -ForegroundColor Gray
    Write-Host ""
    $dbChoice = Read-Host "Your choice (1-3)"
    
    switch ($dbChoice) {
        "1" {
            Write-Host "Copying PostgreSQL configuration..." -ForegroundColor Cyan
            Copy-Item .env.postgres.example .env
            Write-Host "Using PostgreSQL" -ForegroundColor Green
        }
        "2" {
            Write-Host "Copying Neo4j configuration..." -ForegroundColor Cyan
            Copy-Item .env.neo4j.example .env
            Write-Host "Using Neo4j" -ForegroundColor Green
        }
        "3" {
            Write-Host "Please create .env file manually" -ForegroundColor Cyan
            Write-Host "   You can copy from .env.postgres.example or .env.neo4j.example" -ForegroundColor Gray
            exit 0
        }
        default {
            Write-Host "Invalid choice. Using PostgreSQL as default..." -ForegroundColor Yellow
            Copy-Item .env.postgres.example .env
        }
    }
    Write-Host ""
}

# Read database configuration
$DB_TYPE = "neo4j"
$DB_MODE = "local"
if (Test-Path .env) {
    $envContent = Get-Content .env -ErrorAction SilentlyContinue
    
    $dbTypeLine = $envContent | Where-Object { $_ -match "^DB_TYPE=" }
    if ($dbTypeLine) {
        $DB_TYPE = ($dbTypeLine -split "=", 2)[1].Trim().Trim('"')
    }
    
    $dbModeLine = $envContent | Where-Object { $_ -match "^DB_MODE=" }
    if ($dbModeLine) {
        $DB_MODE = ($dbModeLine -split "=", 2)[1].Trim().Trim('"')
    }
}

# Determine compose file
if ($DB_MODE -eq "external") {
    $COMPOSE_FILE = "docker\docker-compose.yml"
    Write-Host "Using external $DB_TYPE database" -ForegroundColor Cyan
} elseif ($DB_TYPE -eq "neo4j") {
    $COMPOSE_FILE = "docker\docker-compose.neo4j.yml"
    Write-Host "Using local Neo4j database" -ForegroundColor Cyan
} elseif ($DB_TYPE -eq "postgresql" -or $DB_TYPE -eq "mysql") {
    $COMPOSE_FILE = "docker\docker-compose.postgres.yml"
    Write-Host "Using local PostgreSQL database" -ForegroundColor Cyan
} else {
    $COMPOSE_FILE = "docker\docker-compose.yml"
    Write-Host "Unknown database type, using default" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "What would you like to do?" -ForegroundColor Yellow
Write-Host "1) Start services and run tests" -ForegroundColor Gray
Write-Host "2) Just start services" -ForegroundColor Gray
Write-Host "3) Just run tests (services must be running)" -ForegroundColor Gray
Write-Host "4) Stop services" -ForegroundColor Gray
Write-Host ""
$actionChoice = Read-Host "Your choice (1-4)"

switch ($actionChoice) {
    "1" {
        Write-Host ""
        Write-Host "Starting services..." -ForegroundColor Cyan
        docker compose -f $COMPOSE_FILE up -d --build
        
        Write-Host ""
        Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        
        Write-Host ""
        Write-Host "Running tests..." -ForegroundColor Cyan
        & "testing\scripts\test-api.bat"
        
        Write-Host ""
        Write-Host "Services are running!" -ForegroundColor Green
        Write-Host "   API: http://localhost:8000/docs" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "To stop services, run:" -ForegroundColor Yellow
        Write-Host "   docker compose -f $COMPOSE_FILE down" -ForegroundColor Gray
    }
    "2" {
        Write-Host ""
        Write-Host "Starting services..." -ForegroundColor Cyan
        docker compose -f $COMPOSE_FILE up --build
    }
    "3" {
        Write-Host ""
        Write-Host "Running tests..." -ForegroundColor Cyan
        & "testing\scripts\test-api.bat"
    }
    "4" {
        Write-Host ""
        Write-Host "Stopping services..." -ForegroundColor Yellow
        docker compose -f $COMPOSE_FILE down
        Write-Host "Services stopped" -ForegroundColor Green
    }
    default {
        Write-Host "Invalid choice" -ForegroundColor Red
        exit 1
    }
}
