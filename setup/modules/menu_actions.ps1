<#
menu_actions.ps1

Module for main menu action handlers.
#>

function Remove-TestDatabaseData {
    <#
    .SYNOPSIS
    Deletes local test database data directories.

    .DESCRIPTION
    This removes host-mounted test database data (Postgres/MySQL/Neo4j/SQLite) and pgAdmin state.
    It is intentionally NOT executed automatically; it must be triggered explicitly from the menu.
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

function Start-Backend {
    param(
        [string]$Port,
        [string]$ComposeFile
    )

    Write-Host "Starting Backend with Database..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "========================================"
    Write-Host "  Services starting:"
    Write-Host "  - Backend API (port $Port)"
    Write-Host "  - PostgreSQL database"
    $webPort = Get-EnvVariable -VariableName "WEB_PORT" -EnvFile ".env" -DefaultValue "8086"
    Write-Host "  - Web GUI at http://localhost:$webPort/"
    Write-Host "========================================"
    Write-Host ""
    Write-Host "Browser will open automatically when API is ready..." -ForegroundColor Gray
    Write-Host ""
    
    Show-RelevantPagesDelayed -Port $Port -TimeoutSeconds 120
    
    docker compose --env-file .env -f $ComposeFile up --build --no-cache --watch
}

function Start-DependencyManagement {
    Write-Host "Opening Dependency Management..." -ForegroundColor Cyan
    & .\python-dependency-management\scripts\manage-python-project-dependencies.ps1
    Write-Host ""
    Write-Host "Dependency Management completed." -ForegroundColor Gray
}

function Start-DependencyAndBackend {
    param(
        [string]$Port,
        [string]$ComposeFile
    )

    Write-Host "Opening Dependency Management first..." -ForegroundColor Cyan
    & .\python-dependency-management\scripts\manage-python-project-dependencies.ps1
    Write-Host ""
    Write-Host "Starting Backend now..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "========================================"
    Write-Host "  API will be accessible at:"
    Write-Host "  http://localhost:$Port/docs"
    $webPort = Get-EnvVariable -VariableName "WEB_PORT" -EnvFile ".env" -DefaultValue "8086"
    Write-Host "  Web GUI at http://localhost:$webPort/"
    Write-Host "========================================"
    Write-Host ""
    Write-Host "Browser will open automatically when API is ready..." -ForegroundColor Gray
    Write-Host ""
    
    Show-RelevantPagesDelayed -Port $Port -TimeoutSeconds 120
    
    docker compose --env-file .env -f $ComposeFile up --build --watch
}

function Invoke-EnvironmentDiagnostics {
    Write-Host "Running Docker/build diagnostics..." -ForegroundColor Yellow
    $diagnosticsScript = "python-dependency-management\scripts\run-docker-build-diagnostics.ps1"
    if (Test-Path $diagnosticsScript) {
        & .\$diagnosticsScript
    } else {
        Write-Host "$diagnosticsScript not found" -ForegroundColor Red
        Write-Host "Please ensure the python-dependency-management directory exists" -ForegroundColor Yellow
    }
}

function Invoke-SetupWizard {
    Write-Host "Re-running the interactive setup wizard" -ForegroundColor Cyan
    Write-Host "" 
    Write-Host "To launch the wizard again, delete the .setup-complete file and restart quick-start." -ForegroundColor Gray
    Write-Host "The wizard automatically backs up your current .env before writing a new one." -ForegroundColor Gray
    Write-Host "" 

    if (-not (Test-Path ".setup-complete")) {
        Write-Host ".setup-complete is already missing. The next quick-start run will start the wizard automatically." -ForegroundColor Gray
    }

    $rerunChoice = Read-Host "Delete .setup-complete and restart quick-start.ps1 now? (y/N)"
    if ($rerunChoice -notmatch "^[Yy]$") {
        Write-Host "No changes were made. Remove .setup-complete manually and run quick-start.ps1 when you're ready." -ForegroundColor Yellow
        return 1
    }

    if (Test-Path ".setup-complete") {
        Remove-Item ".setup-complete" -Force
        Write-Host ".setup-complete removed." -ForegroundColor Green
    } else {
        Write-Host ".setup-complete was not found, continuing." -ForegroundColor Gray
    }

    Write-Host "Restarting quick-start.ps1 so you can walk through the wizard again..." -ForegroundColor Cyan
    & .\quick-start.ps1
    exit $LASTEXITCODE
    return 0
}

function Invoke-DockerComposeDown {
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

function Start-BackendNoCache {
    param(
        [string]$Port,
        [string]$ComposeFile
    )

    Write-Host "Starting Backend (with --no-cache)..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "========================================"
    Write-Host "  API will be accessible at:"
    Write-Host "  http://localhost:$Port/docs"
    Write-Host "========================================"
    Write-Host ""
    Write-Host "Browser will open automatically when API is ready..." -ForegroundColor Gray
    Write-Host ""
    
    Show-RelevantPagesDelayed -Port $Port -TimeoutSeconds 120
    
    docker compose --env-file .env -f $ComposeFile build --no-cache
    docker compose --env-file .env -f $ComposeFile up --watch
}

function Build-ProductionImage {
    Write-Host "Building production Docker image..." -ForegroundColor Cyan
    Write-Host ""
    if (Test-Path build-image\docker-compose.build.yml) {
        docker compose -f build-image\docker-compose.build.yml run --rm build-image
    } else {
        Write-Host "build-image\docker-compose.build.yml not found" -ForegroundColor Red
        Write-Host "Please ensure the build-image directory exists" -ForegroundColor Yellow
    }
}

function Build-WebImage {
    Write-Host "Building web UI Docker image (nginx)..." -ForegroundColor Cyan
    Write-Host ""
    if (Test-Path build-image\docker-compose.build.yml) {
        docker compose -f build-image\docker-compose.build.yml run --rm build-web-image
    } else {
        Write-Host "build-image\docker-compose.build.yml not found" -ForegroundColor Red
        Write-Host "Please ensure the build-image directory exists" -ForegroundColor Yellow
    }
}

function Start-CICDSetup {
    Write-Host "Setting up CI/CD Pipeline..." -ForegroundColor Cyan
    Write-Host ""
    if (Test-Path ci-cd\docker-compose.cicd-setup.yml) {
        docker compose -f ci-cd\docker-compose.cicd-setup.yml run --rm cicd-setup
    } else {
        Write-Host "ci-cd\docker-compose.cicd-setup.yml not found" -ForegroundColor Red
        Write-Host "Please ensure the ci-cd directory exists" -ForegroundColor Yellow
    }
}

function Deploy-AllServices {
    <#
    .SYNOPSIS
    Deploys all services (Backend + Runner + GUI) for backup automation.

    .PARAMETER Port
    API port number.

    .PARAMETER ComposeFile
    Main docker-compose file to use.

    .PARAMETER Detached
    If true, runs in detached mode.
    #>
    param(
        [string]$Port,
        [string]$ComposeFile,
        [bool]$Detached = $false
    )

    $runnerFile = "local-deployment\docker-compose.runner.yml"
    if (-not (Test-Path $runnerFile)) {
        Write-Host "Runner compose file not found: $runnerFile" -ForegroundColor Red
        return 1
    }

    $webPort = Get-EnvVariable -VariableName "WEB_PORT" -EnvFile ".env" -DefaultValue "8086"

    Write-Host ""
    if ($Detached) {
        Write-Host "Starting all services (detached)..." -ForegroundColor Cyan
    } else {
        Write-Host "Starting all services..." -ForegroundColor Cyan
    }
    Write-Host ""
    Write-Host "========================================"
    Write-Host "  Services starting:"
    Write-Host "  - Backend API (port $Port)"
    Write-Host "  - PostgreSQL database"
    Write-Host "  - Backup runner"
    Write-Host "  - Web GUI at http://localhost:$webPort/"
    Write-Host "========================================"
    Write-Host ""
    Write-Host "Browser will open automatically when API is ready..." -ForegroundColor Gray
    Write-Host ""
    
    Show-RelevantPagesDelayed -Port $Port -TimeoutSeconds 120
    
    if ($Detached) {
        docker compose --env-file .env -f $ComposeFile -f $runnerFile up --build -d
        Write-Host ""
        Write-Host "All services started in detached mode!" -ForegroundColor Green
        Write-Host ""
        Write-Host "To view logs:" -ForegroundColor Gray
        Write-Host "     docker compose --env-file .env -f $ComposeFile -f $runnerFile logs -f" -ForegroundColor Gray
        Write-Host "To stop services:" -ForegroundColor Gray
        Write-Host "     docker compose --env-file .env -f $ComposeFile -f $runnerFile down" -ForegroundColor Gray
    } else {
        docker compose --env-file .env -f $ComposeFile -f $runnerFile up --build --watch
    }
}

function Open-BackupGUI {
    <#
    .SYNOPSIS
    Opens the Backup Manager GUI in the default browser.

    .PARAMETER Port
    API port (used to derive web port from .env).
    #>
    param([string]$Port)

    Write-Host "Opening Backup Manager GUI..." -ForegroundColor Cyan
    $webPort = Get-EnvVariable -VariableName "WEB_PORT" -EnvFile ".env" -DefaultValue "8086"
    $url = "http://localhost:$webPort/"
    Write-Host "   URL: $url" -ForegroundColor Gray
    Start-Process $url
}

function Invoke-BackupNow {
    <#
    .SYNOPSIS
    Interactively runs a backup schedule via CLI.

    .PARAMETER Port
    API port number.
    #>
    param([string]$Port)

    Write-Host "Run Backup Now" -ForegroundColor Cyan
    Write-Host ""

    # Check if API is running
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:$Port/health" -Method Get -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    } catch {
        Write-Host "API is not running. Please start the backend first." -ForegroundColor Red
        return 1
    }

    $accessToken = Get-KeycloakAccessToken
    if (-not $accessToken) {
        Write-Host "Missing Keycloak access token." -ForegroundColor Red
        return 1
    }

    Write-Host "Fetching schedules..." -ForegroundColor Gray
    try {
        $headers = @{ "Authorization" = "Bearer $accessToken" }
        $schedulesResponse = Invoke-RestMethod -Uri "http://localhost:$Port/automation/schedules" -Headers $headers -Method Get -ErrorAction Stop
    } catch {
        Write-Host "Failed to fetch schedules. Check your access token." -ForegroundColor Red
        return 1
    }

    Write-Host ""
    Write-Host "Available schedules:" -ForegroundColor Yellow
    if ($schedulesResponse.Count -eq 0) {
        Write-Host "  No schedules configured. Use the web GUI to create one." -ForegroundColor Gray
        return 0
    }

    for ($i = 0; $i -lt $schedulesResponse.Count; $i++) {
        $s = $schedulesResponse[$i]
        $shortId = if ($s.id.Length -gt 8) { $s.id.Substring(0, 8) } else { $s.id }
        Write-Host ("  {0}) {1} (ID: {2}...)" -f ($i + 1), $s.name, $shortId) -ForegroundColor Gray
    }

    Write-Host ""
    $scheduleChoice = Read-Host "Enter schedule number to run (or 'q' to cancel)"

    if ($scheduleChoice -eq 'q') {
        Write-Host "Cancelled." -ForegroundColor Yellow
        return 0
    }

    $idx = [int]$scheduleChoice - 1
    if ($idx -lt 0 -or $idx -ge $schedulesResponse.Count) {
        Write-Host "Invalid selection." -ForegroundColor Red
        return 1
    }

    $scheduleId = $schedulesResponse[$idx].id

    Write-Host ""
    Write-Host "Running backup..." -ForegroundColor Cyan
    try {
        $result = Invoke-RestMethod -Uri "http://localhost:$Port/automation/schedules/$scheduleId/run-now" -Headers $headers -Method Post -ErrorAction Stop
        Write-Host "Backup completed successfully!" -ForegroundColor Green
        Write-Host ("   Filename: {0}" -f $result.backup_filename) -ForegroundColor Gray
    } catch {
        Write-Host "Backup failed:" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
    }
}

function Show-BackupList {
    <#
    .SYNOPSIS
    Lists available backup files.

    .PARAMETER Port
    API port number.
    #>
    param([string]$Port)

    Write-Host "List Backup Files" -ForegroundColor Cyan
    Write-Host ""

    # Check if API is running
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:$Port/health" -Method Get -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    } catch {
        Write-Host "API is not running. Please start the backend first." -ForegroundColor Red
        return 1
    }

    $accessToken = Get-KeycloakAccessToken
    if (-not $accessToken) {
        Write-Host "Missing Keycloak access token." -ForegroundColor Red
        return 1
    }

    Write-Host "Fetching backup files..." -ForegroundColor Gray
    try {
        $headers = @{ "Authorization" = "Bearer $accessToken" }
        $response = Invoke-RestMethod -Uri "http://localhost:$Port/backup/list" -Headers $headers -Method Get -ErrorAction Stop
    } catch {
        Write-Host "Failed to fetch backup files." -ForegroundColor Red
        return 1
    }

    Write-Host ""
    $files = $response.files
    if (-not $files -or $files.Count -eq 0) {
        Write-Host "  No backup files found." -ForegroundColor Gray
    } else {
        Write-Host ("  Found {0} backup(s):" -f $files.Count) -ForegroundColor Yellow
        Write-Host ""
        foreach ($f in $files) {
            Write-Host ("  - {0}" -f $f.filename) -ForegroundColor Gray
            Write-Host ("    Size: {0} MB | Created: {1}" -f $f.size_mb, $f.created_at) -ForegroundColor DarkGray
        }
    }
}

function Start-WithTestDatabases {
    <#
    .SYNOPSIS
    Starts all services with test databases for all supported DB types.

    .PARAMETER Port
    API port number.

    .PARAMETER ComposeFile
    Main docker-compose file.
    #>
    param(
        [string]$Port,
        [string]$ComposeFile
    )

    Write-Host "Starting with Test Databases..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "========================================"
    Write-Host "  Services starting:"
    Write-Host "  - Backend API (port $Port)"
    Write-Host "  - App's database (PostgreSQL or Neo4j)"
    Write-Host "  - Backup runner"
    Write-Host ""
    Write-Host "  Test Databases:"
    Write-Host "  - PostgreSQL (port 5434)"
    Write-Host "  - MySQL (port 3306)"
    Write-Host "  - Neo4j (bolt: 7688, http: 7475)"
    Write-Host ""
    Write-Host "  Admin UIs:"
    Write-Host "  - pgAdmin: http://localhost:5050"
    Write-Host "  - phpMyAdmin: http://localhost:8080"
    Write-Host "  - Neo4j Browser: http://localhost:7475"
    Write-Host "  - Adminer: http://localhost:8082"
    Write-Host "  - Adminer (SQLite): http://localhost:8085"
    Write-Host "  - SQLite Web: http://localhost:8084"
    Write-Host "  - SQLite Browser (GUI): http://localhost:8090"
    Write-Host "========================================"
    Write-Host ""

    $testDbFile = "local-deployment\docker-compose.test-databases.yml"
    $runnerFile = "local-deployment\docker-compose.runner.yml"

    # Check for Keycloak
    $keycloakEnabled = Get-EnvVariable -VariableName "KEYCLOAK_ENABLED" -EnvFile ".env" -DefaultValue "false"
    $keycloakUrl = Get-EnvVariable -VariableName "KEYCLOAK_URL" -EnvFile ".env" -DefaultValue "http://localhost:9090"

    if ($keycloakEnabled.ToLower() -eq "true") {
        try {
            $null = Invoke-WebRequest -Uri "$keycloakUrl/" -Method Get -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        } catch {
            Write-Host ""
            Write-Host "KEYCLOAK_ENABLED=true but Keycloak is not reachable at $keycloakUrl" -ForegroundColor Yellow
            Write-Host "   Start Keycloak from the dedicated repo before logging in:" -ForegroundColor Gray
            Write-Host "   https://github.com/Sokrates1989/keycloak.git" -ForegroundColor Gray
            Write-Host ""
        }
    }

    if (-not (Test-Path $testDbFile)) {
        Write-Host "Test databases compose file not found: $testDbFile" -ForegroundColor Red
        return 1
    }

    if (-not (Test-Path $runnerFile)) {
        Write-Host "Runner compose file not found: $runnerFile" -ForegroundColor Red
        return 1
    }

    Write-Host ""
    Write-Host "Starting all services with test databases..." -ForegroundColor Cyan

    # Start browser opener in background job
    $browserJob = Start-Job -ScriptBlock {
        param($Port, $ComposeFile)
        $maxWait = 120
        $waitTime = 0
        while ($waitTime -lt $maxWait) {
            try {
                $null = Invoke-WebRequest -Uri "http://localhost:$Port/health" -Method Get -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
                break
            } catch {
                Start-Sleep -Seconds 2
                $waitTime += 2
            }
        }
    } -ArgumentList $Port, $ComposeFile

    docker compose --env-file .env -f $ComposeFile -f $runnerFile -f $testDbFile up --build --watch

    Stop-Job $browserJob -ErrorAction SilentlyContinue
    Remove-Job $browserJob -ErrorAction SilentlyContinue
}

function Start-WithAdminUIs {
    <#
    .SYNOPSIS
    Starts services with admin UIs for the app's own database.

    .PARAMETER Port
    API port number.

    .PARAMETER ComposeFile
    Main docker-compose file.
    #>
    param(
        [string]$Port,
        [string]$ComposeFile
    )

    Write-Host "Starting Admin UIs..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "========================================"
    Write-Host "  Services starting:"
    Write-Host "  - Backend API (port $Port)"
    Write-Host "  - App's database"
    Write-Host ""
    Write-Host "  Admin UIs:"
    if ($ComposeFile -like "*postgres*") {
        Write-Host "  - pgAdmin (app DB): http://localhost:5051"
    }
    if ($ComposeFile -like "*neo4j*") {
        Write-Host "  - Neo4j Browser: http://localhost:7474"
    }
    Write-Host "========================================"
    Write-Host ""

    $runnerFile = "local-deployment\docker-compose.runner.yml"

    if (-not (Test-Path $runnerFile)) {
        Write-Host "Runner compose file not found: $runnerFile" -ForegroundColor Red
        return 1
    }

    Write-Host ""
    Write-Host "Starting services with admin profile (watch mode)..." -ForegroundColor Cyan

    docker compose --env-file .env -f $ComposeFile -f $runnerFile --profile admin up --build --watch
}

function Update-ImageVersion {
    <#
    .SYNOPSIS
    Bumps the IMAGE_VERSION in .ci.env file.
    #>
    Write-Host "Bump IMAGE_VERSION" -ForegroundColor Cyan
    
    $ciEnvFile = ".ci.env"
    if (-not (Test-Path $ciEnvFile)) {
        Write-Host ".ci.env file not found" -ForegroundColor Red
        return 1
    }

    $currentVersion = Get-EnvVariable -VariableName "IMAGE_VERSION" -EnvFile $ciEnvFile -DefaultValue "0.0.1"
    Write-Host "Current IMAGE_VERSION: $currentVersion" -ForegroundColor Gray

    $newVersion = Read-Host "Enter new version (or press Enter to keep current)"
    if (-not $newVersion) {
        Write-Host "Version unchanged." -ForegroundColor Yellow
        return 0
    }

    $content = Get-Content $ciEnvFile
    $updated = $content -replace "^IMAGE_VERSION=.*$", "IMAGE_VERSION=$newVersion"
    $updated | Set-Content $ciEnvFile

    Write-Host "IMAGE_VERSION updated to $newVersion" -ForegroundColor Green
}

function Show-MainMenu {
    param(
        [string]$Port,
        [string]$ComposeFile
    )

    $menuNext = 1
    $MENU_START_ALL_UNDETACHED = $menuNext; $menuNext++
    $MENU_START_ALL = $menuNext; $menuNext++

    $MENU_DOWN = $menuNext; $menuNext++
    $MENU_DEP_MGMT = $menuNext; $menuNext++
    $MENU_DIAGNOSTICS = $menuNext; $menuNext++

    $MENU_BUILD = $menuNext; $menuNext++
    $MENU_BUILD_WEB = $menuNext; $menuNext++
    $MENU_CICD = $menuNext; $menuNext++
    $MENU_BUMP_VERSION = $menuNext; $menuNext++

    $MENU_RUN_BACKUP = $menuNext; $menuNext++
    $MENU_LIST_BACKUPS = $menuNext; $menuNext++

    $MENU_TEST_DBS = $menuNext; $menuNext++
    $MENU_TEST_DBS_ADMIN = $menuNext; $menuNext++
    $MENU_CLEAN_TEST_DATA = $menuNext; $menuNext++

    $MENU_SETUP = $menuNext; $menuNext++
    $MENU_KEYCLOAK_BOOTSTRAP = $menuNext; $menuNext++

    $MENU_EXIT = $menuNext

    Write-Host "" 
    Write-Host "================ Main Menu ================" -ForegroundColor Yellow
    Write-Host "" 
    Write-Host "Start:" -ForegroundColor Yellow
    Write-Host "  $MENU_START_ALL_UNDETACHED) Start all services (undetached - logs shown)" -ForegroundColor Gray
    Write-Host "  $MENU_START_ALL) Start all services (detached - background)" -ForegroundColor Gray
    Write-Host "" 
    Write-Host "Maintenance:" -ForegroundColor Yellow
    Write-Host "  $MENU_DOWN) Docker Compose Down (stop and remove containers)" -ForegroundColor Gray
    Write-Host "  $MENU_DEP_MGMT) Open Dependency Management only" -ForegroundColor Gray
    Write-Host "  $MENU_DIAGNOSTICS) Run Docker/Build Diagnostics" -ForegroundColor Gray
    Write-Host "" 
    Write-Host "Build / CI/CD:" -ForegroundColor Yellow
    Write-Host "  $MENU_BUILD) Build Production Docker Image" -ForegroundColor Gray
    Write-Host "  $MENU_BUILD_WEB) Build Website Docker Image (nginx)" -ForegroundColor Gray
    Write-Host "  $MENU_CICD) Setup CI/CD Pipeline" -ForegroundColor Gray
    Write-Host "  $MENU_BUMP_VERSION) Bump release version for docker image" -ForegroundColor Gray
    Write-Host "" 
    Write-Host "Backup Automation:" -ForegroundColor Yellow
    Write-Host "  $MENU_RUN_BACKUP) Run backup now (CLI)" -ForegroundColor Gray
    Write-Host "  $MENU_LIST_BACKUPS) List backup files" -ForegroundColor Gray
    Write-Host "" 
    Write-Host "Testing (all DB types + admin UIs):" -ForegroundColor Yellow
    Write-Host "  $MENU_TEST_DBS) Start with test databases" -ForegroundColor Gray
    Write-Host "  $MENU_TEST_DBS_ADMIN) Start with admin UIs only" -ForegroundColor Gray
    Write-Host "  $MENU_CLEAN_TEST_DATA) Clean test database data" -ForegroundColor Gray
    Write-Host "" 
    Write-Host "Setup:" -ForegroundColor Yellow
    Write-Host "  $MENU_SETUP) Re-run setup wizard" -ForegroundColor Gray
    Write-Host "  $MENU_KEYCLOAK_BOOTSTRAP) Bootstrap Keycloak (realm, roles, users)" -ForegroundColor Gray
    Write-Host "" 
    Write-Host "  $MENU_EXIT) Exit" -ForegroundColor Gray
    Write-Host ""
    $choice = Read-Host "Your choice (1-$MENU_EXIT)"

    $summary = $null
    $exitCode = 0

    switch ($choice) {
        "$MENU_START_ALL_UNDETACHED" {
            Deploy-AllServices -Port $Port -ComposeFile $ComposeFile -Detached $false
            $summary = "All services started (undetached)"
        }
        "$MENU_START_ALL" {
            Deploy-AllServices -Port $Port -ComposeFile $ComposeFile -Detached $true
            $summary = "All services started (detached)"
        }
        "$MENU_DOWN" {
            Invoke-DockerComposeDown -ComposeFile $ComposeFile
            $summary = "Docker Compose Down executed"
        }
        "$MENU_DEP_MGMT" {
            Start-DependencyManagement
            Write-Host "To start the backend, re-run quick-start.ps1 and choose a start option." -ForegroundColor Yellow
            $summary = "Dependency Management executed"
        }
        "$MENU_DIAGNOSTICS" {
            Invoke-EnvironmentDiagnostics
            $summary = "Docker/Build diagnostics launched"
        }
        "$MENU_BUILD" {
            Build-ProductionImage
            $summary = "Production Docker image build triggered"
        }
        "$MENU_BUILD_WEB" {
            Build-WebImage
            $summary = "Website Docker image build triggered"
        }
        "$MENU_CICD" {
            Start-CICDSetup
            $summary = "CI/CD setup started"
        }
        "$MENU_BUMP_VERSION" {
            Update-ImageVersion
            $summary = "IMAGE_VERSION updated"
        }
        "$MENU_RUN_BACKUP" {
            Invoke-BackupNow -Port $Port
            $summary = "Backup operation completed"
        }
        "$MENU_LIST_BACKUPS" {
            Show-BackupList -Port $Port
            $summary = "Backup list displayed"
        }
        "$MENU_TEST_DBS" {
            Start-WithTestDatabases -Port $Port -ComposeFile $ComposeFile
            $summary = "Test databases started"
        }
        "$MENU_TEST_DBS_ADMIN" {
            Start-WithAdminUIs -Port $Port -ComposeFile $ComposeFile
            $summary = "Admin UIs started"
        }
        "$MENU_CLEAN_TEST_DATA" {
            Remove-TestDatabaseData
            $summary = "Test database data cleaned"
        }
        "$MENU_SETUP" {
            $result = Invoke-SetupWizard
            if ($result -eq 0) {
                $summary = "Setup wizard re-run completed"
            } else {
                $summary = "Setup wizard re-run failed or aborted"
                $exitCode = 1
            }
        }
        "$MENU_KEYCLOAK_BOOTSTRAP" {
            $result = Invoke-KeycloakBootstrap
            if ($result -eq 0) {
                $summary = "Keycloak bootstrap completed"
            } else {
                $summary = "Keycloak bootstrap failed"
                $exitCode = 1
            }
        }
        "$MENU_EXIT" {
            Write-Host "Exiting script." -ForegroundColor Cyan
            exit 0
        }
        Default {
            Write-Host "Invalid selection. Please re-run the script." -ForegroundColor Yellow
            exit 1
        }
    }

    Write-Host ""
    if ($summary) {
        Write-Host ("{0}" -f $summary) -ForegroundColor Green
    }
    Write-Host 'Quick-start finished. Run the script again for more actions.' -ForegroundColor Cyan
    Write-Host ""
    exit $exitCode
}
