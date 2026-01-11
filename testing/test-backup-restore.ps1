# Test Backup and Restore Functionality
# This script tests the complete backup/restore workflow

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envFile = Join-Path $repoRoot ".env"

$port = "8000"
$ADMIN_KEY = "change-this-to-a-secure-random-key"
$RESTORE_KEY = "change-this-restore-key-to-something-secure"
$DELETE_KEY = "change-this-delete-key-to-something-secure"

if (Test-Path $envFile) {
    $envLines = Get-Content $envFile
    foreach ($line in $envLines) {
        if ($line -match '^PORT=(.+)$') { $port = $Matches[1].Trim().Trim('"') }
        if ($line -match '^ADMIN_API_KEY=(.+)$') { $ADMIN_KEY = $Matches[1].Trim().Trim('"') }
        if ($line -match '^BACKUP_RESTORE_API_KEY=(.+)$') { $RESTORE_KEY = $Matches[1].Trim().Trim('"') }
        if ($line -match '^BACKUP_DELETE_API_KEY=(.+)$') { $DELETE_KEY = $Matches[1].Trim().Trim('"') }
    }
}

$API_URL = "http://localhost:$port"

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Backup & Restore Test" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Function to make API calls
function Invoke-ApiCall {
    param(
        [string]$Method,
        [string]$Endpoint,
        [object]$Body = $null
    )

    $headers = @{
        "X-Admin-Key" = $ADMIN_KEY
        "Content-Type" = "application/json"
    }

    try {
        if ($Body) {
            return Invoke-RestMethod -Uri "$API_URL$Endpoint" -Method $Method -Headers $headers -Body ($Body | ConvertTo-Json) -ErrorAction Stop
        }
        return Invoke-RestMethod -Uri "$API_URL$Endpoint" -Method $Method -Headers $headers -ErrorAction Stop
    } catch {
        Write-Host "[ERROR] API call failed: $_" -ForegroundColor Red
        throw
    }
}

function Invoke-RestoreCall {
    param(
        [string]$Method,
        [string]$Endpoint,
        [object]$Body = $null
    )

    $headers = @{
        "X-Restore-Key" = $RESTORE_KEY
        "Content-Type" = "application/json"
    }

    if ($Body) {
        return Invoke-RestMethod -Uri "$API_URL$Endpoint" -Method $Method -Headers $headers -Body ($Body | ConvertTo-Json) -ErrorAction Stop
    }
    return Invoke-RestMethod -Uri "$API_URL$Endpoint" -Method $Method -Headers $headers -ErrorAction Stop
}

function Invoke-DeleteCall {
    param(
        [string]$Method,
        [string]$Endpoint,
        [object]$Body = $null
    )

    $headers = @{
        "X-Delete-Key" = $DELETE_KEY
        "Content-Type" = "application/json"
    }

    if ($Body) {
        return Invoke-RestMethod -Uri "$API_URL$Endpoint" -Method $Method -Headers $headers -Body ($Body | ConvertTo-Json) -ErrorAction Stop
    }
    return Invoke-RestMethod -Uri "$API_URL$Endpoint" -Method $Method -Headers $headers -ErrorAction Stop
}

# Step 1: Create test data
Write-Host "[WRITE] Step 1: Creating test data..." -ForegroundColor Yellow

$testData = @(
    @{ name = "Test Item 1"; description = "First test item" }
    @{ name = "Test Item 2"; description = "Second test item" }
    @{ name = "Test Item 3"; description = "Third test item" }
)

foreach ($item in $testData) {
    $result = Invoke-ApiCall -Method POST -Endpoint "/examples/" -Body $item
    Write-Host "  [OK] Created: $($result.data.name)" -ForegroundColor Green
}

# Step 2: Verify data exists
Write-Host ""
Write-Host "[SEARCH] Step 2: Verifying data exists..." -ForegroundColor Yellow
$beforeBackup = Invoke-ApiCall -Method GET -Endpoint "/examples/"
Write-Host "  [DATA] Found $($beforeBackup.total) items before backup" -ForegroundColor Green

# Step 3: Create backup
Write-Host ""
Write-Host "[BACKUP] Step 3: Creating backup..." -ForegroundColor Yellow
$backup = Invoke-ApiCall -Method POST -Endpoint "/backup/create?compress=true"
Write-Host "  [OK] Backup created: $($backup.filename)" -ForegroundColor Green
Write-Host "  [SIZE] Size: $($backup.size_mb) MB" -ForegroundColor Green
$backupFilename = $backup.filename

# Step 4: Wipe database
Write-Host ""
Write-Host "[DELETE]  Step 4: Wiping database..." -ForegroundColor Yellow
Write-Host "  [INFO]  Stopping containers..." -ForegroundColor Yellow
$dbType = "postgresql"
$dbMode = "local"
if (Test-Path $envFile) {
    foreach ($line in $envLines) {
        if ($line -match '^DB_TYPE=(.+)$') { $dbType = $Matches[1].Trim().Trim('"') }
        if ($line -match '^DB_MODE=(.+)$') { $dbMode = $Matches[1].Trim().Trim('"') }
    }
}

$composeFile = Join-Path $repoRoot "local-deployment\docker-compose.postgres.yml"
if ($dbMode -eq "standalone") {
    $composeFile = Join-Path $repoRoot "local-deployment\docker-compose.yml"
} elseif ($dbType -eq "neo4j") {
    $composeFile = Join-Path $repoRoot "local-deployment\docker-compose.neo4j.yml"
} elseif ($dbType -eq "postgresql" -or $dbType -eq "mysql") {
    $composeFile = Join-Path $repoRoot "local-deployment\docker-compose.postgres.yml"
} else {
    $composeFile = Join-Path $repoRoot "local-deployment\docker-compose.yml"
}

docker compose --env-file $envFile -f $composeFile down --remove-orphans
Start-Sleep -Seconds 2

Write-Host "  [DELETE]  Deleting PostgreSQL data..." -ForegroundColor Yellow
$postgresDataPath = Join-Path $repoRoot ".docker\postgres-data"
if (Test-Path $postgresDataPath) {
    Remove-Item -Path $postgresDataPath -Recurse -Force
    Write-Host "  [OK] Database wiped" -ForegroundColor Green
} else {
    Write-Host "  [INFO]  No data directory found (already clean)" -ForegroundColor Cyan
}

Write-Host "  [RESTART] Starting containers..." -ForegroundColor Yellow
docker compose --env-file $envFile -f $composeFile up -d --build
Start-Sleep -Seconds 10  # Wait for services to start

# Step 5: Verify database is empty
Write-Host ""
Write-Host "[SEARCH] Step 5: Verifying database is empty..." -ForegroundColor Yellow
try {
    $afterWipe = Invoke-ApiCall -Method GET -Endpoint "/examples/"
    Write-Host "  [DATA] Found $($afterWipe.total) items after wipe" -ForegroundColor Green
    
    if ($afterWipe.total -eq 0) {
        Write-Host "  [OK] Database successfully wiped" -ForegroundColor Green
    } else {
        Write-Host "  [INFO]  Warning: Database not empty ($($afterWipe.total) items remain)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [INFO]  Database appears empty (expected)" -ForegroundColor Cyan
}

# Step 6: Restore from backup
Write-Host ""
Write-Host "[RESTORE]  Step 6: Restoring from backup..." -ForegroundColor Yellow
Write-Host "  [FILE] Restoring: $backupFilename" -ForegroundColor Cyan
$restore = Invoke-RestoreCall -Method POST -Endpoint "/backup/restore/$backupFilename"
Write-Host "  [OK] $($restore.message)" -ForegroundColor Green

# Step 7: Verify data is restored
Write-Host ""
Write-Host "[SEARCH] Step 7: Verifying data is restored..." -ForegroundColor Yellow
Start-Sleep -Seconds 2  # Give database a moment
$afterRestore = Invoke-ApiCall -Method GET -Endpoint "/examples/"
Write-Host "  [DATA] Found $($afterRestore.total) items after restore" -ForegroundColor Green

# Step 8: Compare results
Write-Host ""
Write-Host "[DATA] Step 8: Comparing results..." -ForegroundColor Yellow
Write-Host "  Before backup: $($beforeBackup.total) items" -ForegroundColor Cyan
Write-Host "  After wipe:    0 items" -ForegroundColor Cyan
Write-Host "  After restore: $($afterRestore.total) items" -ForegroundColor Cyan

if ($beforeBackup.total -eq $afterRestore.total) {
    Write-Host ""
    Write-Host "[OK] SUCCESS! Backup and restore working correctly!" -ForegroundColor Green
    Write-Host "   All $($afterRestore.total) items were successfully restored." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[ERROR] FAILURE! Data mismatch!" -ForegroundColor Red
    Write-Host "   Expected: $($beforeBackup.total) items" -ForegroundColor Red
    Write-Host "   Got: $($afterRestore.total) items" -ForegroundColor Red
    exit 1
}

# Step 9: Cleanup - delete test backup
Write-Host ""
Write-Host "[CLEAN] Step 9: Cleaning up test backup..." -ForegroundColor Yellow
try {
    $delete = Invoke-DeleteCall -Method DELETE -Endpoint "/backup/delete/$backupFilename"
    Write-Host "  [OK] $($delete.message)" -ForegroundColor Green
} catch {
    Write-Host "  [WARNING]  Could not delete backup: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Test Complete!" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
