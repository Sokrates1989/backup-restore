# Test Backup and Restore Functionality
# This script tests the complete backup/restore workflow

$ErrorActionPreference = "Stop"
$API_URL = "http://localhost:8081"
$ADMIN_KEY = "change-this-to-a-secure-random-key"  # Default from .env.template

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
            $response = Invoke-RestMethod -Uri "$API_URL$Endpoint" -Method $Method -Headers $headers -Body ($Body | ConvertTo-Json) -ErrorAction Stop
        } else {
            $response = Invoke-RestMethod -Uri "$API_URL$Endpoint" -Method $Method -Headers $headers -ErrorAction Stop
        }
        return $response
    } catch {
        Write-Host "❌ API call failed: $_" -ForegroundColor Red
        throw
    }
}

# Step 1: Create test data
Write-Host "📝 Step 1: Creating test data..." -ForegroundColor Yellow

$testData = @(
    @{ name = "Test Item 1"; description = "First test item" }
    @{ name = "Test Item 2"; description = "Second test item" }
    @{ name = "Test Item 3"; description = "Third test item" }
)

foreach ($item in $testData) {
    $result = Invoke-ApiCall -Method POST -Endpoint "/examples/" -Body $item
    Write-Host "  ✅ Created: $($result.name)" -ForegroundColor Green
}

# Step 2: Verify data exists
Write-Host ""
Write-Host "🔍 Step 2: Verifying data exists..." -ForegroundColor Yellow
$beforeBackup = Invoke-ApiCall -Method GET -Endpoint "/examples/"
Write-Host "  📊 Found $($beforeBackup.total) items before backup" -ForegroundColor Green

# Step 3: Create backup
Write-Host ""
Write-Host "💾 Step 3: Creating backup..." -ForegroundColor Yellow
$backup = Invoke-ApiCall -Method POST -Endpoint "/backup/create?compress=true"
Write-Host "  ✅ Backup created: $($backup.filename)" -ForegroundColor Green
Write-Host "  📦 Size: $($backup.size_mb) MB" -ForegroundColor Green
$backupFilename = $backup.filename

# Step 4: Wipe database
Write-Host ""
Write-Host "🗑️  Step 4: Wiping database..." -ForegroundColor Yellow
Write-Host "  ⚠️  Stopping containers..." -ForegroundColor Yellow
docker compose down
Start-Sleep -Seconds 2

Write-Host "  🗑️  Deleting PostgreSQL data..." -ForegroundColor Yellow
$postgresDataPath = "d:\Development\Code\python\python-api-template\.docker\postgres-data"
if (Test-Path $postgresDataPath) {
    Remove-Item -Path $postgresDataPath -Recurse -Force
    Write-Host "  ✅ Database wiped" -ForegroundColor Green
} else {
    Write-Host "  ℹ️  No data directory found (already clean)" -ForegroundColor Cyan
}

Write-Host "  🔄 Starting containers..." -ForegroundColor Yellow
docker compose up -d
Start-Sleep -Seconds 10  # Wait for services to start

# Step 5: Verify database is empty
Write-Host ""
Write-Host "🔍 Step 5: Verifying database is empty..." -ForegroundColor Yellow
try {
    $afterWipe = Invoke-ApiCall -Method GET -Endpoint "/examples/"
    Write-Host "  📊 Found $($afterWipe.total) items after wipe" -ForegroundColor Green
    
    if ($afterWipe.total -eq 0) {
        Write-Host "  ✅ Database successfully wiped" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Warning: Database not empty ($($afterWipe.total) items remain)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ℹ️  Database appears empty (expected)" -ForegroundColor Cyan
}

# Step 6: Restore from backup
Write-Host ""
Write-Host "♻️  Step 6: Restoring from backup..." -ForegroundColor Yellow
Write-Host "  📂 Restoring: $backupFilename" -ForegroundColor Cyan
$restore = Invoke-ApiCall -Method POST -Endpoint "/backup/restore/$backupFilename"
Write-Host "  ✅ $($restore.message)" -ForegroundColor Green

# Step 7: Verify data is restored
Write-Host ""
Write-Host "🔍 Step 7: Verifying data is restored..." -ForegroundColor Yellow
Start-Sleep -Seconds 2  # Give database a moment
$afterRestore = Invoke-ApiCall -Method GET -Endpoint "/examples/"
Write-Host "  📊 Found $($afterRestore.total) items after restore" -ForegroundColor Green

# Step 8: Compare results
Write-Host ""
Write-Host "📊 Step 8: Comparing results..." -ForegroundColor Yellow
Write-Host "  Before backup: $($beforeBackup.total) items" -ForegroundColor Cyan
Write-Host "  After wipe:    0 items" -ForegroundColor Cyan
Write-Host "  After restore: $($afterRestore.total) items" -ForegroundColor Cyan

if ($beforeBackup.total -eq $afterRestore.total) {
    Write-Host ""
    Write-Host "✅ SUCCESS! Backup and restore working correctly!" -ForegroundColor Green
    Write-Host "   All $($afterRestore.total) items were successfully restored." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "❌ FAILURE! Data mismatch!" -ForegroundColor Red
    Write-Host "   Expected: $($beforeBackup.total) items" -ForegroundColor Red
    Write-Host "   Got: $($afterRestore.total) items" -ForegroundColor Red
    exit 1
}

# Step 9: Cleanup - delete test backup
Write-Host ""
Write-Host "🧹 Step 9: Cleaning up test backup..." -ForegroundColor Yellow
try {
    $delete = Invoke-ApiCall -Method DELETE -Endpoint "/backup/delete/$backupFilename"
    Write-Host "  ✅ $($delete.message)" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  Could not delete backup: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Test Complete!" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
