# quick-start.ps1
# PowerShell version of quick-start.sh
# Complete onboarding tool for freshly cloned projects

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$setupDir = Join-Path $scriptDir "setup"

# Import modules
Import-Module "$setupDir\modules\docker_helpers.ps1" -Force
Import-Module "$setupDir\modules\version_manager.ps1" -Force
Import-Module "$setupDir\modules\menu_handlers.ps1" -Force

# Source Cognito setup script if available
$cognitoScript = Join-Path $setupDir "modules\cognito_setup.ps1"
if (Test-Path $cognitoScript) {
    . $cognitoScript
}

Write-Host "FastAPI Redis API Test - Quick Start" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker availability
if (-not (Test-DockerInstallation)) {
    exit 1
}
Write-Host ""

# Check if initial setup is needed
if (-not (Test-Path .setup-complete)) {
    Write-Host " First-time setup detected!" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "This appears to be your first time running this project." -ForegroundColor Yellow
    Write-Host "Would you like to run the interactive setup wizard?" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "The setup wizard will help you configure:" -ForegroundColor Gray
    Write-Host "  - Docker image name and version" -ForegroundColor Gray
    Write-Host "  - Python version" -ForegroundColor Gray
    Write-Host "  - Database type (PostgreSQL or Neo4j)" -ForegroundColor Gray
    Write-Host "  - Database mode (local or external)" -ForegroundColor Gray
    Write-Host "  - API configuration" -ForegroundColor Gray
    Write-Host ""
    
    $runSetup = Read-Host "Run setup wizard now? (Y/n)"
    if ($runSetup -ne "n" -and $runSetup -ne "N") {
        Write-Host ""
        Write-Host "Starting setup wizard..." -ForegroundColor Cyan
        docker compose -f setup/docker-compose.setup.yml run --rm setup
        Write-Host ""
        if (Get-Command Invoke-CognitoSetup -ErrorAction SilentlyContinue) {
            Invoke-CognitoSetup
            Write-Host "" -ForegroundColor Gray
        }
    } else {
        Write-Host ""
        Write-Host "Skipping setup wizard. Creating basic .env from template..." -ForegroundColor Yellow
        if (Test-Path setup\.env.template) {
            Copy-Item setup\.env.template .env
            Write-Host ".env file created from template." -ForegroundColor Green
            Write-Host "  Please edit .env to configure your environment before continuing." -ForegroundColor Yellow
            if (Get-Command Invoke-CognitoSetup -ErrorAction SilentlyContinue) {
                Invoke-CognitoSetup
                Write-Host "" -ForegroundColor Gray
            }
        } else {
            Write-Host "[ERROR] setup\.env.template not found!" -ForegroundColor Red
            exit 1
        }
    }
    Write-Host ""
} elseif (-not (Test-Path .env)) {
    # Setup complete but .env missing - recreate from template
    Write-Host " .env file missing. Creating from template..." -ForegroundColor Yellow
    if (Test-Path setup\.env.template) {
        Copy-Item setup\.env.template .env
        Write-Host ".env file created from template." -ForegroundColor Green
        Write-Host "Please check the values in .env if needed." -ForegroundColor Yellow
        if (Get-Command Invoke-CognitoSetup -ErrorAction SilentlyContinue) {
            Invoke-CognitoSetup
            Write-Host "" -ForegroundColor Gray
        }
    } else {
        Write-Host "[ERROR] setup\.env.template not found!" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

# Read PORT from .env (default: 8000)
$PORT = Get-EnvVariable -VariableName "PORT" -EnvFile ".env" -DefaultValue "8000"

# Read database configuration from .env
$DB_TYPE = Get-EnvVariable -VariableName "DB_TYPE" -EnvFile ".env" -DefaultValue "neo4j"
$DB_MODE = Get-EnvVariable -VariableName "DB_MODE" -EnvFile ".env" -DefaultValue "local"

# Determine Docker Compose file based on DB_TYPE and DB_MODE
$COMPOSE_FILE = Get-ComposeFile -DbType $DB_TYPE -DbMode $DB_MODE

if ($DB_MODE -eq "external") {
    Write-Host "Detected external database mode" -ForegroundColor Cyan
    Write-Host "   Database Type: $DB_TYPE" -ForegroundColor Gray
    Write-Host "   Will connect to external database (no local DB container)" -ForegroundColor Gray
} elseif ($DB_TYPE -eq "neo4j") {
    Write-Host "Detected local Neo4j database" -ForegroundColor Cyan
    Write-Host "   Will start Neo4j container" -ForegroundColor Gray
} elseif ($DB_TYPE -eq "postgresql" -or $DB_TYPE -eq "mysql") {
    Write-Host "Detected local $DB_TYPE database" -ForegroundColor Cyan
    Write-Host "   Will start PostgreSQL container" -ForegroundColor Gray
} else {
    Write-Host "Unknown DB_TYPE: $DB_TYPE, using default compose file" -ForegroundColor Yellow
}

Write-Host "   Using: $COMPOSE_FILE" -ForegroundColor Gray
Write-Host ""

# Check if this is the first setup run
if (-not (Test-Path .setup-complete)) {
    Write-Host "First setup detected - Running automatic dependency configuration..." -ForegroundColor Cyan
    Write-Host "The first start may take a bit longer, but it will be much faster afterwards." -ForegroundColor Yellow
    Write-Host ""
    
    # Run diagnostics to validate Docker/build configuration first
    $diagnosticsScript = "python-dependency-management\scripts\run-docker-build-diagnostics.ps1"
    if (Test-Path $diagnosticsScript) {
        Write-Host "Running Docker/Build diagnostics..." -ForegroundColor Yellow
        Write-Host "Collecting diagnostic information..." -ForegroundColor Gray
        try {
            & .\$diagnosticsScript
            if ($LASTEXITCODE -eq 0) {
                Write-Host "Diagnostics completed successfully" -ForegroundColor Green
            } else {
                throw "Diagnostics reported issues"
            }
        } catch {
            Write-Host "Diagnostics reported issues with your Docker or build configuration!" -ForegroundColor Red
            Write-Host "Please address the reported problems before continuing." -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Troubleshooting steps:" -ForegroundColor Yellow
            Write-Host "1. Ensure Docker Desktop/daemon is running" -ForegroundColor Gray
            Write-Host "2. Verify .env values (especially PYTHON_VERSION and DB settings)" -ForegroundColor Gray
            Write-Host "3. Review missing files noted in the diagnostics output" -ForegroundColor Gray
            Write-Host "4. Re-run manually via: .\$diagnosticsScript" -ForegroundColor Gray
            Write-Host "" -ForegroundColor Gray
            $continue = Read-Host "Continue anyway? (y/N)"
            if ($continue -notmatch "^[Yy]$") {
                Write-Host "Setup aborted. Please fix the reported diagnostics issues first." -ForegroundColor Red
                exit 1
            }
            Write-Host "Continuing with potentially broken configuration..." -ForegroundColor Yellow
        }
    } else {
        Write-Host "$diagnosticsScript not found - skipping diagnostics" -ForegroundColor Yellow
    }
    
    Write-Host ""
    
    # Run Dependency Management in initial-run mode
    if (Test-Path python-dependency-management\scripts\manage-python-project-dependencies.ps1) {
        Write-Host "Starting Dependency Management for initial setup..." -ForegroundColor Cyan
        try {
            & .\python-dependency-management\scripts\manage-python-project-dependencies.ps1 -InitialRun
        } catch {
            Write-Host "Error running dependency management: $_" -ForegroundColor Red
            Write-Host "Dependencies will be installed when Docker builds the container" -ForegroundColor Yellow
        }
    } else {
        Write-Host "python-dependency-management\scripts\manage-python-project-dependencies.ps1 not found - skipping" -ForegroundColor Yellow
        Write-Host "Dependencies will be installed when Docker builds the container" -ForegroundColor Yellow
    }
    
    # Mark setup as complete
    New-Item -ItemType File -Path .setup-complete -Force | Out-Null
    
    Write-Host ""
    Write-Host "First setup complete!" -ForegroundColor Green
    Write-Host "Starting backend now..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  API will be accessible at:" -ForegroundColor Cyan
    Write-Host "  http://localhost:$PORT/docs" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Press ENTER to open the API documentation in your browser..." -ForegroundColor Yellow
    Write-Host "(The API may take a few seconds to start. Please refresh the page if needed.)" -ForegroundColor Gray
    $null = Read-Host
    
    # Open browser in incognito/private mode
    Write-Host "Opening browser..." -ForegroundColor Cyan
    Start-Process "msedge" "--inprivate http://localhost:$PORT/docs" -ErrorAction SilentlyContinue
    if ($LASTEXITCODE -ne 0) {
        # Fallback to Chrome if Edge not available
        Start-Process "chrome" "--incognito http://localhost:$PORT/docs" -ErrorAction SilentlyContinue
        if ($LASTEXITCODE -ne 0) {
            # Fallback to default browser
            Start-Process "http://localhost:$PORT/docs"
        }
    }
    
    Write-Host ""
    docker compose --env-file .env -f $COMPOSE_FILE up --build
} else {
    Write-Host "🐳 Starte Backend mit Docker Compose..." -ForegroundColor Cyan
    Write-Host "Backend wird verfügbar sein auf: http://localhost:$PORT" -ForegroundColor Cyan
    Write-Host ""

    Show-MainMenu -Port $PORT -ComposeFile $COMPOSE_FILE
}