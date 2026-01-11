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
    param(
        [Parameter(Mandatory=$true)]
        [string]$Url
    )

    try {
        # Detect Windows: $IsWindows only exists in PS Core 6+; fallback for Windows PowerShell 5.x
        $isWin = $false
        if ($null -ne $IsWindows) {
            $isWin = $IsWindows
        } elseif ($env:OS -match "Windows") {
            $isWin = $true
        }

        if ($isWin) {
            # Try Edge first (preinstalled on Windows)
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

function Get-ComposeServiceBlock {
    <#
    .SYNOPSIS
    Extracts the YAML block of a docker compose service by name.

    .PARAMETER ComposeFile
    Path to the docker-compose YAML file.

    .PARAMETER ServiceName
    The service key under `services:` (e.g. "phpmyadmin").

    .OUTPUTS
    System.String[]

    .NOTES
    This is a heuristic based on indentation; no YAML parser dependency.
    #>
    param(
        [string]$ComposeFile,
        [string]$ServiceName
    )

    if (-not (Test-Path $ComposeFile)) {
        return @()
    }

    $lines = Get-Content $ComposeFile
    $startPattern = "^\s{2}$([Regex]::Escape($ServiceName)):\s*$"
    $serviceStart = $null

    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $startPattern) {
            $serviceStart = $i + 1
            break
        }
    }

    if ($null -eq $serviceStart) {
        return @()
    }

    $block = @()
    for ($j = $serviceStart; $j -lt $lines.Count; $j++) {
        if ($lines[$j] -match "^\s{2}[A-Za-z0-9_-]+:\s*$") {
            break
        }
        $block += $lines[$j]
    }

    return $block
}

function Compose-HasService {
    <#
    .SYNOPSIS
    Checks whether a compose file contains a given service.

    .PARAMETER ComposeFile
    Path to the docker-compose YAML file.

    .PARAMETER ServiceName
    The service key under `services:`.

    .OUTPUTS
    System.Boolean
    #>
    param(
        [string]$ComposeFile,
        [string]$ServiceName
    )

    if (-not (Test-Path $ComposeFile)) {
        return $false
    }

    $content = Get-Content $ComposeFile -Raw
    return ($content -match "(?m)^\s{2}$([Regex]::Escape($ServiceName)):\s*$")
}

function Compose-ServiceHasPorts {
    <#
    .SYNOPSIS
    Checks whether a given service has a `ports:` section.

    .PARAMETER ComposeFile
    Path to the docker-compose YAML file.

    .PARAMETER ServiceName
    The service key under `services:`.

    .OUTPUTS
    System.Boolean

    .NOTES
    Used to decide whether a service is reachable via localhost.
    #>
    param(
        [string]$ComposeFile,
        [string]$ServiceName
    )

    $block = Get-ComposeServiceBlock -ComposeFile $ComposeFile -ServiceName $ServiceName
    if (-not $block -or $block.Count -eq 0) {
        return $false
    }

    return $null -ne ($block | Where-Object { $_ -match "^\s+ports:\s*$" } | Select-Object -First 1)
}

function Show-RelevantPagesDelayed {
    <#
    .SYNOPSIS
    Prints a short list of useful URLs and opens them when services become available.

    .PARAMETER ComposeFile
    Compose file used to determine which services are present.

    .PARAMETER TimeoutSeconds
    Maximum time to wait for services in seconds (default: 120).

    .NOTES
    Reads ports from `.env` via Get-EnvVariable (defined in docker_helpers.ps1).
    #>
    param(
        [string]$ComposeFile,
        [int]$TimeoutSeconds = 120
    )

    $apiPort = Get-EnvVariable -VariableName "API_PORT" -EnvFile ".env" -DefaultValue "8083"

    $apiUrl = "http://localhost:$apiPort/docs"
    $apiHealthUrl = "http://localhost:$apiPort/health"
    $webUrl = "http://localhost:$apiPort/"

    Write-Host "" 
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "  Services will be accessible at:" -ForegroundColor Yellow
    Write-Host "  - API Docs: $apiUrl" -ForegroundColor Gray
    Write-Host "  - Web GUI: $webUrl" -ForegroundColor Gray
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "" 
    Write-Host "Browser will open automatically when services are ready..." -ForegroundColor Yellow
    Write-Host ""

    # Wait for services and open browsers in background
    $scriptPath = $PSScriptRoot
    if (-not $scriptPath) {
        $scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
    }
    $browserHelpersFile = Join-Path $scriptPath "browser_helpers.ps1"
    
    # Build list of URLs to open
    $urlsToOpen = @($webUrl, $apiUrl)

    # Build Open-Url calls for each URL
    $openUrlCommands = ($urlsToOpen | ForEach-Object { "Open-Url '$_'" }) -join "`n    "
    
    # Write script to a temp file to avoid -EncodedCommand (flagged by some AV software)
    $tempScript = Join-Path $env:TEMP "backup_restore_browser_open_$([guid]::NewGuid().ToString('N').Substring(0,8)).ps1"
    $logFile = Join-Path $env:TEMP "backup_restore_browser_open.log"
    
    $scriptContent = @"
# Auto-generated script to open browser after services start
. `$ErrorActionPreference = 'Continue'
. '$browserHelpersFile'

`$logFile = '$logFile'
try {
    Add-Content -Path `$logFile -Value ("[{0}] Browser helper started. HealthUrl={1}" -f (Get-Date), '$apiHealthUrl') -Encoding UTF8
} catch {
}

# Wait for API to become available first
try {
    Write-Host 'Waiting for API to start...' -ForegroundColor Cyan
    Add-Content -Path `$logFile -Value ("[{0}] Waiting for API..." -f (Get-Date)) -Encoding UTF8
    `$apiReady = Wait-ForUrl -Url '$apiHealthUrl' -TimeoutSeconds $TimeoutSeconds -IntervalMs 1000
    Add-Content -Path `$logFile -Value ("[{0}] Wait finished. apiReady={1}" -f (Get-Date), `$apiReady) -Encoding UTF8
} catch {
    try { Add-Content -Path `$logFile -Value ("[{0}] ERROR in Wait-ForUrl: {1}" -f (Get-Date), `$_.Exception.Message) -Encoding UTF8 } catch {}
    `$apiReady = `$false
}

if (`$apiReady) {
    Write-Host 'API is ready!' -ForegroundColor Green
} else {
    Write-Host 'Timeout waiting for API' -ForegroundColor Yellow
}

try {
    Write-Host 'Opening browsers...' -ForegroundColor Green
    Add-Content -Path `$logFile -Value ("[{0}] Opening URLs..." -f (Get-Date)) -Encoding UTF8
    Start-Sleep -Seconds 1
    $openUrlCommands
    Add-Content -Path `$logFile -Value ("[{0}] Open-Url calls done." -f (Get-Date)) -Encoding UTF8
} catch {
    try { Add-Content -Path `$logFile -Value ("[{0}] ERROR opening URLs: {1}" -f (Get-Date), `$_.Exception.Message) -Encoding UTF8 } catch {}
}

# Clean up this temp script
Remove-Item -Path '$tempScript' -Force -ErrorAction SilentlyContinue
"@
    
    Set-Content -Path $tempScript -Value $scriptContent -Encoding UTF8
    
    # Execute the temp script file (safer than -EncodedCommand for AV software)
    $psExe = $null
    try {
        $psExe = (Get-Command powershell -ErrorAction SilentlyContinue).Source
        if (-not $psExe) {
            $psExe = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
        }
    } catch {
        $psExe = $null
    }
    if (-not $psExe) {
        $psExe = "powershell"
    }

    Write-Host "[WEB] Browser helper started (log: $logFile)" -ForegroundColor Gray
    Start-Process -FilePath $psExe -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-WindowStyle",
        "Hidden",
        "-File",
        $tempScript
    ) -WindowStyle Hidden
}
