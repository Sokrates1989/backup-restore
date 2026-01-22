<#
menu_browser.ps1

Module for browser-related menu actions.
Uses shared browser_helpers.ps1 for incognito mode with first-run suppression.
#>

function Open-BrowserInIncognito {
    <#
    .SYNOPSIS
    Opens multiple URLs in an incognito browser window for backup-restore.

    .PARAMETER Port
    API port number.

    .PARAMETER ComposeFile
    Docker compose file path (used to detect neo4j).

    .PARAMETER Mode
    Optional mode: "test" or "admin" for special UI modes.
    #>
    param(
        [int]$Port,
        [string]$ComposeFile,
        [string]$Mode = ""
    )

    $apiUrl = "http://localhost:$Port/docs"
    $webPort = Get-EnvVariable -VariableName "WEB_PORT" -EnvFile ".env" -DefaultValue "8086"
    $guiUrl = "http://localhost:$webPort/"
    $neo4jUrl = "http://localhost:7474"
    $includeNeo4j = $ComposeFile -like "*neo4j*"

    Write-Host "Opening browser..." -ForegroundColor Cyan

    # Open main URLs using shared helper (suppresses first-run prompts)
    Open-Url -Url $guiUrl
    Start-Sleep -Seconds 1
    Open-Url -Url $apiUrl

    if ($includeNeo4j) {
        Start-Sleep -Seconds 1
        Open-Url -Url $neo4jUrl
        Write-Host "Neo4j Browser will open at $neo4jUrl" -ForegroundColor Gray
    }

    # Add test database admin UIs if in test mode
    if ($Mode -eq "test") {
        Write-Host ""
        Write-Host "[WEB] Opening browser with all admin UIs:" -ForegroundColor Cyan
        Write-Host "  - Backup Manager: $guiUrl" -ForegroundColor Gray
        Write-Host "  - API Docs: $apiUrl" -ForegroundColor Gray
        Write-Host "  - pgAdmin: http://localhost:5050" -ForegroundColor Gray
        Write-Host "  - phpMyAdmin: http://localhost:8080" -ForegroundColor Gray
        Write-Host "  - Neo4j Browser: http://localhost:7475" -ForegroundColor Gray
        Write-Host "  - Adminer: http://localhost:8082" -ForegroundColor Gray
        Write-Host "  - Adminer (SQLite): http://localhost:8085" -ForegroundColor Gray
        Write-Host "  - SQLite Web: http://localhost:8084" -ForegroundColor Gray
        Write-Host "  - SQLite Browser (GUI): http://localhost:8090" -ForegroundColor Gray

        Start-Sleep -Seconds 1
        Open-Url -Url "http://localhost:5050"
        Start-Sleep -Milliseconds 500
        Open-Url -Url "http://localhost:8080"
        Start-Sleep -Milliseconds 500
        Open-Url -Url "http://localhost:7475/browser?connectURL=neo4j://localhost:7688"
        Start-Sleep -Milliseconds 500
        Open-Url -Url "http://localhost:8082"
        Start-Sleep -Milliseconds 500
        Open-Url -Url "http://localhost:8085"
        Start-Sleep -Milliseconds 500
        Open-Url -Url "http://localhost:8084"
        Start-Sleep -Milliseconds 500
        Open-Url -Url "http://localhost:8090"
    }

    # Add admin UIs if in admin mode
    if ($Mode -eq "admin") {
        Write-Host ""
        Write-Host "[WEB] Opening browser with admin UIs:" -ForegroundColor Cyan
        Write-Host "  - Backup Manager: $guiUrl" -ForegroundColor Gray
        Write-Host "  - API Docs: $apiUrl" -ForegroundColor Gray
        if ($ComposeFile -like "*postgres*") {
            Write-Host "  - pgAdmin (app DB): http://localhost:5051" -ForegroundColor Gray
            Start-Sleep -Seconds 1
            Open-Url -Url "http://localhost:5051"
        }
        if ($includeNeo4j) {
            Write-Host "  - Neo4j Browser: http://localhost:7474" -ForegroundColor Gray
        }
    }
}
