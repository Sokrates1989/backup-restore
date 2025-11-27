# Quick-Start Modules

This directory contains modular components used by the `quick-start.sh` and `quick-start.ps1` scripts.

## Module Structure

The modular approach separates concerns and makes the quick-start scripts more maintainable and testable.

### Available Modules

#### 1. `docker_helpers.sh` / `docker_helpers.ps1`
**Purpose:** Docker installation and configuration checks

**Functions:**
- `check_docker_installation()` / `Test-DockerInstallation` - Verifies Docker, Docker daemon, and Docker Compose are installed and running
- `read_env_variable()` / `Get-EnvVariable` - Reads environment variables from .env files
- `determine_compose_file()` / `Get-ComposeFile` - Determines which Docker Compose file to use based on database type and mode

#### 2. `version_manager.sh` / `version_manager.ps1`
**Purpose:** Semantic versioning and image version management

**Functions:**
- `bump_semver()` / `Bump-SemVer` - Bumps semantic version (patch, minor, or major)
- `update_image_version_in_file()` / `Update-ImageVersionInFile` - Updates IMAGE_VERSION in a specific file
- `update_image_version()` / `Update-ImageVersion` - Interactive version update for both .env and .ci.env

#### 3. `menu_handlers.sh` / `menu_handlers.ps1`
**Purpose:** Menu action handlers for the quick-start script

**Functions:**
- `handle_backend_start()` / `Start-Backend` - Starts the backend with Docker Compose
- `handle_dependency_management()` / `Start-DependencyManagement` - Opens dependency management menu
- `handle_dependency_and_backend()` / `Start-DependencyAndBackend` - Runs dependency management then starts backend
- `handle_python_version_test()` / `Test-PythonVersionConfiguration` - Tests Python version configuration
- `handle_build_production_image()` / `Build-ProductionImage` - Builds production Docker image
- `handle_cicd_setup()` / `Start-CICDSetup` - Sets up CI/CD pipeline

## Usage in Quick-Start Scripts

### Bash (quick-start.sh)
```bash
# Source modules at the beginning of the script
source "${SETUP_DIR}/modules/docker_helpers.sh"
source "${SETUP_DIR}/modules/version_manager.sh"
source "${SETUP_DIR}/modules/menu_handlers.sh"

# Use module functions
if ! check_docker_installation; then
    exit 1
fi
```

### PowerShell (quick-start.ps1)
```powershell
# Import modules at the beginning of the script
Import-Module "$setupDir\modules\docker_helpers.ps1" -Force
Import-Module "$setupDir\modules\version_manager.ps1" -Force
Import-Module "$setupDir\modules\menu_handlers.ps1" -Force

# Use module functions
if (-not (Test-DockerInstallation)) {
    exit 1
}
```

## Benefits of Modular Approach

1. **Maintainability** - Each module focuses on a single responsibility
2. **Reusability** - Functions can be reused across different scripts
3. **Testability** - Individual modules can be tested in isolation
4. **Readability** - Main scripts are cleaner and easier to understand
5. **Scalability** - New features can be added as new modules without cluttering main scripts

## Adding New Modules

To add a new module:

1. Create both `.sh` and `.ps1` versions in this directory
2. Implement equivalent functions in both versions
3. Source/Import the module in the main quick-start scripts
4. Document the module functions in this README

## Module Naming Convention

- Use lowercase with underscores for bash files: `module_name.sh`
- Use PascalCase for PowerShell files: `ModuleName.ps1`
- Use descriptive function names that clearly indicate their purpose
- Maintain consistency between bash and PowerShell function names (accounting for shell conventions)
