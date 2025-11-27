# docker_helpers.ps1
# PowerShell module for Docker-related helper functions

function Test-DockerInstallation {
    Write-Host "Checking Docker installation..." -ForegroundColor Yellow
    
    try {
        $null = docker --version 2>&1
        if ($LASTEXITCODE -ne 0) { throw "Docker not found" }
    } catch {
        Write-Host "[ERROR] Docker is not installed!" -ForegroundColor Red
        Write-Host "Please install Docker from: https://www.docker.com/get-started" -ForegroundColor Yellow
        return $false
    }

    try {
        $null = docker info 2>&1
        if ($LASTEXITCODE -ne 0) { throw "Docker daemon not running" }
    } catch {
        Write-Host "[ERROR] Docker daemon is not running!" -ForegroundColor Red
        Write-Host "Please start Docker Desktop or the Docker service" -ForegroundColor Yellow
        return $false
    }

    try {
        $null = docker compose version 2>&1
        if ($LASTEXITCODE -ne 0) { throw "Docker Compose not available" }
    } catch {
        Write-Host "[ERROR] Docker Compose is not available!" -ForegroundColor Red
        Write-Host "Please install a current Docker version with Compose plugin" -ForegroundColor Yellow
        return $false
    }

    Write-Host "Docker is installed and running" -ForegroundColor Green
    return $true
}

function Get-EnvVariable {
    param(
        [string]$VariableName,
        [string]$EnvFile = ".env",
        [string]$DefaultValue = ""
    )
    
    if (-not (Test-Path $EnvFile)) {
        return $DefaultValue
    }
    
    $content = Get-Content $EnvFile -ErrorAction SilentlyContinue
    $line = $content | Where-Object { $_ -match "^$VariableName=" } | Select-Object -First 1
    
    if ($line) {
        $value = ($line -split "=", 2)[1].Trim().Trim('"')
        return $value
    }
    
    return $DefaultValue
}

function Get-ComposeFile {
    param(
        [string]$DbType,
        [string]$DbMode
    )
    
    if ($DbMode -eq "external") {
        return "local-deployment\docker-compose.yml"
    } elseif ($DbType -eq "neo4j") {
        return "local-deployment\docker-compose.neo4j.yml"
    } elseif ($DbType -eq "postgresql" -or $DbType -eq "mysql") {
        return "local-deployment\docker-compose.postgres.yml"
    } else {
        return "local-deployment\docker-compose.yml"
    }
}
