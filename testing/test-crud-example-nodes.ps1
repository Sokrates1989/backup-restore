# Test script for Neo4j ExampleNode CRUD operations
# This script demonstrates all CRUD operations for the example-nodes endpoints

$API_URL = "http://localhost:8081"
$ENDPOINT = "$API_URL/example-nodes"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Testing Neo4j ExampleNode CRUD Operations" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Create first node
Write-Host "Step 1: Creating first ExampleNode..." -ForegroundColor Yellow
$node1 = Invoke-RestMethod -Uri "$ENDPOINT/" -Method Post -ContentType "application/json" -Body '{"name": "Test Node 1", "description": "First test node"}'
$node1Id = $node1.data.id
Write-Host "✅ Created node with ID: $node1Id" -ForegroundColor Green
Write-Host ""

# Step 2: Create second node
Write-Host "Step 2: Creating second ExampleNode..." -ForegroundColor Yellow
$node2 = Invoke-RestMethod -Uri "$ENDPOINT/" -Method Post -ContentType "application/json" -Body '{"name": "Test Node 2", "description": "Second test node"}'
$node2Id = $node2.data.id
Write-Host "✅ Created node with ID: $node2Id" -ForegroundColor Green
Write-Host ""

# Step 3: List all nodes
Write-Host "Step 3: Listing all ExampleNodes..." -ForegroundColor Yellow
$nodeList = Invoke-RestMethod -Uri "$ENDPOINT/"
Write-Host "✅ Found $($nodeList.data.total) node(s)" -ForegroundColor Green
$nodeList.data.items | ForEach-Object {
    Write-Host "  - $($_.name): $($_.description)" -ForegroundColor Gray
}
Write-Host ""

# Step 4: Get specific node
Write-Host "Step 4: Getting specific ExampleNode..." -ForegroundColor Yellow
$specificNode = Invoke-RestMethod -Uri "$ENDPOINT/$node1Id"
Write-Host "✅ Retrieved: $($specificNode.data.name)" -ForegroundColor Green
Write-Host ""

# Step 5: Update node
Write-Host "Step 5: Updating ExampleNode..." -ForegroundColor Yellow
$updated = Invoke-RestMethod -Uri "$ENDPOINT/$node1Id" -Method Put -ContentType "application/json" -Body '{"name": "Updated Node 1", "description": "This node has been updated"}'
Write-Host "✅ Updated: $($updated.data.name)" -ForegroundColor Green
Write-Host "   Description: $($updated.data.description)" -ForegroundColor Gray
Write-Host ""

# Step 6: Filter by name
Write-Host "Step 6: Filtering nodes by name..." -ForegroundColor Yellow
$filtered = Invoke-RestMethod -Uri "$ENDPOINT/?name=Updated"
Write-Host "✅ Found $($filtered.data.total) node(s) matching 'Updated'" -ForegroundColor Green
Write-Host ""

# Step 7: Delete one node
Write-Host "Step 7: Deleting one ExampleNode..." -ForegroundColor Yellow
$deleted = Invoke-RestMethod -Uri "$ENDPOINT/$node2Id" -Method Delete
Write-Host "✅ $($deleted.message)" -ForegroundColor Green
Write-Host ""

# Step 8: Verify deletion
Write-Host "Step 8: Verifying deletion..." -ForegroundColor Yellow
$remaining = Invoke-RestMethod -Uri "$ENDPOINT/"
Write-Host "✅ Remaining nodes: $($remaining.data.total)" -ForegroundColor Green
Write-Host ""

# Step 9: Clean up - delete all
Write-Host "Step 9: Cleaning up - deleting all nodes..." -ForegroundColor Yellow
$cleanup = Invoke-RestMethod -Uri "$ENDPOINT/" -Method Delete
Write-Host "✅ $($cleanup.message)" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "All tests completed successfully! ✅" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
