<#
.SYNOPSIS
    Stack operations module for Backup-Restore quick-start menu.

.DESCRIPTION
    This module provides functions for starting, stopping, and managing
    the Docker Compose stack for Backup-Restore. Extracted from menu_handlers.ps1
    for single responsibility and modularity.

.NOTES
    Author: Auto-generated
    Date: 2026-01-29
    Version: 1.0.0
#>

$scriptPath = $PSScriptRoot
$browserHelpersPath = Join-Path $scriptPath "browser_helpers.ps1"
if (Test-Path $browserHelpersPath) {
    . $browserHelpersPath
}

function Get-EnvVariable {
    <#
    .SYNOPSIS
        Get an environment variable from .env file or environment.

    .PARAMETER VariableName
        Name of the variable to retrieve.

    .PARAMETER EnvFile
        Path to the .env file.

    .PARAMETER DefaultValue
        Default value if not found.

    .RETURNS
        The variable value or default.
    #>
    param(
        [string]$VariableName,
        [string]$EnvFile = ".env",
        [string]$DefaultValue = ""
    )

    $value = $DefaultValue

    if (Test-Path $EnvFile) {
        $envContent = Get-Content $EnvFile -ErrorAction SilentlyContinue
        $line = $envContent | Where-Object { $_ -match "^$VariableName=" }
        if ($line) {
            $value = ($line -split "=", 2)[1].Trim().Trim('"')
        }
    }

    if ([string]::IsNullOrWhiteSpace($value)) {
        $envValue = [Environment]::GetEnvironmentVariable($VariableName)
        if (-not [string]::IsNullOrWhiteSpace($envValue)) {
            $value = $envValue
        }
    }

    return $value
}

function Start-Backend {
    <#
    .SYNOPSIS
        Start the backend with database in foreground.

    .PARAMETER Port
        API port number.

    .PARAMETER ComposeFile
        Path to the Docker Compose file.
    #>
    param(
        [string]$Port,
        [string]$ComposeFile
    )
    
    Write-Host "[INFO] Starting Backend with Database..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "  Services starting:" -ForegroundColor Yellow
    Write-Host "  - Backend API (port $Port)" -ForegroundColor Gray
    Write-Host "  - PostgreSQL database" -ForegroundColor Gray
    $webPort = Get-EnvVariable -VariableName "WEB_PORT" -EnvFile ".env" -DefaultValue "8086"
    Write-Host "  - Web GUI at http://localhost:$webPort/" -ForegroundColor Gray
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Browser will open automatically when API is ready..." -ForegroundColor Yellow
    Write-Host ""
    
    if (Get-Command Show-RelevantPagesDelayed -ErrorAction SilentlyContinue) {
        Show-RelevantPagesDelayed -ComposeFile $ComposeFile -TimeoutSeconds 120
    }
    
    Write-Host ""
    docker compose --env-file .env -f $ComposeFile up --build --no-cache --watch
}

function Start-BackendNoCache {
    <#
    .SYNOPSIS
        Start backend directly with --no-cache build.

    .PARAMETER Port
        API port number.

    .PARAMETER ComposeFile
        Path to the Docker Compose file.
    #>
    param(
        [string]$Port,
        [string]$ComposeFile
    )
    
    Write-Host "Starting backend directly (with --no-cache)..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  API will be accessible at:" -ForegroundColor Cyan
    Write-Host "  http://localhost:$Port/docs" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Green
    if ($ComposeFile -like "*neo4j*") {
        Write-Host "  Neo4j Browser will be accessible at:" -ForegroundColor Cyan
        Write-Host "  http://localhost:7474" -ForegroundColor Yellow
        Write-Host "========================================" -ForegroundColor Green
    }
    Write-Host ""
    Write-Host "[WEB] Browser will open automatically when API is ready..." -ForegroundColor Yellow
    Write-Host ""
    
    if (Get-Command Show-RelevantPagesDelayed -ErrorAction SilentlyContinue) {
        Show-RelevantPagesDelayed -ComposeFile $ComposeFile -TimeoutSeconds 120
    }
    
    Write-Host ""
    docker compose --env-file .env -f $ComposeFile build --no-cache
    docker compose --env-file .env -f $ComposeFile up --watch
}

function Invoke-DockerComposeDown {
    <#
    .SYNOPSIS
        Stop and remove containers.

    .PARAMETER ComposeFile
        Path to the Docker Compose file.
    #>
    param(
        [string]$ComposeFile
    )
    
    Write-Host "Stopping and removing containers..." -ForegroundColor Yellow
    Write-Host "   Using compose file: $ComposeFile" -ForegroundColor Gray
    Write-Host ""
    docker compose --env-file .env -f $ComposeFile down --remove-orphans
    Write-Host ""
    Write-Host "Containers stopped and removed" -ForegroundColor Green
}

function Deploy-AllServices {
    <#
    .SYNOPSIS
        Deploy all services (Backend + Runner + GUI) for backup automation.

    .PARAMETER Port
        API port number.

    .PARAMETER ComposeFile
        Path to the Docker Compose file.

    .PARAMETER Detached
        Run in detached mode.
    #>
    param(
        [int]$Port,
        [string]$ComposeFile,
        [bool]$Detached = $true
    )

    Write-Host "[INFO] Deploying all services (Backend + Runner)..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "   Services:" -ForegroundColor Gray
    Write-Host "   - Backend API (port $Port)" -ForegroundColor Gray
    Write-Host "   - PostgreSQL database" -ForegroundColor Gray
    Write-Host "   - Backup runner (periodic execution)" -ForegroundColor Gray
    $webPort = Get-EnvVariable -VariableName "WEB_PORT" -EnvFile ".env" -DefaultValue "8086"
    Write-Host "   - Web GUI at http://localhost:$webPort/" -ForegroundColor Gray
    Write-Host ""

    $runnerFile = "local-deployment/docker-compose.runner.yml"
    if (-not (Test-Path $runnerFile)) {
        Write-Host "[ERROR] Runner compose file not found: $runnerFile" -ForegroundColor Red
        return
    }

    $detachMode = if ($Detached) { "detached" } else { "undetached" }

    if (Get-Command Show-RelevantPagesDelayed -ErrorAction SilentlyContinue) {
        Show-RelevantPagesDelayed -ComposeFile $ComposeFile -TimeoutSeconds 120 -Port $Port
    }

    Write-Host "[DOCKER] Starting services ($detachMode)..." -ForegroundColor Cyan

    if ($Detached) {
        docker compose --env-file .env -f $ComposeFile -f $runnerFile up -d --build
    } else {
        docker compose --env-file .env -f $ComposeFile -f $runnerFile up --build --watch
        return
    }

    Write-Host ""
    Write-Host "[WAIT] Waiting for services to be ready..." -ForegroundColor Cyan

    $maxWait = 60
    $waitCount = 0
    do {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$Port/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host "[OK] Backend is ready!" -ForegroundColor Green
                break
            }
        } catch { }
        Write-Host "." -NoNewline -ForegroundColor Gray
        Start-Sleep -Seconds 2
        $waitCount++
    } while ($waitCount -lt $maxWait)

    if ($waitCount -eq $maxWait) {
        Write-Host ""
        Write-Host "[ERROR] Backend failed to start within ${maxWait}s" -ForegroundColor Red
        Write-Host "   Check logs: docker compose logs" -ForegroundColor Yellow
        return
    }

    Write-Host ""
    Write-Host "[OK] All services deployed and running!" -ForegroundColor Green
    Write-Host ""
    Write-Host "   Services status:" -ForegroundColor Gray
    docker compose --env-file .env -f $ComposeFile -f $runnerFile ps
    Write-Host ""
    Write-Host "   To stop all services:" -ForegroundColor Gray
    Write-Host "     docker compose --env-file .env -f $ComposeFile -f $runnerFile down" -ForegroundColor Gray
}

function Start-WithTestDatabases {
    <#
    .SYNOPSIS
        Start all services with test databases for all supported DB types.

    .PARAMETER Port
        API port number.

    .PARAMETER ComposeFile
        Path to the Docker Compose file.
    #>
    param(
        [int]$Port,
        [string]$ComposeFile
    )

    Write-Host "[TEST] Starting with Test Databases..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "  Services starting:" -ForegroundColor Yellow
    Write-Host "  - Backend API (port $Port)" -ForegroundColor Gray
    Write-Host "  - App's database (PostgreSQL or Neo4j)" -ForegroundColor Gray
    Write-Host "  - Backup runner" -ForegroundColor Gray
    Write-Host "" -ForegroundColor Yellow
    Write-Host "  Test Databases:" -ForegroundColor Yellow
    Write-Host "  - PostgreSQL (port 5434)" -ForegroundColor Gray
    Write-Host "  - MySQL (port 3306)" -ForegroundColor Gray
    Write-Host "  - Neo4j (bolt: 7688, http: 7475)" -ForegroundColor Gray
    Write-Host "" -ForegroundColor Yellow
    Write-Host "  Admin UIs:" -ForegroundColor Yellow
    Write-Host "  - pgAdmin: http://localhost:5050" -ForegroundColor Gray
    Write-Host "  - phpMyAdmin: http://localhost:8080" -ForegroundColor Gray
    Write-Host "  - Neo4j Browser: http://localhost:7475" -ForegroundColor Gray
    Write-Host "  - Adminer: http://localhost:8082" -ForegroundColor Gray
    Write-Host "  - Adminer (SQLite): http://localhost:8085" -ForegroundColor Gray
    Write-Host "  - SQLite Web: http://localhost:8084" -ForegroundColor Gray
    Write-Host "  - SQLite Browser (GUI): http://localhost:8090" -ForegroundColor Gray
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host ""

    $testDbFile = "local-deployment/docker-compose.test-databases.yml"
    $runnerFile = "local-deployment/docker-compose.runner.yml"

    if (-not (Test-Path $testDbFile)) {
        Write-Host "[ERROR] Test databases compose file not found: $testDbFile" -ForegroundColor Red
        return
    }

    if (-not (Test-Path $runnerFile)) {
        Write-Host "[ERROR] Runner compose file not found: $runnerFile" -ForegroundColor Red
        return
    }

    Write-Host ""
    Write-Host "[CLEAN] Stopping any previous stack (freeing ports)..." -ForegroundColor Cyan
    docker compose --env-file .env -f $ComposeFile -f $runnerFile down --remove-orphans 2>&1 | Out-Null
    docker compose --env-file .env -f $ComposeFile -f $runnerFile -f $testDbFile down --remove-orphans 2>&1 | Out-Null
    Write-Host "[OK] Previous stack stopped (if any)" -ForegroundColor Green

    Write-Host ""
    Write-Host "[INFO] Keeping existing test database data (no automatic cleanup)." -ForegroundColor Gray
    Write-Host "       Use the explicit 'Clean test database data' menu option if you want a fresh start." -ForegroundColor Gray
    Write-Host ""
    Write-Host "[DOCKER] Starting all services with test databases..." -ForegroundColor Cyan
    
    $webPort = Get-EnvVariable -VariableName "WEB_PORT" -EnvFile ".env" -DefaultValue "8086"
    $urlsToOpen = @(
        "http://localhost:$webPort/",
        "http://localhost:$Port/docs",
        "http://localhost:5050",
        "http://localhost:8080",
        "http://localhost:7475/browser?connectURL=neo4j://localhost:7688",
        "http://localhost:8082/",
        "http://localhost:8085/",
        "http://localhost:8084",
        "http://localhost:8090"
    )

    if (Get-Command Show-RelevantPagesDelayed -ErrorAction SilentlyContinue) {
        Show-RelevantPagesDelayed -ComposeFile $ComposeFile -TimeoutSeconds 120 -Port $Port -UrlsToOpen $urlsToOpen
    }

    Write-Host ""
    Write-Host "[DOCKER] Starting all services with test databases (undetached)..." -ForegroundColor Cyan

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
    $logDir = Join-Path $projectRoot (Join-Path "logs" (Join-Path "test-databases" $timestamp))
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null

    $composeLogFile = Join-Path $logDir "docker-compose.log"
    Set-Content -Path $composeLogFile -Value "" -Encoding utf8
    Write-Host "[LOG] Docker compose output will be written to: $composeLogFile" -ForegroundColor Gray

    $composeArgsBase = @("--env-file", ".env", "-f", $ComposeFile, "-f", $runnerFile, "-f", $testDbFile)

    $logJob = Start-Job -ScriptBlock {
        param($projectRoot, $composeLogFile, $composeArgsBase)
        Set-Location $projectRoot
        while ($true) {
            if (Test-Path $composeLogFile) {
                Get-Content -Path $composeLogFile -Tail 1 -Wait
            }
            Start-Sleep -Milliseconds 100
        }
    } -ArgumentList $projectRoot, $composeLogFile, $composeArgsBase

    try {
        docker compose @composeArgsBase up --build --watch 2>&1 | Tee-Object -FilePath $composeLogFile
    } finally {
        try { Stop-Job -Job $logJob -Force -ErrorAction SilentlyContinue } catch { }
        try { Remove-Job -Job $logJob -Force -ErrorAction SilentlyContinue } catch { }
    }
}

function Remove-TestDatabaseData {
    <#
    .SYNOPSIS
        Delete local test database data directories.
    #>

    Write-Host "" 
    Write-Host "[CLEAN] Clean test database data" -ForegroundColor Yellow
    Write-Host "" 
    Write-Host "This will delete the following directories:" -ForegroundColor Gray
    Write-Host "  - .docker/test-*" -ForegroundColor Gray
    Write-Host "  - .docker/pgadmin-data" -ForegroundColor Gray
    Write-Host "" 

    $confirm = Read-Host "Are you sure? (y/N)"
    if ($confirm -notmatch "^[Yy]$") {
        Write-Host "[CANCEL] Cleanup cancelled." -ForegroundColor Yellow
        return
    }

    try {
        Remove-Item -Path ".docker/test-*" -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item -Path ".docker/pgadmin-data" -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "[OK] Test database data cleaned. Next start will use fresh databases." -ForegroundColor Green
    } catch {
        Write-Host "[WARN] Cleanup encountered an error: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}
