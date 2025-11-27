# manage-python-project-dependencies.ps1
#
# PowerShell version of manage-python-project-dependencies.sh
# This script automates the setup and interactive use of a Dockerized Python dependency management environment.
# Usage: .\manage-python-project-dependencies.ps1 [-InitialRun]
#
# - Checks Docker installation and availability
# - Builds the dev Docker image (if needed)
# - Runs the setup script to generate poetry.lock and pdm.lock
# - Drops the user into an interactive shell with Poetry and PDM ready to use (default)
# - OR runs initial setup non-interactively with pdm install (initial-run parameter)
# - All changes persist in your project directory

param(
    [switch]$InitialRun
)

$ErrorActionPreference = "Stop"

# Helper function for colored output
function Write-ColorOutput {
    param(
        [Parameter(Position=0)]
        [string]$Message,
        [Parameter(Position=1)]
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

Write-ColorOutput "Python Dependency Management with Docker" "Cyan"
Write-Host ""

# Check Docker availability
Write-ColorOutput "Checking Docker installation..." "Cyan"
try {
    $null = & docker --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Docker not found" }
} catch {
    Write-ColorOutput "[ERROR] Docker is not installed!" "Red"
    Write-ColorOutput "Please install Docker from: https://www.docker.com/get-started" "Yellow"
    exit 1
}

# Check Docker daemon
try {
    $null = & docker info 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Docker daemon not running" }
} catch {
    Write-ColorOutput "[ERROR] Docker daemon is not running!" "Red"
    Write-ColorOutput "Please start Docker Desktop or the Docker service" "Yellow"
    exit 1
}

# Check Docker Compose
try {
    $null = & docker compose version 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose not available" }
} catch {
    Write-ColorOutput "[ERROR] Docker Compose is not available!" "Red"
    Write-ColorOutput "Please install a current Docker version with Compose plugin" "Yellow"
    exit 1
}

Write-ColorOutput "[OK] Docker is installed and running" "Green"
Write-Host ""

# Change to the python-dependency-management directory for config files
$originalPath = Get-Location
# First go to the script's directory, then to parent (python-dependency-management)
Set-Location $PSScriptRoot
Set-Location ..

# Check if config.env exists, if not create it from example
if (-not (Test-Path "config.env")) {
    if (Test-Path "config.env.example") {
        Write-ColorOutput "config.env not found. Creating from config.env.example..." "Yellow"
        Copy-Item "config.env.example" "config.env"
        Write-ColorOutput "[OK] Created config.env from example template" "Green"
    } else {
        Write-ColorOutput "[ERROR] Neither config.env nor config.env.example found!" "Red"
        Set-Location $originalPath
        exit 1
    }
} else {
    Write-ColorOutput "[OK] config.env found" "Green"
}

# Show current configuration
Write-ColorOutput "Current configuration:" "Cyan"
Write-Host ""
Get-Content "config.env" | ForEach-Object {
    $line = $_.Trim()
    # Skip empty lines and comments
    if ($line -and -not $line.StartsWith("#")) {
        Write-ColorOutput "  $line" "Yellow"
    }
}
Write-Host ""

# Ask user if they want to proceed or modify config (unless in initial-run mode)
if ($InitialRun) {
    Write-ColorOutput "[OK] Initial run mode: Proceeding with current configuration automatically..." "Green"
} else {
    Write-ColorOutput "Do you want to proceed with this configuration?" "Cyan"
    Write-ColorOutput "  [y] Yes, proceed with current config" "Yellow"
    Write-ColorOutput "  [n] No, let me modify config.env first" "Yellow"
    Write-Host ""
    $choice = Read-Host "Enter your choice (y/n)"

    switch ($choice.ToLower()) {
        { $_ -in @("y", "yes", "") } {
            Write-ColorOutput "[OK] Proceeding with current configuration..." "Green"
        }
        { $_ -in @("n", "no") } {
            Write-ColorOutput "Please edit python-dependency-management\config.env and run this script again." "Yellow"
            Write-ColorOutput "You can use: notepad python-dependency-management\config.env" "Yellow"
            Set-Location $originalPath
            exit 0
        }
        default {
            Write-ColorOutput "[ERROR] Invalid choice. Please run the script again and choose y or n." "Red"
            Set-Location $originalPath
            exit 1
        }
    }
}

Write-ColorOutput "[python-dependency-management] Building dev environment Docker image..." "Yellow"

# Build the Docker image using the root docker-compose file
Set-Location ..
& docker compose --env-file .env -f local-deployment\docker-compose-python-dependency-management.yml build

if ($LASTEXITCODE -ne 0) {
    Write-ColorOutput "[ERROR] Docker build failed!" "Red"
    exit 1
}

Write-ColorOutput "[python-dependency-management] Running setup script to generate lock files..." "Yellow"

# Run the setup script in a container (use bash to handle potential line ending issues)
& docker compose --env-file .env -f local-deployment\docker-compose-python-dependency-management.yml run --rm dev /bin/bash ./python-dependency-management/dev-setup.sh

if ($LASTEXITCODE -ne 0) {
    Write-ColorOutput "[ERROR] Setup script failed!" "Red"
    exit 1
}

Write-ColorOutput "[python-dependency-management] Setup complete!" "Green"

if ($InitialRun) {
    Write-ColorOutput "Initial run mode: Running pdm install to update lock files..." "Cyan"
    Write-ColorOutput "This will ensure your project dependencies are properly locked and ready for Docker builds." "Yellow"
    Write-ColorOutput "This may take a moment on first run, but subsequent runs will be faster." "Yellow"
    Write-Host ""
    
    # Run pdm install in the container to generate proper lock files
    & docker compose --env-file .env -f local-deployment\docker-compose-python-dependency-management.yml run --rm dev pdm install
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "[ERROR] PDM install failed!" "Red"
        exit 1
    }
    
    Write-ColorOutput "[OK] PDM install completed successfully!" "Green"
    Write-ColorOutput "Your project is now ready for Docker builds!" "Cyan"
    Write-Host ""
    Write-ColorOutput "Next steps:" "Yellow"
    Write-ColorOutput "  - Your lock files have been updated" "Yellow"
    Write-ColorOutput "  - Docker builds will now work correctly" "Yellow"
    Write-ColorOutput "  - To manage dependencies interactively, run: .\manage-python-project-dependencies.ps1" "Yellow"
    Write-Host ""
    Write-ColorOutput "Common PDM commands for future reference:" "Yellow"
    Write-ColorOutput "  pdm add requests          # Add a package" "Yellow"
    Write-ColorOutput "  pdm add pytest --dev     # Add development dependency" "Yellow"
    Write-ColorOutput "  pdm remove requests       # Remove a package" "Yellow"
    Write-ColorOutput "  pdm install              # Install all dependencies" "Yellow"
    Write-ColorOutput "  pdm update               # Update all dependencies" "Yellow"
    Write-Host ""
} else {
    Write-ColorOutput "Dropping you into an interactive shell with Poetry and PDM ready to use..." "Cyan"
    Write-Host ""
    Write-ColorOutput "Common PDM Commands and Use Cases:" "Cyan"
    Write-Host ""
    Write-ColorOutput "Basic Package Management:" "Yellow"
    Write-ColorOutput "  pdm add requests                    # Add a package" "Gray"
    Write-ColorOutput "  pdm add `"requests>=2.28.0`"         # Add with version constraint" "Gray"
    Write-ColorOutput "  pdm add pytest --dev               # Add development dependency" "Gray"
    Write-ColorOutput "  pdm remove requests                 # Remove a package" "Gray"
    Write-ColorOutput "  pdm install                         # Install all dependencies" "Gray"
    Write-ColorOutput "  pdm list                            # List installed packages" "Gray"
    Write-Host ""
    Write-ColorOutput "Dependency Management:" "Yellow"
    Write-ColorOutput "  pdm update                          # Update all dependencies" "Gray"
    Write-ColorOutput "  pdm update requests                 # Update specific package" "Gray"
    Write-ColorOutput "  pdm lock                            # Update lock file" "Gray"
    Write-ColorOutput "  pdm lock --check                    # Check if lock file is up-to-date" "Gray"
    Write-ColorOutput "  pdm sync                            # Sync environment with lock file" "Gray"
    Write-Host ""
    Write-ColorOutput "Troubleshooting and Conflicts:" "Yellow"
    Write-ColorOutput "  pdm lock --update-reuse             # Update lock with conflict resolution" "Gray"
    Write-ColorOutput "  pdm install --no-lock               # Install without updating lock file" "Gray"
    Write-ColorOutput "  pdm cache clear                     # Clear package cache" "Gray"
    Write-ColorOutput "  pdm info                            # Show project information" "Gray"
    Write-ColorOutput "  pdm info requests                   # Show package details" "Gray"
    Write-Host ""
    Write-ColorOutput "Python Version Management:" "Yellow"
    Write-ColorOutput "  pdm python list                     # List available Python versions" "Gray"
    Write-ColorOutput "  pdm python install 3.12             # Install specific Python version" "Gray"
    Write-ColorOutput "  pdm use 3.12                        # Switch to Python 3.12" "Gray"
    Write-Host ""
    Write-ColorOutput "Running Scripts:" "Yellow"
    Write-ColorOutput "  pdm run python script.py            # Run script with project dependencies" "Gray"
    Write-ColorOutput "  pdm run pytest                      # Run tests" "Gray"
    Write-ColorOutput "  pdm run --list                      # List available scripts" "Gray"
    Write-Host ""
    Write-ColorOutput "Debugging Dependency Issues:" "Yellow"
    Write-ColorOutput "  pdm show --graph                    # Show dependency tree" "Gray"
    Write-ColorOutput "  pdm show --reverse requests         # Show what depends on requests" "Gray"
    Write-ColorOutput "  pdm export -f requirements          # Export to requirements.txt format" "Gray"
    Write-ColorOutput "  pdm import requirements.txt         # Import from requirements.txt" "Gray"
    Write-Host ""
    Write-ColorOutput "Quick Fixes for Common Issues:" "Yellow"
    Write-ColorOutput "  # Dependency conflict resolution:" "Gray"
    Write-ColorOutput "  pdm lock --update-reuse --resolution=highest" "Gray"
    Write-Host ""
    Write-ColorOutput "  # Force reinstall all packages:" "Gray"
    Write-ColorOutput "  pdm sync --reinstall" "Gray"
    Write-Host ""
    Write-ColorOutput "  # Install from fresh lock file:" "Gray"
    Write-ColorOutput "  rm pdm.lock; pdm lock; pdm install" "Gray"
    Write-Host ""
    Write-ColorOutput "Type 'exit' to leave the container when done." "Yellow"
    Write-Host ""

    # Start interactive shell in a clean container
    & docker compose --env-file .env -f local-deployment\docker-compose-python-dependency-management.yml run --rm dev
}
