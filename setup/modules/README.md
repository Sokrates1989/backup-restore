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

#### 3. `browser_helpers.sh` / `browser_helpers.ps1`
**Purpose:** Browser automation for opening URLs in incognito/private mode

**Functions:**
- `open_url()` / `Open-Url` - Opens a URL in incognito browser with first-run prompt suppression
- `wait_for_url()` / `Wait-ForUrl` - Polls a URL until it becomes available
- `show_api_docs_delayed()` / `Show-RelevantPagesDelayed` - Opens API docs and web GUI when services are ready
- `stop_incognito_profile_procs()` / `Stop-IncognitoProfileProcesses` - Cleans up browser profile processes

#### 4. `menu_io.sh` / `menu_io.ps1`
**Purpose:** I/O utilities for menu prompts

**Functions:**
- `read_prompt()` - Reads user input with TTY fallback (Bash)
- `Get-EnvVariable` - Reads variables from .env files (PowerShell)

#### 5. `menu_browser.sh` / `menu_browser.ps1`
**Purpose:** Browser-related menu actions using shared browser helpers

**Functions:**
- `open_browser_incognito()` / `Open-BrowserInIncognito` - Opens multiple URLs for test/admin modes

#### 6. `menu_keycloak.sh` / `menu_keycloak.ps1`
**Purpose:** Keycloak authentication and bootstrap operations

**Functions:**
- `get_keycloak_access_token()` / `Get-KeycloakAccessToken` - Retrieves Keycloak access token for CLI operations
- `handle_keycloak_bootstrap()` / `Invoke-KeycloakBootstrap` - Bootstraps Keycloak realm with clients, roles, and users

#### 7. `menu_actions.sh` / `menu_actions.ps1`
**Purpose:** Main menu action handlers

**Functions:**
- `handle_backend_start()` / `Start-Backend` - Starts the backend with Docker Compose
- `handle_dependency_management()` / `Start-DependencyManagement` - Opens dependency management menu
- `handle_deploy_all_services()` / `Deploy-AllServices` - Deploys all services (API, runner, GUI)
- `handle_build_production_image()` / `Build-ProductionImage` - Builds production Docker image
- `handle_cicd_setup()` / `Start-CICDSetup` - Sets up CI/CD pipeline
- `handle_start_with_test_databases()` / `Start-WithTestDatabases` - Starts with test database containers
- `handle_start_admin_uis()` / `Start-WithAdminUIs` - Starts with admin UI containers
- `handle_view_logs()` - Views Docker Compose logs (Bash)
- `handle_db_reinstall()` - Reinstalls database volumes (Bash)
- `show_main_menu()` / `Show-MainMenu` - Displays and handles main menu

#### 8. `menu_handlers.sh` / `menu_handlers.ps1` (Legacy)
**Purpose:** Original monolithic menu handlers (kept for backward compatibility)

> **Note:** These files are superseded by the modular `menu_io`, `menu_browser`, `menu_keycloak`, and `menu_actions` modules. New development should use the modular approach.

## Usage in Quick-Start Scripts

### Bash (quick-start.sh)
```bash
# Source modules at the beginning of the script
source "${SETUP_DIR}/modules/docker_helpers.sh"
source "${SETUP_DIR}/modules/version_manager.sh"
source "${SETUP_DIR}/modules/browser_helpers.sh"
source "${SETUP_DIR}/modules/menu_io.sh"
source "${SETUP_DIR}/modules/menu_browser.sh"
source "${SETUP_DIR}/modules/menu_keycloak.sh"
source "${SETUP_DIR}/modules/menu_actions.sh"

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
Import-Module "$setupDir\modules\browser_helpers.ps1" -Force
Import-Module "$setupDir\modules\menu_io.ps1" -Force
Import-Module "$setupDir\modules\menu_browser.ps1" -Force
Import-Module "$setupDir\modules\menu_keycloak.ps1" -Force
Import-Module "$setupDir\modules\menu_actions.ps1" -Force

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
