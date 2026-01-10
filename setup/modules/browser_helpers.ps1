<#
browser_helpers.ps1

Purpose:
- Helper utilities for backup-restore quick-start scripts.
- Opens URLs in incognito/private browser mode with auto-close on restart.

Notes:
- Best-effort only: should not break quick-start execution.
#>

# Global flag to track if browser has been cleaned for this session
$script:BrowserCleaned = $false

function Wait-ForUrl {
    <#
    .SYNOPSIS
    Waits for a URL to become available by polling until it returns a valid HTTP status.

    .PARAMETER Url
    The URL to check.

    .PARAMETER TimeoutSeconds
    Maximum time to wait in seconds (default: 120).

    .PARAMETER IntervalMs
    Time between checks in milliseconds (default: 500).

    .OUTPUTS
    Boolean. Returns $true if URL became available, $false if timeout reached.
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$Url,
        [int]$TimeoutSeconds = 120,
        [int]$IntervalMs = 500
    )
    
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    while ($stopwatch.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        try {
            $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) { return $true }
        } catch {
            try {
                $ex = $_.Exception
                if ($ex -and $ex.Response -and $ex.Response.StatusCode) {
                    $status = [int]$ex.Response.StatusCode
                    if ($status -eq 405) { return $true }
                }
            } catch {
            }
        }
        
        Start-Sleep -Milliseconds $IntervalMs
    }
    
    return $false
}

function Stop-IncognitoProfileProcesses {
    <#
    .SYNOPSIS
    Stops running Edge/Chrome processes that use a specific user-data-dir.
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$ProfileDir,
        [Parameter(Mandatory=$true)]
        [string[]]$ProcessNames
    )
    
    if (-not $ProfileDir -or -not $ProcessNames) {
        return
    }

    try {
        foreach ($procName in $ProcessNames) {
            Get-Process | Where-Object { $_.ProcessName -eq $procName -and $_.CommandLine -like "*--user-data-dir=$ProfileDir*" } | Stop-Process -Force -ErrorAction SilentlyContinue
            ($ProcessNames -contains $_.Name) -and ($_.CommandLine -like "*--user-data-dir=$ProfileDir*")
        }
        foreach ($proc in $procs) {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
        }
    } catch {
        Write-Host "[WARN] Failed to stop existing browser processes for profile $ProfileDir" -ForegroundColor Yellow
    }
}

$script:IncognitoProfileCleaned = $false

function Open-Url {
    <#
    .SYNOPSIS
    Opens a URL in an incognito/private browser window with backup-restore-specific profile.

    .PARAMETER Url
    URL to open.
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$Url
    )

    # Only clean browser processes once per session
    if (-not $script:BrowserCleaned) {
        $edgeProfile = Join-Path $env:TEMP "edge_incog_profile_backup-restore"
        $chromeProfile = Join-Path $env:TEMP "chrome_incog_profile_backup-restore"
        New-Item -ItemType Directory -Path $edgeProfile -Force | Out-Null
        New-Item -ItemType Directory -Path $chromeProfile -Force | Out-Null
        
        Stop-IncognitoProfileProcesses -ProfileDir $edgeProfile -ProcessNames @("msedge.exe")
        Stop-IncognitoProfileProcesses -ProfileDir $chromeProfile -ProcessNames @("chrome.exe")
        
        $script:BrowserCleaned = $true
                return
            }
            if (Test-Path "/Applications/Microsoft Edge.app") {
                & open -na "Microsoft Edge" --args -inprivate $Url 2>$null
                return
            }
            if (Test-Path "/Applications/Firefox.app") {
                & open -na "Firefox" --args -private-window $Url 2>$null
                return
            }
            & open $Url 2>$null
            return
        }

        # Linux
        if ($IsLinux) {
            $linuxChrome = Get-Command google-chrome -ErrorAction SilentlyContinue
            if ($linuxChrome) { & $linuxChrome.Source --incognito $Url 2>$null | Out-Null; return }
            $linuxFirefox = Get-Command firefox -ErrorAction SilentlyContinue
            if ($linuxFirefox) { & $linuxFirefox.Source -private-window $Url 2>$null | Out-Null; return }
            $xdgOpen = Get-Command xdg-open -ErrorAction SilentlyContinue
            if ($xdgOpen) { & $xdgOpen.Source $Url 2>$null | Out-Null; return }
        }

        Start-Process $Url | Out-Null
    } catch {
        Write-Host "[WARN] Could not open browser automatically. Please open manually: $Url" -ForegroundColor Yellow
    }
}

function Show-ApiDocsDelayed {
    <#
    .SYNOPSIS
    Prints API documentation URL and opens it when the service becomes available.

    .PARAMETER Port
    Port number for the API service.

    .PARAMETER TimeoutSeconds
    Maximum time to wait for service in seconds (default: 120).

    .NOTES
    Uses Open-Url to open in incognito mode with auto-restart capability.
    #>
    param(
        [int]$Port,
        [int]$TimeoutSeconds = 120
    )

    $apiUrl = "http://localhost:$Port/docs"
    $apiHealthUrl = "http://localhost:$Port/health"
    $webUrl = "http://localhost:$Port/"

    Write-Host "" 
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "  API will be accessible at:" -ForegroundColor Yellow
    Write-Host "  - API Docs: $apiUrl" -ForegroundColor Gray
    Write-Host "  - Web GUI: $webUrl" -ForegroundColor Gray
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "" 
    Write-Host "Browser will open automatically when API is ready..." -ForegroundColor Yellow
    Write-Host ""

    $scriptPath = $PSScriptRoot
    if (-not $scriptPath) {
        $scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
    }
    $browserHelpersFile = Join-Path $scriptPath "browser_helpers.ps1"
    
    $tempScript = Join-Path $env:TEMP "backup_restore_browser_open_$([guid]::NewGuid().ToString('N').Substring(0,8)).ps1"
    
    $scriptContent = @"
# Auto-generated script to open browser after API starts
. '$browserHelpersFile'

# Wait for API to become available first
Write-Host 'Waiting for API to start...' -ForegroundColor Cyan
`$apiReady = Wait-ForUrl -Url '$apiHealthUrl' -TimeoutSeconds $TimeoutSeconds -IntervalMs 1000

if (`$apiReady) {
    Write-Host 'API is ready!' -ForegroundColor Green
} else {
    Write-Host 'Timeout waiting for API' -ForegroundColor Yellow
}

Write-Host 'Opening browser...' -ForegroundColor Green
Start-Sleep -Seconds 1
# Open both API docs and web GUI in same browser window
Open-Url '$apiUrl'
Start-Sleep -Seconds 2
Open-Url '$webUrl'

# Clean up this temp script
Remove-Item -Path '$tempScript' -Force -ErrorAction SilentlyContinue
"@
    
    Set-Content -Path $tempScript -Value $scriptContent -Encoding UTF8
    
    Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", $tempScript -WindowStyle Hidden
}
