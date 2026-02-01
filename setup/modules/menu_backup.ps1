<#
.SYNOPSIS
    Backup operations module for Backup-Restore quick-start menu.

.DESCRIPTION
    This module provides functions for backup-related operations including
    running backups, listing backup files, and managing backup schedules.

.NOTES
    Author: Auto-generated
    Date: 2026-01-29
    Version: 1.0.0
#>

function Get-KeycloakAccessToken {
    <#
    .SYNOPSIS
        Retrieve a Keycloak access token using client credentials.

    .PARAMETER EnvFile
        Path to the environment file.

    .RETURNS
        Access token string.
    #>
    param(
        [string]$EnvFile = ".env"
    )

    $accessToken = $env:ACCESS_TOKEN
    if ($accessToken) {
        return $accessToken
    }

    $keycloakUrl = ""
    $keycloakRealm = ""
    $keycloakClientId = ""
    $keycloakClientSecret = ""

    if (Test-Path $EnvFile) {
        $envContent = Get-Content $EnvFile -ErrorAction SilentlyContinue
        
        $line = $envContent | Where-Object { $_ -match "^KEYCLOAK_URL=" }
        if ($line) { $keycloakUrl = ($line -split "=", 2)[1].Trim().Trim('"') }
        
        $line = $envContent | Where-Object { $_ -match "^KEYCLOAK_INTERNAL_URL=" }
        if ($line) { 
            $internalUrl = ($line -split "=", 2)[1].Trim().Trim('"')
            if ($internalUrl) { $keycloakUrl = $internalUrl }
        }
        
        $line = $envContent | Where-Object { $_ -match "^KEYCLOAK_REALM=" }
        if ($line) { $keycloakRealm = ($line -split "=", 2)[1].Trim().Trim('"') }
        
        $line = $envContent | Where-Object { $_ -match "^KEYCLOAK_CLIENT_ID=" }
        if ($line) { $keycloakClientId = ($line -split "=", 2)[1].Trim().Trim('"') }
        
        $line = $envContent | Where-Object { $_ -match "^KEYCLOAK_CLIENT_SECRET=" }
        if ($line) { $keycloakClientSecret = ($line -split "=", 2)[1].Trim().Trim('"') }
    }

    if ($keycloakUrl -and $keycloakRealm -and $keycloakClientId -and $keycloakClientSecret) {
        $tokenEndpoint = "$($keycloakUrl.TrimEnd('/'))/realms/$keycloakRealm/protocol/openid-connect/token"
        $body = @{ 
            grant_type = "client_credentials"
            client_id = $keycloakClientId
            client_secret = $keycloakClientSecret
        }
        try {
            $tokenResponse = Invoke-RestMethod -Method Post -Uri $tokenEndpoint -Body $body -ContentType "application/x-www-form-urlencoded" -ErrorAction Stop
            if ($tokenResponse.access_token) {
                return $tokenResponse.access_token
            }
        } catch {
            Write-Host "[WARN] Failed to fetch Keycloak access token: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }

    return Read-Host "Enter Keycloak access token"
}

function Invoke-BackupNow {
    <#
    .SYNOPSIS
        Interactively runs a backup schedule via CLI.

    .PARAMETER Port
        API port number.
    #>
    param(
        [int]$Port
    )

    Write-Host "[RUN] Run Backup Now" -ForegroundColor Cyan
    Write-Host ""

    # Check if API is running
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$Port/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -ne 200) {
            throw "API not ready"
        }
    } catch {
        Write-Host "[ERROR] API is not running. Please start the backend first." -ForegroundColor Red
        return
    }

    $accessToken = Get-KeycloakAccessToken
    if (-not $accessToken) {
        Write-Host "[ERROR] Missing Keycloak access token." -ForegroundColor Red
        return
    }

    # List schedules
    Write-Host "[LIST] Fetching schedules..." -ForegroundColor Cyan
    try {
        $schedulesResponse = Invoke-RestMethod -Uri "http://localhost:$Port/automation/schedules" -Headers @{ Authorization = "Bearer $accessToken" } -ErrorAction Stop
    } catch {
        Write-Host "[ERROR] Failed to fetch schedules. Check your access token." -ForegroundColor Red
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
        Write-Host "[ERROR] Invalid selection." -ForegroundColor Red
        return
    }

    $scheduleId = $schedulesResponse[$scheduleIndex].id

    Write-Host ""
    Write-Host "[INFO] Running backup..." -ForegroundColor Cyan
    try {
        $result = Invoke-RestMethod -Uri "http://localhost:$Port/automation/schedules/$scheduleId/run-now" -Method POST -Headers @{ Authorization = "Bearer $accessToken" } -ErrorAction Stop
        
        if ($result.backup_filename) {
            Write-Host "[OK] Backup completed successfully!" -ForegroundColor Green
            Write-Host "   Filename: $($result.backup_filename)" -ForegroundColor Gray
        } else {
            Write-Host "[ERROR] Backup failed:" -ForegroundColor Red
            Write-Host ($result | ConvertTo-Json -Depth 10) -ForegroundColor Red
        }
    } catch {
        Write-Host "[ERROR] Backup failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Show-BackupList {
    <#
    .SYNOPSIS
        Lists available backup files.

    .PARAMETER Port
        API port number.
    #>
    param(
        [int]$Port
    )

    Write-Host "[FILES] List Backup Files" -ForegroundColor Cyan
    Write-Host ""

    # Check if API is running
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$Port/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -ne 200) {
            throw "API not ready"
        }
    } catch {
        Write-Host "[ERROR] API is not running. Please start the backend first." -ForegroundColor Red
        return
    }

    $accessToken = Get-KeycloakAccessToken
    if (-not $accessToken) {
        Write-Host "[ERROR] Missing Keycloak access token." -ForegroundColor Red
        return
    }

    Write-Host "[LIST] Fetching backup files..." -ForegroundColor Cyan
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:$Port/backup/list" -Headers @{ Authorization = "Bearer $accessToken" } -ErrorAction Stop
    } catch {
        Write-Host "[ERROR] Failed to fetch backup files. Check your access token." -ForegroundColor Red
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

function Open-BackupGUI {
    <#
    .SYNOPSIS
        Opens the Backup Manager GUI in the default browser.

    .PARAMETER Port
        API port number.
    #>
    param(
        [int]$Port
    )

    Write-Host "[WEB] Opening Backup Manager GUI..." -ForegroundColor Cyan
    Write-Host ""
    
    $webPort = "8086"
    if (Test-Path ".env") {
        $envContent = Get-Content ".env" -ErrorAction SilentlyContinue
        $line = $envContent | Where-Object { $_ -match "^WEB_PORT=" }
        if ($line) { $webPort = ($line -split "=", 2)[1].Trim().Trim('"') }
    }
    
    Write-Host "   URL: http://localhost:$webPort/" -ForegroundColor Gray
    Write-Host ""

    $url = "http://localhost:$webPort/"
    Start-Process $url
}
