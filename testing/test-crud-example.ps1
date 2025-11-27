# Test script for CRUD example endpoints (PowerShell)

$BASE_URL = "http://localhost:8000"

Write-Host "========================================" -ForegroundColor Blue
Write-Host "Testing CRUD Example Endpoints" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# Function to print test results
function Print-Result {
    param($success, $message)
    if ($success) {
        Write-Host "✓ $message" -ForegroundColor Green
    } else {
        Write-Host "✗ $message" -ForegroundColor Red
    }
}

# Note: Table is created automatically via migrations on startup
# No initialization endpoint needed!

# 1. Create example
Write-Host "1. Creating example..." -ForegroundColor Blue
$body = @{
    name = "Test Example"
    description = "This is a test"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "$BASE_URL/examples/" -Method Post -Body $body -ContentType "application/json"
Print-Result ($response.status -eq "success") "Create example"
$exampleId = $response.data.id
Write-Host "Created example with ID: $exampleId"
Write-Host ""

# 2. Get example by ID
Write-Host "2. Getting example by ID..." -ForegroundColor Blue
$response = Invoke-RestMethod -Uri "$BASE_URL/examples/$exampleId" -Method Get
Print-Result ($response.data.name -eq "Test Example") "Get example by ID"
Write-Host ""

# 3. List all examples
Write-Host "3. Listing all examples..." -ForegroundColor Blue
$response = Invoke-RestMethod -Uri "$BASE_URL/examples/" -Method Get
Print-Result ($response.data.Count -gt 0) "List examples"
Write-Host ""

# 4. Update example
Write-Host "4. Updating example..." -ForegroundColor Blue
$updateBody = @{
    name = "Updated Example"
    description = "Updated description"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "$BASE_URL/examples/$exampleId" -Method Put -Body $updateBody -ContentType "application/json"
Print-Result ($response.data.name -eq "Updated Example") "Update example"
Write-Host ""

# 5. Verify update
Write-Host "5. Verifying update..." -ForegroundColor Blue
$response = Invoke-RestMethod -Uri "$BASE_URL/examples/$exampleId" -Method Get
Print-Result ($response.data.name -eq "Updated Example") "Verify update"
Write-Host ""

# 6. Delete example
Write-Host "6. Deleting example..." -ForegroundColor Blue
$response = Invoke-RestMethod -Uri "$BASE_URL/examples/$exampleId" -Method Delete
Print-Result ($response.status -eq "success") "Delete example"
Write-Host ""

# 7. Verify deletion
Write-Host "7. Verifying deletion..." -ForegroundColor Blue
try {
    $response = Invoke-RestMethod -Uri "$BASE_URL/examples/$exampleId" -Method Get
    Print-Result $false "Verify deletion (should be deleted)"
} catch {
    Print-Result $true "Verify deletion"
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Blue
Write-Host "All tests completed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Blue
