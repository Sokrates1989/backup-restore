#!/usr/bin/env pwsh
# Quick script to rebuild and push the Docker image with the migration fix

$ErrorActionPreference = "Stop"

Write-Host "🔨 Rebuilding Docker Image with Migration Fix" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# Get the current version from pyproject.toml
$VERSION = (Get-Content pyproject.toml | Select-String '^version = "(.+)"').Matches.Groups[1].Value
Write-Host "📦 Current version: $VERSION" -ForegroundColor Yellow
Write-Host ""

# Ask for confirmation
$response = Read-Host "Build and push sokrates1989/python-api-template:$VERSION? (y/n)"
if ($response -ne 'y' -and $response -ne 'Y') {
    Write-Host "❌ Cancelled" -ForegroundColor Red
    exit 1
}

# Build the image
Write-Host "🔨 Building Docker image..." -ForegroundColor Yellow
docker build -t sokrates1989/python-api-template:$VERSION .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Build successful" -ForegroundColor Green
Write-Host ""

# Tag as latest
Write-Host "🏷️  Tagging as latest..." -ForegroundColor Yellow
docker tag sokrates1989/python-api-template:$VERSION sokrates1989/python-api-template:latest

# Push to Docker Hub
Write-Host "📤 Pushing to Docker Hub..." -ForegroundColor Yellow
docker push sokrates1989/python-api-template:$VERSION
docker push sokrates1989/python-api-template:latest

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Push failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Successfully built and pushed:" -ForegroundColor Green
Write-Host "   - sokrates1989/python-api-template:$VERSION" -ForegroundColor Green
Write-Host "   - sokrates1989/python-api-template:latest" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Update your swarm deployment:" -ForegroundColor White
Write-Host "      docker service update --image sokrates1989/python-api-template:$VERSION python-api-template_api" -ForegroundColor Gray
Write-Host ""
Write-Host "   2. Or use the quick-start script:" -ForegroundColor White
Write-Host "      .\quick-start.ps1" -ForegroundColor Gray
Write-Host "      Choose option 4 (Update API image)" -ForegroundColor Gray
Write-Host ""
Write-Host "   3. Verify migrations ran successfully:" -ForegroundColor White
Write-Host "      docker service logs python-api-template_api --tail 50" -ForegroundColor Gray
Write-Host ""
