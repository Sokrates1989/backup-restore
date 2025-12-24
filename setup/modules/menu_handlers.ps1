# menu_handlers.ps1
# PowerShell module for handling menu actions in quick-start script

function Open-BrowserInIncognito {
    param(
        [string]$Port,
        [string]$ComposeFile
    )

    $apiUrl = "http://localhost:$Port/docs"
    $neo4jUrl = "http://localhost:7474"
    $includeNeo4j = $ComposeFile -like "*neo4j*"

    Write-Host "Opening browser..." -ForegroundColor Cyan

    $edgeArgs = "--inprivate $apiUrl"
    $chromeArgs = "--incognito $apiUrl"

    if ($includeNeo4j) {
        $edgeArgs = "$edgeArgs $neo4jUrl"
        $chromeArgs = "$chromeArgs $neo4jUrl"
        Write-Host "Neo4j Browser will open at $neo4jUrl using the same private window." -ForegroundColor Gray
    }

    Start-Process "msedge" $edgeArgs -ErrorAction SilentlyContinue
    if ($LASTEXITCODE -ne 0) {
        Start-Process "chrome" $chromeArgs -ErrorAction SilentlyContinue
    }
}

function Start-Backend {
    param(
        [string]$Port,
        [string]$ComposeFile
    )
    
    Write-Host "Starting backend directly..." -ForegroundColor Cyan
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
    Write-Host "Press ENTER to open the API documentation in your browser..." -ForegroundColor Yellow
    Write-Host "(The API may take a few seconds to start. Please refresh the page if needed.)" -ForegroundColor Gray
    $null = Read-Host
    
    # Open browser in incognito/private mode, reusing the same window for Neo4j if needed
    Open-BrowserInIncognito -Port $Port -ComposeFile $ComposeFile
    
    Write-Host ""
    docker compose --env-file .env -f $ComposeFile up --build
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
    Write-Host "Starting backend now..." -ForegroundColor Cyan
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
    Write-Host "Press ENTER to open the API documentation in your browser..." -ForegroundColor Yellow
    Write-Host "(The API may take a few seconds to start. Please refresh the page if needed.)" -ForegroundColor Gray
    $null = Read-Host
    
    # Open browser in incognito/private mode, reusing the same window for Neo4j if needed
    Open-BrowserInIncognito -Port $Port -ComposeFile $ComposeFile
    
    Write-Host ""
    docker compose --env-file .env -f $ComposeFile up --build
}

function Invoke-EnvironmentDiagnostics {
    Write-Host "Running Docker/build diagnostics..." -ForegroundColor Yellow
    $diagnosticsScript = "python-dependency-management\scripts\run-docker-build-diagnostics.ps1"
    if (Test-Path $diagnosticsScript) {
        Write-Host "Gathering diagnostic information..." -ForegroundColor Gray
        try {
            & .\$diagnosticsScript
        } catch {
            Write-Host "Diagnostics encountered an error: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "$diagnosticsScript not found" -ForegroundColor Yellow
    }
}

function Invoke-SetupWizard {
    Write-Host "Re-running the interactive setup wizard" -ForegroundColor Cyan
    Write-Host "" 
    Write-Host "To launch the wizard again, delete the .setup-complete file and restart quick-start." -ForegroundColor Gray
    Write-Host "The wizard automatically backs up your current .env before writing a new one." -ForegroundColor Gray
    Write-Host "" 

    if (-not (Test-Path .setup-complete)) {
        Write-Host ".setup-complete is already missing. The next quick-start run will start the wizard automatically." -ForegroundColor Yellow
    }

    $choice = Read-Host "Delete .setup-complete and restart quick-start.ps1 now? (y/N)"
    if ($choice -notmatch "^[Yy]$") {
        Write-Host "No changes were made. Remove .setup-complete manually and run .\quick-start.ps1 when you're ready." -ForegroundColor Yellow
        return 1
    }

    if (Test-Path .setup-complete) {
        Remove-Item .setup-complete -Force -ErrorAction SilentlyContinue
        Write-Host ".setup-complete removed." -ForegroundColor Green
    } else {
        Write-Host ".setup-complete was not found, continuing." -ForegroundColor Gray
    }

    Write-Host "" 
    Write-Host "Now re-run quick-start to start the wizard again:" -ForegroundColor Cyan
    Write-Host "  Windows: .\quick-start.ps1" -ForegroundColor Gray
    Write-Host "  Mac/Linux: ./quick-start.sh" -ForegroundColor Gray
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
    Write-Host "Press ENTER to open the API documentation in your browser..." -ForegroundColor Yellow
    Write-Host "(The API may take a few seconds to start. Please refresh the page if needed.)" -ForegroundColor Gray
    $null = Read-Host
    
    # Open browser in incognito/private mode, reusing the same window for Neo4j if needed
    Open-BrowserInIncognito -Port $Port -ComposeFile $ComposeFile
    
    Write-Host ""
    docker compose --env-file .env -f $ComposeFile build --no-cache
    docker compose --env-file .env -f $ComposeFile up
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

function Show-MainMenu {
    param(
        [string]$Port,
        [string]$ComposeFile
    )

    $menuNext = 1
    $MENU_START = $menuNext; $menuNext++
    $MENU_START_NO_CACHE = $menuNext; $menuNext++
    $MENU_START_BOTH = $menuNext; $menuNext++

    $MENU_DOWN = $menuNext; $menuNext++
    $MENU_DEP_MGMT = $menuNext; $menuNext++
    $MENU_DIAGNOSTICS = $menuNext; $menuNext++

    $MENU_BUILD = $menuNext; $menuNext++
    $MENU_CICD = $menuNext; $menuNext++
    $MENU_BUMP_VERSION = $menuNext; $menuNext++

    $MENU_SETUP = $menuNext; $menuNext++

    $MENU_EXIT = $menuNext

    Write-Host "" 
    Write-Host "================ Main Menu ================" -ForegroundColor Yellow
    Write-Host "" 
    Write-Host "Start:" -ForegroundColor Yellow
    Write-Host "  $MENU_START) Start backend directly (docker compose up)" -ForegroundColor Gray
    Write-Host "  $MENU_START_NO_CACHE) Start backend with --no-cache (fixes caching issues)" -ForegroundColor Gray
    Write-Host "  $MENU_START_BOTH) Both - Dependency Management and then start backend" -ForegroundColor Gray
    Write-Host "" 
    Write-Host "Maintenance:" -ForegroundColor Yellow
    Write-Host "  $MENU_DOWN) Docker Compose Down (stop and remove containers)" -ForegroundColor Gray
    Write-Host "  $MENU_DEP_MGMT) Open Dependency Management only" -ForegroundColor Gray
    Write-Host "  $MENU_DIAGNOSTICS) Run Docker/Build Diagnostics" -ForegroundColor Gray
    Write-Host "" 
    Write-Host "Build / CI/CD:" -ForegroundColor Yellow
    Write-Host "  $MENU_BUILD) Build Production Docker Image" -ForegroundColor Gray
    Write-Host "  $MENU_CICD) Setup CI/CD Pipeline" -ForegroundColor Gray
    Write-Host "  $MENU_BUMP_VERSION) Bump release version for docker image" -ForegroundColor Gray
    Write-Host "" 
    Write-Host "Setup:" -ForegroundColor Yellow
    Write-Host "  $MENU_SETUP) Re-run setup wizard" -ForegroundColor Gray
    Write-Host "" 
    Write-Host "  $MENU_EXIT) Exit" -ForegroundColor Gray
    Write-Host ""
    $choice = Read-Host "Your choice (1-$MENU_EXIT)"

    $summary = $null
    $exitCode = 0

    switch ($choice) {
        "$MENU_START" {
            Start-Backend -Port $Port -ComposeFile $ComposeFile
            $summary = "Backend start triggered (docker compose up)"
        }
        "$MENU_START_NO_CACHE" {
            Start-BackendNoCache -Port $Port -ComposeFile $ComposeFile
            $summary = "Backend start with --no-cache triggered"
        }
        "$MENU_START_BOTH" {
            Start-DependencyAndBackend -Port $Port -ComposeFile $ComposeFile
            $summary = "Dependency Management and backend start executed"
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
        "$MENU_CICD" {
            Start-CICDSetup
            $summary = "CI/CD setup started"
        }
        "$MENU_BUMP_VERSION" {
            Update-ImageVersion
            $summary = "IMAGE_VERSION updated"
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
