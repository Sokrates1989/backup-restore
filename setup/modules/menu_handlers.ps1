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

function Invoke-DockerComposeDown {
    param(
        [string]$ComposeFile
    )
    
    Write-Host "Stopping and removing containers..." -ForegroundColor Yellow
    Write-Host "   Using compose file: $ComposeFile" -ForegroundColor Gray
    Write-Host ""
    docker compose --env-file .env -f $ComposeFile down
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

    $hasCognito = [bool](Get-Command Invoke-CognitoSetup -ErrorAction SilentlyContinue)
    Write-Host "Choose an option:" -ForegroundColor Yellow
    Write-Host "1) Start backend directly (docker compose up)" -ForegroundColor Gray
    Write-Host "2) Start backend with --no-cache (fixes caching issues)" -ForegroundColor Gray
    Write-Host "3) Docker Compose Down (stop and remove containers)" -ForegroundColor Gray
    Write-Host "4) Open Dependency Management only" -ForegroundColor Gray
    Write-Host "5) Both - Dependency Management and then start backend" -ForegroundColor Gray
    Write-Host "6) Run Docker/Build Diagnostics" -ForegroundColor Gray
    Write-Host "7) Configure AWS Cognito" -ForegroundColor Gray
    Write-Host "8) Build Production Docker Image" -ForegroundColor Gray
    Write-Host "9) Setup CI/CD Pipeline" -ForegroundColor Gray
    Write-Host "10) Bump release version for docker image" -ForegroundColor Gray
    Write-Host "11) Exit" -ForegroundColor Gray
    Write-Host ""
    $choice = Read-Host "Your choice (1-11)"

    $summary = $null
    $exitCode = 0

    switch ($choice) {
        "1" {
            Start-Backend -Port $Port -ComposeFile $ComposeFile
            $summary = "Backend start triggered (docker compose up)"
        }
        "2" {
            Start-BackendNoCache -Port $Port -ComposeFile $ComposeFile
            $summary = "Backend start with --no-cache triggered"
        }
        "3" {
            Invoke-DockerComposeDown -ComposeFile $ComposeFile
            $summary = "Docker Compose Down executed"
        }
        "4" {
            Start-DependencyManagement
            Write-Host "To start the backend, run: docker compose -f $ComposeFile up --build" -ForegroundColor Yellow
            $summary = "Dependency Management executed"
        }
        "5" {
            Start-DependencyAndBackend -Port $Port -ComposeFile $ComposeFile
            $summary = "Dependency Management and backend start executed"
        }
        "6" {
            Invoke-EnvironmentDiagnostics
            $summary = "Docker/Build diagnostics launched"
        }
        "7" {
            if ($hasCognito) {
                Invoke-CognitoSetup
                $summary = "AWS Cognito setup executed"
            } else {
                Write-Host "AWS Cognito module not loaded." -ForegroundColor Yellow
                Write-Host "Ensure setup/modules/cognito_setup.ps1 is imported before selecting this option." -ForegroundColor Yellow
                $summary = "AWS Cognito setup could not run"
                $exitCode = 1
            }
        }
        "8" {
            Build-ProductionImage
            $summary = "Production Docker image build triggered"
        }
        "9" {
            Start-CICDSetup
            $summary = "CI/CD setup started"
        }
        "10" {
            Update-ImageVersion
            $summary = "IMAGE_VERSION updated"
        }
        "11" {
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
        Write-Host ("✅ {0}" -f $summary) -ForegroundColor Green
    }
    Write-Host 'ℹ️  Quick-start finished. Run the script again for more actions.' -ForegroundColor Cyan
    Write-Host ""
    exit $exitCode
}
