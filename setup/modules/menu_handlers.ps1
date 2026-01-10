# menu_handlers.ps1
# PowerShell module for handling menu actions in quick-start script

function Stop-IncognitoProfileProcesses {
    <#
    .SYNOPSIS
    Stops running Edge/Chrome processes that use a specific user-data-dir.

    .PARAMETER ProfileDir
    The profile directory passed via --user-data-dir to target for shutdown.

    .PARAMETER ProcessNames
    Browser process names to search (e.g., msedge.exe, chrome.exe).
    #>
    param(
        [string]$ProfileDir,
        [string[]]$ProcessNames
    )

    if (-not $ProfileDir -or -not $ProcessNames) {
        return
    }

    try {
        $procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
            ($ProcessNames -contains $_.Name) -and ($_.CommandLine -like "*--user-data-dir=$ProfileDir*")
        }
        foreach ($proc in $procs) {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
        }
    } catch {
        Write-Host "[WARN] Failed to stop existing browser processes for profile $ProfileDir" -ForegroundColor Yellow
    }
}

function Open-BrowserInIncognito {
    param(
        [int]$Port,
        [string]$ComposeFile,
        [string]$Mode = ""  # "test" or "admin" for special UI modes
    )

    $apiUrl = "http://localhost:$Port/docs"
    $guiUrl = "http://localhost:$Port/"
    $neo4jUrl = "http://localhost:7474"
    $includeNeo4j = $ComposeFile -like "*neo4j*"

    Write-Host "Opening browser..." -ForegroundColor Cyan

    # Build URL list
    $urls = @($guiUrl, $apiUrl)
    if ($includeNeo4j) {
        $urls += $neo4jUrl
        Write-Host "Neo4j Browser will open at $neo4jUrl using the same private window." -ForegroundColor Gray
    }

    # Add test database admin UIs if in test mode
    if ($Mode -eq "test") {
        $urls += @(
            "http://localhost:5050"  # pgAdmin
            "http://localhost:8080"  # phpMyAdmin
            "http://localhost:7475"  # Neo4j Browser (test)
            "http://localhost:8082"  # Adminer
            "http://localhost:8083"  # SQLite Web
        )
        
        Write-Host ""
        Write-Host "🌐 Opening browser with all admin UIs:" -ForegroundColor Cyan
        Write-Host "  - Backup Manager: $guiUrl" -ForegroundColor Gray
        Write-Host "  - API Docs: $apiUrl" -ForegroundColor Gray
        Write-Host "  - pgAdmin: http://localhost:5050" -ForegroundColor Gray
        Write-Host "  - phpMyAdmin: http://localhost:8080" -ForegroundColor Gray
        Write-Host "  - Neo4j Browser: http://localhost:7475" -ForegroundColor Gray
        Write-Host "  - Adminer: http://localhost:8082" -ForegroundColor Gray
        Write-Host "  - SQLite Web: http://localhost:8083" -ForegroundColor Gray
    }

    # Add admin UIs if in admin mode
    if ($Mode -eq "admin") {
        if ($ComposeFile -like "*postgres*") {
            $urls += "http://localhost:5051"  # pgAdmin for app's postgres
        }
        if ($includeNeo4j) {
            $urls += $neo4jUrl  # Neo4j Browser (app's)
        }
        
        Write-Host ""
        Write-Host "🌐 Opening browser with admin UIs:" -ForegroundColor Cyan
        Write-Host "  - Backup Manager: $guiUrl" -ForegroundColor Gray
        Write-Host "  - API Docs: $apiUrl" -ForegroundColor Gray
        if ($ComposeFile -like "*postgres*") {
            Write-Host "  - pgAdmin (app DB): http://localhost:5051" -ForegroundColor Gray
        }
        if ($includeNeo4j) {
            Write-Host "  - Neo4j Browser: http://localhost:7474" -ForegroundColor Gray
        }
    }

    # Detect Windows: $IsWindows only exists in PS Core 6+; fallback for Windows PowerShell 5.x
    $isWin = $false
    if ($null -ne $IsWindows) {
        $isWin = $IsWindows
    } elseif ($env:OS -match "Windows") {
        $isWin = $true
    }

    Write-Host "[DEBUG] Open-BrowserInIncognito: isWin=$isWin" -ForegroundColor Magenta

    # Always restart browser processes for clean state
    if ($isWin) {
        $profileDir = Join-Path $env:TEMP "edge_incog_profile_backup_restore"
        Stop-IncognitoProfileProcesses -ProfileDir $profileDir -ProcessNames @("msedge.exe")
        
        $profileDir = Join-Path $env:TEMP "chrome_incog_profile_backup_restore"
        Stop-IncognitoProfileProcesses -ProfileDir $profileDir -ProcessNames @("chrome.exe", "msedge.exe")
        
        # Additional cleanup for any processes with backup_restore
        Get-Process | Where-Object { $_.ProcessName -like "*chrome*" -and $_.CommandLine -like "*backup_restore*" } | Stop-Process -Force -ErrorAction SilentlyContinue
        Get-Process | Where-Object { $_.ProcessName -like "*edge*" -and $_.CommandLine -like "*backup_restore*" } | Stop-Process -Force -ErrorAction SilentlyContinue
        
        # Remove profile directories to ensure clean start
        Remove-Item -Path (Join-Path $env:TEMP "edge_incog_profile_backup_restore") -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item -Path (Join-Path $env:TEMP "chrome_incog_profile_backup_restore") -Recurse -Force -ErrorAction SilentlyContinue
    }

    if ($isWin) {
        # Try Edge first (preinstalled on Windows). Use repo-specific profile to separate taskbar groups.
        $edgePaths = @(
            "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
            "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
        )
        foreach ($edgePath in $edgePaths) {
            if (Test-Path $edgePath) {
                Write-Host "[DEBUG] Found Edge at: $edgePath - launching inprivate" -ForegroundColor Magenta
                $profileDir = Join-Path $env:TEMP "edge_incog_profile_backup_restore"
                New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
                Start-Process -FilePath $edgePath -ArgumentList (@("-inprivate", "--user-data-dir=$profileDir") + $urls)
                return
            }
        }

        # Then Chrome in common locations
        $chromePaths = @(
            "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
            "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
            "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
        )
        foreach ($chromePath in $chromePaths) {
            if (Test-Path $chromePath) {
                Write-Host "[DEBUG] Found Chrome at: $chromePath - launching incognito" -ForegroundColor Magenta
                $profileDir = Join-Path $env:TEMP "chrome_incog_profile_backup_restore"
                New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
                Start-Process -FilePath $chromePath -ArgumentList (@("-incognito", "--user-data-dir=$profileDir") + $urls)
                return
            }
        }

        # Try Firefox in common locations
        $firefoxPaths = @(
            "$env:ProgramFiles\Mozilla Firefox\firefox.exe",
            "${env:ProgramFiles(x86)}\Mozilla Firefox\firefox.exe"
        )
        foreach ($firefoxPath in $firefoxPaths) {
            if (Test-Path $firefoxPath) {
                Write-Host "[DEBUG] Found Firefox at: $firefoxPath - launching private" -ForegroundColor Magenta
                Start-Process -FilePath $firefoxPath -ArgumentList (@("-private-window") + $urls)
                return
            }
        }

        Write-Host "[DEBUG] No browser found, using default handler (NOT incognito)" -ForegroundColor Yellow
        foreach ($url in $urls) {
            Start-Process $url -ErrorAction SilentlyContinue
        }
        return
    }

    # macOS/Linux fallback
    foreach ($url in $urls) {
        Start-Process $url -ErrorAction SilentlyContinue
    }
}

function Start-Backend {
    param(
        [string]$Port,
        [string]$ComposeFile
    )
    
    Write-Host "🚀 Starting Backend with Database..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "  Services starting:" -ForegroundColor Yellow
    Write-Host "  - Backend API (port $Port)" -ForegroundColor Gray
    Write-Host "  - PostgreSQL database" -ForegroundColor Gray
    Write-Host "  - Web GUI at http://localhost:$Port/" -ForegroundColor Gray
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Browser will open automatically when API is ready..." -ForegroundColor Yellow
    Write-Host ""
    
    # Start browser opening in background
    Show-ApiDocsDelayed -Port $Port -TimeoutSeconds 120
    
    Write-Host ""
    docker compose --env-file .env -f $ComposeFile up --build --no-cache
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
    Write-Host "🌐 Browser will open automatically when API is ready..." -ForegroundColor Yellow
    Write-Host ""
    
    # Start browser opening in background
    Show-ApiDocsDelayed -Port $Port -TimeoutSeconds 120
    
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
    Write-Host "🌐 Browser will open automatically when API is ready..." -ForegroundColor Yellow
    Write-Host ""
    
    # Start browser opening in background
    Show-ApiDocsDelayed -Port $Port -TimeoutSeconds 120
    
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

function Deploy-AllServices {
    <#
    .SYNOPSIS
    Deploys all services (Backend + Runner + GUI) for backup automation.
    #>
    param(
        [int]$Port,
        [string]$ComposeFile
    )

    Write-Host "🚀 Deploying all services (Backend + Runner)..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "   Services:" -ForegroundColor Gray
    Write-Host "   - Backend API (port $Port)" -ForegroundColor Gray
    Write-Host "   - PostgreSQL database" -ForegroundColor Gray
    Write-Host "   - Backup runner (periodic execution)" -ForegroundColor Gray
    Write-Host "   - Web GUI at http://localhost:$Port/" -ForegroundColor Gray
    Write-Host ""

    # Check if runner compose file exists
    $runnerFile = "local-deployment/docker-compose.runner.yml"
    if (-not (Test-Path $runnerFile)) {
        Write-Host "❌ Runner compose file not found: $runnerFile" -ForegroundColor Red
        return
    }

    Write-Host "🐳 Starting services..." -ForegroundColor Cyan
    docker compose --env-file .env -f $ComposeFile -f $runnerFile up -d --build

    Write-Host ""
    Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Cyan

    # Wait for backend health
    $maxWait = 30
    $waitCount = 0
    do {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$Port/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host "✅ Backend is ready!" -ForegroundColor Green
                break
            }
        } catch {
            # Continue waiting
        }
        Write-Host "." -NoNewline -ForegroundColor Gray
        Start-Sleep -Seconds 2
        $waitCount++
    } while ($waitCount -lt $maxWait)

    if ($waitCount -eq $maxWait) {
        Write-Host ""
        Write-Host "❌ Backend failed to start within ${maxWait}s" -ForegroundColor Red
        Write-Host "   Check logs: docker compose logs" -ForegroundColor Yellow
        return
    }

    Write-Host ""
    Write-Host "🌐 Opening Backup Manager GUI..." -ForegroundColor Cyan
    Open-BackupGUI -Port $Port

    Write-Host ""
    Write-Host "✅ All services deployed and running!" -ForegroundColor Green
    Write-Host ""
    Write-Host "   Services status:" -ForegroundColor Gray
    docker compose --env-file .env -f $ComposeFile -f $runnerFile ps
    Write-Host ""
    Write-Host "   To stop all services:" -ForegroundColor Gray
    Write-Host "     docker compose --env-file .env -f $ComposeFile -f $runnerFile down" -ForegroundColor Gray
}

function Open-BackupGUI {
    <#
    .SYNOPSIS
    Opens the Backup Manager GUI in the default browser.
    #>
    param(
        [int]$Port
    )

    Write-Host "🌐 Opening Backup Manager GUI..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "   URL: http://localhost:$Port/" -ForegroundColor Gray
    Write-Host ""

    $url = "http://localhost:$Port/"
    Start-Process $url
}

function Invoke-BackupNow {
    <#
    .SYNOPSIS
    Interactively runs a backup schedule via CLI.
    #>
    param(
        [int]$Port
    )

    Write-Host "⚡ Run Backup Now" -ForegroundColor Cyan
    Write-Host ""

    # Check if API is running
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$Port/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -ne 200) {
            throw "API not ready"
        }
    } catch {
        Write-Host "❌ API is not running. Please start the backend first." -ForegroundColor Red
        return
    }

    # Get admin key from .env
    $adminKey = ""
    if (Test-Path ".env") {
        $adminKey = (Select-String -Path ".env" -Pattern "^ADMIN_API_KEY=" -SimpleMatch).Line -replace "^ADMIN_API_KEY=", "" -replace '"', ''
    }

    if (-not $adminKey) {
        $adminKey = Read-Host "Enter Admin API Key"
    }

    # List schedules
    Write-Host "📋 Fetching schedules..." -ForegroundColor Cyan
    try {
        $schedulesResponse = Invoke-RestMethod -Uri "http://localhost:$Port/automation/schedules" -Headers @{ "X-Admin-Key" = $adminKey } -ErrorAction Stop
    } catch {
        Write-Host "❌ Failed to fetch schedules. Check your API key." -ForegroundColor Red
        return
    }

    Write-Host ""
    Write-Host "Available schedules:" -ForegroundColor Gray
    if ($schedulesResponse.Count -eq 0) {
        Write-Host "  No schedules configured. Use the web GUI to create one." -ForegroundColor Yellow
        return
    }

    for ($i = 0; $i -lt $schedulesResponse.Count; $i++) {
        $schedule = $schedulesResponse[$i]
        $shortId = $schedule.id.Substring(0, [Math]::Min(8, $schedule.id.Length))
        Write-Host "  $($i + 1)) $($schedule.name) (ID: $shortId...)" -ForegroundColor Gray
    }

    Write-Host ""
    $scheduleChoice = Read-Host "Enter schedule number to run (or 'q' to cancel)"

    if ($scheduleChoice -eq 'q') {
        Write-Host "Cancelled." -ForegroundColor Yellow
        return
    }

    # Validate choice
    $scheduleIndex = [int]$scheduleChoice - 1
    if ($scheduleIndex -lt 0 -or $scheduleIndex -ge $schedulesResponse.Count) {
        Write-Host "❌ Invalid selection." -ForegroundColor Red
        return
    }

    $scheduleId = $schedulesResponse[$scheduleIndex].id

    Write-Host ""
    Write-Host "🚀 Running backup..." -ForegroundColor Cyan
    try {
        $result = Invoke-RestMethod -Uri "http://localhost:$Port/automation/schedules/$scheduleId/run-now" -Method POST -Headers @{ "X-Admin-Key" = $adminKey } -ErrorAction Stop
        
        if ($result.backup_filename) {
            Write-Host "✅ Backup completed successfully!" -ForegroundColor Green
            Write-Host "   Filename: $($result.backup_filename)" -ForegroundColor Gray
        } else {
            Write-Host "❌ Backup failed:" -ForegroundColor Red
            Write-Host ($result | ConvertTo-Json -Depth 10) -ForegroundColor Red
        }
    } catch {
        Write-Host "❌ Backup failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Show-BackupList {
    <#
    .SYNOPSIS
    Lists available backup files.
    #>
    param(
        [int]$Port
    )

    Write-Host "📁 List Backup Files" -ForegroundColor Cyan
    Write-Host ""

    # Check if API is running
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$Port/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -ne 200) {
            throw "API not ready"
        }
    } catch {
        Write-Host "❌ API is not running. Please start the backend first." -ForegroundColor Red
        return
    }

    # Get admin key from .env
    $adminKey = ""
    if (Test-Path ".env") {
        $adminKey = (Select-String -Path ".env" -Pattern "^ADMIN_API_KEY=" -SimpleMatch).Line -replace "^ADMIN_API_KEY=", "" -replace '"', ''
    }

    if (-not $adminKey) {
        $adminKey = Read-Host "Enter Admin API Key"
    }

    Write-Host "📋 Fetching backup files..." -ForegroundColor Cyan
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:$Port/backup/list" -Headers @{ "X-Admin-Key" = $adminKey } -ErrorAction Stop
    } catch {
        Write-Host "❌ Failed to fetch backup files. Check your API key." -ForegroundColor Red
        return
    }

    Write-Host ""
    if ($response.files.Count -eq 0) {
        Write-Host "  No backup files found." -ForegroundColor Yellow
    } else {
        Write-Host "  Found $($response.count) backup(s):" -ForegroundColor Gray
        Write-Host ""
        foreach ($file in $response.files) {
            Write-Host "  - $($file.filename)" -ForegroundColor Gray
            Write-Host "    Size: $($file.size_mb) MB | Created: $($file.created_at)" -ForegroundColor Gray
        }
    }
}

function Start-WithTestDatabases {
    <#
    .SYNOPSIS
    Starts all services with test databases for all supported DB types.
    #>
    param(
        [int]$Port,
        [string]$ComposeFile
    )

    Write-Host "🧪 Starting with Test Databases..." -ForegroundColor Cyan
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
    Write-Host "  - SQLite Web: http://localhost:8083" -ForegroundColor Gray
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host ""

    $testDbFile = "local-deployment/docker-compose.test-databases.yml"
    $runnerFile = "local-deployment/docker-compose.runner.yml"

    if (-not (Test-Path $testDbFile)) {
        Write-Host "❌ Test databases compose file not found: $testDbFile" -ForegroundColor Red
        return
    }

    if (-not (Test-Path $runnerFile)) {
        Write-Host "❌ Runner compose file not found: $runnerFile" -ForegroundColor Red
        return
    }

    Write-Host ""
    Write-Host "🧹 Cleaning up old test database data..." -ForegroundColor Cyan
    
    # Remove test database data to ensure fresh setup
    Remove-Item -Path ".docker/test-*" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path ".docker/pgadmin-data" -Recurse -Force -ErrorAction SilentlyContinue
    
    Write-Host "✅ Old test data removed" -ForegroundColor Green
    Write-Host ""
    Write-Host "🐳 Starting all services with test databases..." -ForegroundColor Cyan
    $composeJob = Start-Job -ScriptBlock {
        param($envFile, $composeFile, $runnerFile, $testDbFile)
        docker compose --env-file $envFile -f $composeFile -f $runnerFile -f $testDbFile up --build
    } -ArgumentList ".env", $ComposeFile, $runnerFile, $testDbFile

    Write-Host ""
    Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Cyan
    
    # Wait for API to be ready
    $maxWait = 120
    $waitTime = 0
    $apiReady = $false
    
    while ($waitTime -lt $maxWait) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$Port/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host "`n✅ API is ready!" -ForegroundColor Green
                $apiReady = $true
                break
            }
        } catch {
            # API not ready yet
        }
        
        Write-Host -NoNewline "."
        Start-Sleep -Seconds 2
        $waitTime += 2
    }
    
    if (-not $apiReady) {
        Write-Host "`n⚠️  API not ready after $maxWait seconds, opening browser anyway..." -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "🌐 Opening browser with all admin UIs..." -ForegroundColor Cyan
    
    # Open browser now that services are ready
    Open-BrowserInIncognito -Port $Port -ComposeFile $ComposeFile -Mode "test"

    Write-Host ""
    Write-Host "✅ All services with test databases started!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Service status:" -ForegroundColor Gray
    docker compose --env-file .env -f $ComposeFile -f $runnerFile -f $testDbFile ps
    
    Write-Host ""
    Write-Host "Press Ctrl+C to stop all services..." -ForegroundColor Yellow
    
    # Wait for the compose job to finish (when user presses Ctrl+C)
    try {
        Wait-Job -Job $composeJob | Out-Null
    } finally {
        Remove-Job -Job $composeJob -Force -ErrorAction SilentlyContinue
    }
}

function Start-WithAdminUIs {
    <#
    .SYNOPSIS
    Starts services with admin UIs for the app's own database.
    #>
    param(
        [int]$Port,
        [string]$ComposeFile
    )

    Write-Host "🖥️  Starting Admin UIs..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "  Services starting:" -ForegroundColor Yellow
    Write-Host "  - Backend API (port $Port)" -ForegroundColor Gray
    Write-Host "  - App's database" -ForegroundColor Gray
    Write-Host "" -ForegroundColor Yellow
    Write-Host "  Admin UIs:" -ForegroundColor Yellow
    if ($ComposeFile -like "*postgres*") {
        Write-Host "  - pgAdmin (app DB): http://localhost:5051" -ForegroundColor Gray
    }
    if ($ComposeFile -like "*neo4j*") {
        Write-Host "  - Neo4j Browser: http://localhost:7474" -ForegroundColor Gray
    }
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host ""

    $runnerFile = "local-deployment/docker-compose.runner.yml"

    if (-not (Test-Path $runnerFile)) {
        Write-Host "❌ Runner compose file not found: $runnerFile" -ForegroundColor Red
        return
    }

    Write-Host ""
    Write-Host "🐳 Starting services with admin profile..." -ForegroundColor Cyan
    $composeJob = Start-Job -ScriptBlock {
        param($envFile, $composeFile, $runnerFile)
        docker compose --env-file $envFile -f $composeFile -f $runnerFile --profile admin up --build
    } -ArgumentList ".env", $ComposeFile, $runnerFile

    Write-Host ""
    Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Cyan
    
    # Wait for API to be ready
    $maxWait = 120
    $waitTime = 0
    $apiReady = $false
    
    while ($waitTime -lt $maxWait) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$Port/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host "`n✅ API is ready!" -ForegroundColor Green
                $apiReady = $true
                break
            }
        } catch {
            # API not ready yet
        }
        
        Write-Host -NoNewline "."
        Start-Sleep -Seconds 2
        $waitTime += 2
    }
    
    if (-not $apiReady) {
        Write-Host "`n⚠️  API not ready after $maxWait seconds, opening browser anyway..." -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "🌐 Opening browser with admin UIs..." -ForegroundColor Cyan
    
    # Open browser now that services are ready
    Open-BrowserInIncognito -Port $Port -ComposeFile $ComposeFile -Mode "admin"

    Write-Host ""
    Write-Host "✅ Services with admin UIs started!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Service status:" -ForegroundColor Gray
    docker compose --env-file .env -f $ComposeFile -f $runnerFile --profile admin ps
    
    Write-Host ""
    Write-Host "Press Ctrl+C to stop all services..." -ForegroundColor Yellow
    
    # Wait for the compose job to finish (when user presses Ctrl+C)
    try {
        Wait-Job -Job $composeJob | Out-Null
    } finally {
        Remove-Job -Job $composeJob -Force -ErrorAction SilentlyContinue
    }
}

function Show-MainMenu {
    param(
        [string]$Port,
        [string]$ComposeFile
    )

    $menuNext = 1
    $MENU_START_ALL = $menuNext; $menuNext++

    $MENU_DOWN = $menuNext; $menuNext++
    $MENU_DEP_MGMT = $menuNext; $menuNext++
    $MENU_DIAGNOSTICS = $menuNext; $menuNext++

    $MENU_BUILD = $menuNext; $menuNext++
    $MENU_CICD = $menuNext; $menuNext++
    $MENU_BUMP_VERSION = $menuNext; $menuNext++

    $MENU_RUN_BACKUP = $menuNext; $menuNext++
    $MENU_LIST_BACKUPS = $menuNext; $menuNext++

    $MENU_TEST_DBS = $menuNext; $menuNext++
    $MENU_TEST_DBS_ADMIN = $menuNext; $menuNext++

    $MENU_SETUP = $menuNext; $menuNext++

    $MENU_EXIT = $menuNext

    Write-Host "" 
    Write-Host "================ Main Menu ================" -ForegroundColor Yellow
    Write-Host "" 
    Write-Host "Start:" -ForegroundColor Yellow
    Write-Host "  $MENU_START_ALL) Start all services (Backend + Database + Runner + GUI)" -ForegroundColor Gray
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
    Write-Host "Backup Automation:" -ForegroundColor Yellow
    Write-Host "  $MENU_RUN_BACKUP) Run backup now (CLI)" -ForegroundColor Gray
    Write-Host "  $MENU_LIST_BACKUPS) List backup files" -ForegroundColor Gray
    Write-Host "" 
    Write-Host "Testing (all DB types + admin UIs):" -ForegroundColor Yellow
    Write-Host "  $MENU_TEST_DBS) Start with test databases" -ForegroundColor Gray
    Write-Host "  $MENU_TEST_DBS_ADMIN) Start with admin UIs only" -ForegroundColor Gray
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
        "$MENU_START_ALL" {
            Deploy-AllServices -Port $Port -ComposeFile $ComposeFile
            $summary = "All services started"
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
