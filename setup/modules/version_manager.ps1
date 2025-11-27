# version_manager.ps1
# PowerShell module for managing Docker image versions and semantic versioning

function Bump-SemVer {
    param(
        [string]$Version,
        [ValidateSet('patch','minor','major')]
        [string]$Level
    )

    if ([string]::IsNullOrWhiteSpace($Version)) {
        $Version = '0.0.0'
    }

    $prefix = ''
    if ($Version.StartsWith('v') -or $Version.StartsWith('V')) {
        $prefix = $Version.Substring(0,1)
        $Version = $Version.Substring(1)
    }

    $parts = $Version.Split('.')
    if ($parts.Count -lt 3) {
        $parts = @($parts + @('0','0','0'))[0..2]
    }

    try {
        $major = [int]$parts[0]
        $minor = [int]$parts[1]
        $patch = [int]$parts[2]
    } catch {
        return $null
    }

    switch ($Level) {
        'patch' { $patch += 1 }
        'minor' { $minor += 1; $patch = 0 }
        'major' { $major += 1; $minor = 0; $patch = 0 }
    }

    return "$prefix$major.$minor.$patch"
}

function Update-ImageVersionInFile {
    param(
        [string]$Path,
        [string]$NewVersion
    )

    if (-not (Test-Path $Path)) {
        Write-Host "[WARN] $Path not found - skipping." -ForegroundColor Yellow
        return
    }

    $lines = Get-Content $Path
    $replaced = $false
    $updatedLines = foreach ($line in $lines) {
        if (-not $replaced -and $line -match '^IMAGE_VERSION=') {
            $replaced = $true
            "IMAGE_VERSION=$NewVersion"
        } else {
            $line
        }
    }

    if (-not $replaced) {
        $updatedLines += "IMAGE_VERSION=$NewVersion"
    }

    Set-Content -Path $Path -Value $updatedLines
    Write-Host "[OK] $Path -> IMAGE_VERSION=$NewVersion" -ForegroundColor Green
}

function Get-RemoteImageState {
    param([string]$ImageRef)

    if ([string]::IsNullOrWhiteSpace($ImageRef)) {
        return [pscustomobject]@{ State = 'unknown'; Detail = $null }
    }

    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        return [pscustomobject]@{ State = 'skipped'; Detail = 'Docker CLI not available' }
    }

    $previousEA = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    $output = & docker manifest inspect $ImageRef 2>&1
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousEA
    $combined = ($output | Out-String).Trim()

    if ($exitCode -eq 0) {
        return [pscustomobject]@{ State = 'present'; Detail = $null }
    }

    if ($combined -match '(?i)(not found|no such manifest)') {
        return [pscustomobject]@{ State = 'missing'; Detail = $null }
    }

    if ($combined -match '(?i)(denied|unauthorized)') {
        return [pscustomobject]@{ State = 'unauthorized'; Detail = $null }
    }

    $firstLine = ($combined -split "`r?`n")[0]
    return [pscustomobject]@{ State = 'error'; Detail = $firstLine }
}

function Get-StateLabel {
    param(
        [string]$Prefix,
        [string]$State,
        [string]$Detail
    )

    switch ($State) {
        'present'      { return ("{0}: available" -f $Prefix) }
        'missing'      { return ("{0}: missing" -f $Prefix) }
        'unauthorized' { return ("{0}: access denied" -f $Prefix) }
        'error' {
            if ($Detail) { return ("{0}: error - {1}" -f $Prefix, $Detail) }
            return ("{0}: error" -f $Prefix)
        }
        'skipped' {
            if ($Detail) { return ("{0}: not checked ({1})" -f $Prefix, $Detail) }
            return ("{0}: not checked" -f $Prefix)
        }
        'unknown'      { return ("{0}: unknown" -f $Prefix) }
        Default        { return ("{0}: unknown" -f $Prefix) }
    }
}

function Build-VersionAnnotation {
    param(
        [string]$ImageName,
        [string]$Version
    )

    if ([string]::IsNullOrWhiteSpace($ImageName)) {
        return " (Remote: not checked - IMAGE_NAME missing)"
    }

    if ([string]::IsNullOrWhiteSpace($Version)) {
        return " (Remote: not checked - version missing)"
    }

    $imageRef = "{0}:{1}" -f $ImageName, $Version
    $remote = Get-RemoteImageState -ImageRef $imageRef
    return " (" + (Get-StateLabel -Prefix 'Remote' -State $remote.State -Detail $remote.Detail) + ')'
}

function Test-RemoteImage {
    param(
        [string]$ImageRef,
        [string]$Context
    )

    if ([string]::IsNullOrWhiteSpace($ImageRef)) {
        return
    }

    $result = Get-RemoteImageState -ImageRef $ImageRef

    switch ($result.State) {
        'present' {
            $message = if ($Context) { "[OK] {0}: {1} is available on the registry." -f $Context, $ImageRef } else { "[OK] Remote image found: {0}" -f $ImageRef }
            Write-Host $message -ForegroundColor Green
        }
        'missing' {
            $message = if ($Context) { "[INFO] {0}: {1} was not found on the registry." -f $Context, $ImageRef } else { "[INFO] Remote image not found: {0}" -f $ImageRef }
            Write-Host $message -ForegroundColor Yellow
        }
        'unauthorized' {
            Write-Host ("[WARN] {0}: access denied for {1}. Please log in to the registry." -f $Context, $ImageRef) -ForegroundColor Yellow
        }
        'skipped' {
            $detail = $result.Detail
            if ($Context) {
                if ($detail) {
                    Write-Host ("[WARN] {0}: remote check skipped ({1})." -f $Context, $detail) -ForegroundColor Yellow
                } else {
                    Write-Host ("[WARN] {0}: remote check skipped." -f $Context) -ForegroundColor Yellow
                }
            } else {
                if ($detail) {
                    Write-Host ("[WARN] Remote check skipped ({0})." -f $detail) -ForegroundColor Yellow
                } else {
                    Write-Host "[WARN] Remote check skipped." -ForegroundColor Yellow
                }
            }
        }
        'error' {
            $detail = if ($result.Detail) { $result.Detail } else { 'unknown error' }
            if ($Context) {
                Write-Host ("[WARN] {0}: error while checking {1}: {2}" -f $Context, $ImageRef, $detail) -ForegroundColor Yellow
            } else {
                Write-Host ("[WARN] Error while checking {0}: {1}" -f $ImageRef, $detail) -ForegroundColor Yellow
            }
        }
        Default {
            if ($Context) {
                Write-Host ("[WARN] {0}: unknown state for {1}." -f $Context, $ImageRef) -ForegroundColor Yellow
            } else {
                Write-Host ("[WARN] Unknown state for {0}." -f $ImageRef) -ForegroundColor Yellow
            }
        }
    }
}

function Update-ImageVersion {
    $envFile = '.env'
    $ciEnvFile = '.ci.env'

    $currentEnvVersion = $null
    if (Test-Path $envFile) {
        $envLine = Get-Content $envFile | Where-Object { $_ -match '^IMAGE_VERSION=' } | Select-Object -First 1
        if ($envLine) {
            $currentEnvVersion = ($envLine -split '=', 2)[1].Trim().Trim('"')
        }
    }

    $currentCiVersion = $null
    if (Test-Path $ciEnvFile) {
        $ciLine = Get-Content $ciEnvFile | Where-Object { $_ -match '^IMAGE_VERSION=' } | Select-Object -First 1
        if ($ciLine) {
            $currentCiVersion = ($ciLine -split '=', 2)[1].Trim().Trim('"')
        }
    }

    $baseVersion = if (-not [string]::IsNullOrWhiteSpace($currentEnvVersion)) { $currentEnvVersion }
                  elseif (-not [string]::IsNullOrWhiteSpace($currentCiVersion)) { $currentCiVersion }
                  else { '0.1.0' }

    $imageName = $null
    if (Test-Path $envFile) {
        $nameLine = Get-Content $envFile | Where-Object { $_ -match '^IMAGE_NAME=' } | Select-Object -First 1
        if ($nameLine) {
            $imageName = ($nameLine -split '=', 2)[1].Trim().Trim('"')
        }
    }

    $displayEnv = if ($currentEnvVersion) { $currentEnvVersion } else { '<not set>' }
    $displayCi = if ($currentCiVersion) { $currentCiVersion } else { '<not set>' }

    Write-Host ''
    Write-Host 'Current IMAGE_VERSION values:' -ForegroundColor Cyan
    Write-Host ("  - .env    : {0}{1}" -f $displayEnv, (Build-VersionAnnotation -ImageName $imageName -Version $currentEnvVersion)) -ForegroundColor Gray
    Write-Host ("  - .ci.env : {0}{1}" -f $displayCi, (Build-VersionAnnotation -ImageName $imageName -Version $currentCiVersion)) -ForegroundColor Gray
    Write-Host ''

    if ($imageName -and $baseVersion) {
        $currentImageRef = "{0}:{1}" -f $imageName, $baseVersion
        Test-RemoteImage -ImageRef $currentImageRef -Context 'Current version on registry'
        Write-Host ''
    } elseif (-not $imageName) {
        Write-Host '[WARN] IMAGE_NAME not set - skipping remote check.' -ForegroundColor Yellow
        Write-Host ''
    }

    Write-Host 'How would you like to update the version?' -ForegroundColor Yellow
    Write-Host '  1) Bugfix/Patch (+0.0.1)' -ForegroundColor Gray
    Write-Host '  2) Feature/Minor (+0.1.0)' -ForegroundColor Gray
    Write-Host '  3) Breaking/Major (+1.0.0)' -ForegroundColor Gray
    Write-Host '  or enter a new version directly (e.g. 1.2.3)' -ForegroundColor Gray

    $newVersion = $null
    while ($true) {
        $choice = (Read-Host 'Your choice (1-3 or SemVer)').Trim()

        switch ($choice) {
            '1' { $newVersion = Bump-SemVer -Version $baseVersion -Level 'patch' }
            '2' { $newVersion = Bump-SemVer -Version $baseVersion -Level 'minor' }
            '3' { $newVersion = Bump-SemVer -Version $baseVersion -Level 'major' }
            '' {
                Write-Host 'Please choose an option or enter a SemVer value.' -ForegroundColor Red
                continue
            }
            Default {
                if ($choice -match '^[vV]?[0-9]+\.[0-9]+\.[0-9]+$') {
                    $newVersion = $choice
                } else {
                    Write-Host 'Invalid input. Enter 1-3 or a SemVer (e.g. 1.2.3).' -ForegroundColor Red
                    continue
                }
            }
        }

        if (-not [string]::IsNullOrWhiteSpace($newVersion)) {
            if ($imageName) {
                $candidateRef = "{0}:{1}" -f $imageName, $newVersion
                $existingTag = Get-RemoteImageState -ImageRef $candidateRef
                if ($existingTag -and $existingTag.State -eq 'present') {
                    Write-Host ("The tag {0} already exists on the registry. Please choose another version." -f $candidateRef) -ForegroundColor Red
                    $newVersion = $null
                    continue
                }
            }
            break
        }
    }

    if ([string]::IsNullOrWhiteSpace($newVersion)) {
        Write-Host 'Could not determine new version. Please try again.' -ForegroundColor Red
        return
    }

    if ($imageName) {
        Write-Host ''
        $selectedImageRef = "{0}:{1}" -f $imageName, $newVersion
        Test-RemoteImage -ImageRef $selectedImageRef -Context 'Selected version on registry'
    }

    Write-Host ''
    Update-ImageVersionInFile -Path $envFile -NewVersion $newVersion
    Update-ImageVersionInFile -Path $ciEnvFile -NewVersion $newVersion
    Write-Host ''
    Write-Host ("IMAGE_VERSION updated to {0}" -f $newVersion) -ForegroundColor Green
}
