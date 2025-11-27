#!/usr/bin/env pwsh
# run-docker-build-diagnostics.ps1
# Comprehensive Docker build diagnostics for the Python API template

$ErrorActionPreference = "Stop"

# Change to project root (script lives in python-dependency-management\scripts)
Set-Location (Join-Path $PSScriptRoot "..\..")

function Write-ColorOutput {
    param(
        [Parameter(Mandatory=$true, Position=0)][string]$Message,
        [Parameter(Position=1)][string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Show-Diagnostics {
    Write-Host ""
    Write-ColorOutput "Diagnostic Information:" "Cyan"
    Write-ColorOutput "=======================" "Cyan"

    try {
        $null = & docker --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "[OK] Docker CLI available" "Green"
            try {
                $null = & docker info 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-ColorOutput "[OK] Docker daemon is running" "Green"
                } else {
                    Write-ColorOutput "[ERROR] Docker daemon is not running" "Red"
                }
            } catch {
                Write-ColorOutput "[ERROR] Docker daemon is not running" "Red"
            }
        } else {
            Write-ColorOutput "[ERROR] Docker CLI not found" "Red"
        }
    } catch {
        Write-ColorOutput "[ERROR] Docker CLI not found" "Red"
    }

    try {
        $composeVersion = & docker compose version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "[OK] docker compose command available" "Green"
        } else {
            Write-ColorOutput "[ERROR] docker compose command unavailable" "Red"
        }
    } catch {
        Write-ColorOutput "[ERROR] docker compose command unavailable" "Red"
    }

    if (Test-Path .env) {
        Write-ColorOutput "[OK] .env file exists" "Green"
        $envContent = Get-Content .env -Raw
        if ($envContent -match "PYTHON_VERSION") {
            $pythonVersionLine = (Get-Content .env | Where-Object { $_ -match '^PYTHON_VERSION' }) -join ", "
            Write-ColorOutput "[OK] PYTHON_VERSION is defined -> $pythonVersionLine" "Green"
        } else {
            Write-ColorOutput "[ERROR] PYTHON_VERSION missing in .env" "Red"
        }
    } else {
        Write-ColorOutput "[ERROR] .env file does not exist" "Red"
    }

    if (Test-Path Dockerfile) {
        Write-ColorOutput "[OK] Dockerfile exists" "Green"
    } else {
        Write-ColorOutput "[ERROR] Dockerfile missing" "Red"
    }

    if (Test-Path python-dependency-management\Dockerfile) {
        Write-ColorOutput "[OK] python-dependency-management/Dockerfile exists" "Green"
    } else {
        Write-ColorOutput "[ERROR] python-dependency-management/Dockerfile missing" "Red"
    }

    $composeFiles = @(
        'local-deployment/docker-compose.yml',
        'local-deployment/docker-compose.postgres.yml',
        'local-deployment/docker-compose.neo4j.yml'
    )

    foreach ($file in $composeFiles) {
        if (Test-Path $file) {
            Write-ColorOutput "[OK] $file exists" "Green"
        } else {
            Write-ColorOutput "[ERROR] $file missing" "Red"
        }
    }
}

function Invoke-DockerBuild {
    param(
        [Parameter(Mandatory=$true)][string]$Description,
        [Parameter(Mandatory=$true)][string[]]$Arguments,
        [string]$SuccessMessage
    )

    Write-Host ""
    Write-ColorOutput $Description "Cyan"
    & docker @Arguments
    if ($LASTEXITCODE -eq 0) {
        if ($SuccessMessage) {
            Write-ColorOutput $SuccessMessage "Green"
        } else {
            Write-ColorOutput "[OK] $Description" "Green"
        }
    } else {
        Write-ColorOutput "[ERROR] $Description failed" "Red"
        Show-Diagnostics
        exit 1
    }
}

function Invoke-ComposeBuild {
    param(
        [Parameter(Mandatory=$true)][string]$ComposeFile,
        [Parameter(Mandatory=$true)][string]$Description
    )

    Write-ColorOutput "→ Building $Description ($ComposeFile)" "Cyan"
    $args = @("compose", "-f", $ComposeFile, "build", "--no-cache")
    & docker @args
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "[OK] $Description builds successfully" "Green"
    } else {
        Write-ColorOutput "[ERROR] $Description build failed" "Red"
        Show-Diagnostics
        exit 1
    }
    Write-Host ""
}

Write-ColorOutput "Running Docker build diagnostics..." "Cyan"
Write-ColorOutput "==================================" "Cyan"

if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*)\s*=\s*(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim().Trim('"').Trim("'")
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
    if (-not $env:PYTHON_VERSION) {
        Write-ColorOutput "[ERROR] PYTHON_VERSION not found in loaded environment." "Red"
        Show-Diagnostics
        exit 1
    }
    Write-ColorOutput "[OK] Loaded .env configuration (PYTHON_VERSION=$($env:PYTHON_VERSION))" "Green"
} else {
    Write-ColorOutput "[ERROR] .env file not found" "Red"
    Write-ColorOutput "   Please ensure .env exists in the project root" "Yellow"
    Show-Diagnostics
    exit 1
}

Invoke-DockerBuild -Description "Building main Dockerfile" -Arguments @("build", "--build-arg", "PYTHON_VERSION=$($env:PYTHON_VERSION)", "-t", "diagnostics-main", ".") -SuccessMessage "[OK] Main Dockerfile builds successfully"

Push-Location python-dependency-management
Invoke-DockerBuild -Description "Building python-dependency-management Dockerfile" -Arguments @("build", "--build-arg", "PYTHON_VERSION=$($env:PYTHON_VERSION)", "-t", "diagnostics-dev", ".") -SuccessMessage "[OK] python-dependency-management Dockerfile builds successfully"
Pop-Location

Write-Host ""
Write-ColorOutput "Testing docker compose stacks..." "Cyan"
Invoke-ComposeBuild -ComposeFile "local-deployment/docker-compose.yml" -Description "base services"
Invoke-ComposeBuild -ComposeFile "local-deployment/docker-compose.postgres.yml" -Description "PostgreSQL stack"
Invoke-ComposeBuild -ComposeFile "local-deployment/docker-compose.neo4j.yml" -Description "Neo4j stack"

Write-ColorOutput "🎉 Docker build diagnostics completed successfully!" "Green"
Write-ColorOutput "===============================================" "Green"
