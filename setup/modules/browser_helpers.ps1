<#
browser_helpers.ps1

Purpose:
- Helper utilities for backup-restore quick-start script.
- Opens URLs in incognito/private browser mode with auto-close on restart.

Notes:
- Best-effort only: should not break quick-start execution.
#>

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

$script:IncognitoProfileCleaned = $false

function Open-Url {
    <#
    .SYNOPSIS
    Opens a URL in an incognito/private browser window with backup-restore-specific profile.

    .PARAMETER Url
    URL to open.
    #>
    param([string]$Url)

    try {
        $isWin = $false
        if ($null -ne $IsWindows) {
            $isWin = $IsWindows
        } elseif ($env:OS -match "Windows") {
            $isWin = $true
        }

        if ($isWin) {
            # Try Edge first
            $edgePaths = @(
                "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
                "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
            )
            foreach ($edgePath in $edgePaths) {
                if (Test-Path $edgePath) {
                    $profileDir = Join-Path $env:TEMP "edge_incog_profile_backup-restore"
                    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
                    if (-not $script:IncognitoProfileCleaned) {
                        Stop-IncognitoProfileProcesses -ProfileDir $profileDir -ProcessNames @("msedge.exe")
                        $script:IncognitoProfileCleaned = $true
                    }
                    Start-Process -FilePath $edgePath -ArgumentList "-inprivate", "--user-data-dir=$profileDir", $Url
                    return
                }
            }

            # Then Chrome
            $chromePaths = @(
                "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
                "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
                "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
            )
            foreach ($chromePath in $chromePaths) {
                if (Test-Path $chromePath) {
                    $profileDir = Join-Path $env:TEMP "chrome_incog_profile_backup-restore"
                    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
                    if (-not $script:IncognitoProfileCleaned) {
                        Stop-IncognitoProfileProcesses -ProfileDir $profileDir -ProcessNames @("chrome.exe")
                        $script:IncognitoProfileCleaned = $true
                    }
                    Start-Process -FilePath $chromePath -ArgumentList "--incognito", "--user-data-dir=$profileDir", $Url
                    return
                }
            }

            # Firefox (no custom profile needed)
            $firefoxPaths = @(
                "$env:ProgramFiles\Mozilla Firefox\firefox.exe",
                "${env:ProgramFiles(x86)}\Mozilla Firefox\firefox.exe"
            )
            foreach ($firefoxPath in $firefoxPaths) {
                if (Test-Path $firefoxPath) {
                    Start-Process -FilePath $firefoxPath -ArgumentList "-private-window", $Url
                    return
                }
            }

            # Fallback: default browser
            Start-Process $Url | Out-Null
            return
        }

        # macOS
        if ($IsMacOS) {
            if (Test-Path "/Applications/Google Chrome.app") {
                & open -na "Google Chrome" --args --incognito $Url 2>$null
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

    Write-Host "" 
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "  API will be accessible at:" -ForegroundColor Yellow
    Write-Host "  - API Docs: $apiUrl" -ForegroundColor Gray
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
Open-Url '$apiUrl'

# Clean up this temp script
Remove-Item -Path '$tempScript' -Force -ErrorAction SilentlyContinue
"@
    
    Set-Content -Path $tempScript -Value $scriptContent -Encoding UTF8
    
    Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", $tempScript -WindowStyle Hidden
}
