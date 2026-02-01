<#
menu_keycloak.ps1

Module for Keycloak-related menu actions.
#>

function Get-KeycloakAccessToken {
    <#
    .SYNOPSIS
    Retrieves a Keycloak access token for CLI operations.

    .DESCRIPTION
    Uses environment variables or .env file values to request a service-account token.
    Falls back to prompting for a token if automatic retrieval is not possible.

    .PARAMETER EnvFile
    Path to the environment file to read KEYCLOAK_* variables from.

    .OUTPUTS
    System.String
    Access token string.
    #>
    param(
        [string]$EnvFile = ".env"
    )

    $accessToken = $env:ACCESS_TOKEN
    if ($accessToken) {
        return $accessToken
    }

    $keycloakUrl = Get-EnvVariable -VariableName "KEYCLOAK_URL" -EnvFile $EnvFile -DefaultValue ""
    $keycloakInternalUrl = Get-EnvVariable -VariableName "KEYCLOAK_INTERNAL_URL" -EnvFile $EnvFile -DefaultValue ""
    $keycloakRealm = Get-EnvVariable -VariableName "KEYCLOAK_REALM" -EnvFile $EnvFile -DefaultValue ""
    $keycloakClientId = Get-EnvVariable -VariableName "KEYCLOAK_CLIENT_ID" -EnvFile $EnvFile -DefaultValue ""
    $keycloakClientSecret = Get-EnvVariable -VariableName "KEYCLOAK_CLIENT_SECRET" -EnvFile $EnvFile -DefaultValue ""

    if ($keycloakInternalUrl) {
        $keycloakUrl = $keycloakInternalUrl
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

function Invoke-KeycloakBootstrap {
    <#
    .SYNOPSIS
    Bootstrap Keycloak realm with clients, roles, and users.

    .DESCRIPTION
    Creates a new realm in Keycloak with frontend/backend clients,
    granular backup roles, and optional default users.

    .OUTPUTS
    System.Int32
    Exit code (0 for success, non-zero for failure).
    #>

    $projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
    $scriptsDir = Join-Path $projectRoot "scripts"
    $bootstrapImage = "backup-restore-keycloak-bootstrap"
    
    Write-Host ""
    Write-Host "Keycloak Bootstrap" -ForegroundColor Cyan
    Write-Host ""
    
    # Load .env defaults
    $keycloakUrl = Get-EnvVariable -VariableName "KEYCLOAK_URL" -EnvFile "$projectRoot\.env" -DefaultValue "http://localhost:9090"
    $keycloakRealm = Get-EnvVariable -VariableName "KEYCLOAK_REALM" -EnvFile "$projectRoot\.env" -DefaultValue "backup-restore"
    
    # Check if Keycloak is reachable
    Write-Host "Checking Keycloak at $keycloakUrl..." -ForegroundColor Gray
    try {
        $null = Invoke-WebRequest -Uri "$keycloakUrl/" -Method Get -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        Write-Host "Keycloak is reachable" -ForegroundColor Green
    } catch {
        Write-Host ""
        Write-Host "Cannot reach Keycloak at $keycloakUrl" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please ensure Keycloak is running. Start it from the dedicated repo:" -ForegroundColor Gray
        Write-Host "  https://github.com/Sokrates1989/keycloak.git" -ForegroundColor Gray
        Write-Host ""
        return 1
    }
    Write-Host ""
    
    # Check if bootstrap image exists, build if not
    $bootstrapImageId = docker image ls -q $bootstrapImage
    if ([string]::IsNullOrWhiteSpace($bootstrapImageId)) {
        Write-Host "Building bootstrap image..." -ForegroundColor Cyan
        docker build -t $bootstrapImage $scriptsDir
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to build bootstrap image" -ForegroundColor Red
            return 1
        }
    }
    
    # Collect configuration
    $inputUrl = Read-Host "Keycloak base URL [$keycloakUrl]"
    if ($inputUrl) { $keycloakUrl = $inputUrl }
    
    $adminUser = Read-Host "Keycloak admin username [admin]"
    if (-not $adminUser) { $adminUser = "admin" }
    
    $adminPassword = Read-Host "Keycloak admin password [admin]"
    if (-not $adminPassword) { $adminPassword = "admin" }
    
    $realm = Read-Host "Realm name [$keycloakRealm]"
    if (-not $realm) { $realm = $keycloakRealm }
    
    $frontendClient = Read-Host "Frontend client ID [backup-restore-frontend]"
    if (-not $frontendClient) { $frontendClient = "backup-restore-frontend" }
    
    $backendClient = Read-Host "Backend client ID [backup-restore-backend]"
    if (-not $backendClient) { $backendClient = "backup-restore-backend" }
    
    $webPort = Get-EnvVariable -VariableName "WEB_PORT" -EnvFile "$projectRoot\.env" -DefaultValue "8086"
    $frontendUrl = Read-Host "Frontend root URL [http://localhost:$webPort]"
    if (-not $frontendUrl) { $frontendUrl = "http://localhost:$webPort" }
    
    $apiPort = Get-EnvVariable -VariableName "PORT" -EnvFile "$projectRoot\.env" -DefaultValue "8000"
    $apiUrl = Read-Host "API root URL [http://localhost:$apiPort]"
    if (-not $apiUrl) { $apiUrl = "http://localhost:$apiPort" }
    
    Write-Host ""
    Write-Host "Creating granular roles:" -ForegroundColor Green
    Write-Host "   - backup:read      (view backups, stats)" -ForegroundColor Gray
    Write-Host "   - backup:create    (manual backup runs)" -ForegroundColor Gray
    Write-Host "   - backup:run       (run scheduled/manual backups)" -ForegroundColor Gray
    Write-Host "   - backup:configure (configure targets/destinations/schedules)" -ForegroundColor Gray
    Write-Host "   - backup:restore   (restore backups - CRITICAL)" -ForegroundColor Gray
    Write-Host "   - backup:delete    (delete backups)" -ForegroundColor Gray
    Write-Host "   - backup:download  (download backup files)" -ForegroundColor Gray
    Write-Host "   - backup:history   (view audit history)" -ForegroundColor Gray
    Write-Host "   - backup:admin     (full access)" -ForegroundColor Gray
    Write-Host ""
    
    $useDefaults = Read-Host "Create default users (admin/operator/viewer)? (Y/n)"
    $userArgs = @()
    if ($useDefaults -notmatch "^[Nn]$") {
        $userArgs = @(
            "--user", "admin:admin:backup:admin",
            "--user", "operator:operator:backup:read,backup:create,backup:run,backup:restore,backup:download,backup:history",
            "--user", "viewer:viewer:backup:read"
        )
    } else {
        Write-Host "Role format: backup:read, backup:create, backup:run, backup:configure, backup:restore, backup:delete, backup:download, backup:history, backup:admin" -ForegroundColor Gray
        $customUser = Read-Host "Enter user spec (username:password:role1,role2)"
        if ($customUser) {
            $userArgs = @("--user", $customUser)
        }
    }
    
    if ($userArgs.Count -eq 0) {
        Write-Host "No users specified. Aborting bootstrap." -ForegroundColor Red
        return 1
    }
    
    Write-Host ""
    Write-Host "Bootstrapping Keycloak realm..." -ForegroundColor Cyan
    
    $dockerArgs = @(
        "--base-url", $keycloakUrl,
        "--admin-user", $adminUser,
        "--admin-password", $adminPassword,
        "--realm", $realm,
        "--frontend-client-id", $frontendClient,
        "--backend-client-id", $backendClient,
        "--frontend-root-url", $frontendUrl,
        "--api-root-url", $apiUrl
    ) + $userArgs
    
    docker run --rm --network host $bootstrapImage $dockerArgs
    
    $exitCode = $LASTEXITCODE
    
    Write-Host ""
    if ($exitCode -eq 0) {
        Write-Host "Bootstrap complete! Update your .env with the client secret from output above." -ForegroundColor Green
    } else {
        Write-Host "Bootstrap failed. Check Keycloak logs for details." -ForegroundColor Red
    }
    
    return $exitCode
}
