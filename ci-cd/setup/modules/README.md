# CI/CD Setup Modules

This directory contains reusable, single-responsibility modules for the CI/CD setup wizard.

## Module Overview

### user-prompts.sh
**Purpose**: Reusable user input functions

**Functions**:
- `prompt_yes_no(question, default)` - Yes/No prompts with defaults
- `prompt_text(prompt, default)` - Text input with optional default
- `prompt_selection(prompt, options...)` - Single selection from list
- `prompt_multi_selection(prompt, options...)` - Multiple selections from list
- `wait_for_enter(message)` - Pause for user confirmation
- `section_header(title)` - Display formatted section headers
- `success_message(msg)` - Display success messages
- `warning_message(msg)` - Display warnings
- `error_message(msg)` - Display errors
- `info_message(msg)` - Display info messages

**Dependencies**: None

---

### git-detector.sh
**Purpose**: Git repository detection and URL building

**Functions**:
- `detect_git_info()` - Detects git remote and extracts platform/owner/repo
- `build_github_secrets_url(owner, repo)` - Builds GitHub secrets settings URL
- `build_gitlab_variables_url(owner, repo)` - Builds GitLab variables settings URL
- `display_git_info(platform, owner, repo, url)` - Displays repository information
- `get_remote_branches()` - Lists all remote branches
- `check_git_repository()` - Validates git repository exists

**Dependencies**: user-prompts.sh (for error_message)

**Returns**: Pipe-separated values: `platform|owner|repo|remote_url`

---

### branch-selector.sh
**Purpose**: Branch selection for CI/CD triggers

**Functions**:
- `select_cicd_branches()` - Interactive branch selection
- `format_branches_github(branches)` - Formats branches for GitHub Actions YAML
- `format_branches_gitlab(branches)` - Formats branches for GitLab CI YAML
- `validate_branch_name(branch)` - Validates branch exists in remote

**Dependencies**: 
- user-prompts.sh
- git-detector.sh (for get_remote_branches)

**Returns**: Space-separated branch names (e.g., "main develop production")

---

### platform-config.sh
**Purpose**: CI/CD platform and deployment target selection

**Functions**:
- `select_platform()` - Select GitHub or GitLab
- `select_deployment_target()` - Select deployment destination
- `get_platform_name(platform)` - Get display name for platform
- `get_deployment_name(deployment)` - Get display name for deployment
- `display_config_summary(platform, deployment)` - Show configuration summary

**Dependencies**: user-prompts.sh

**Returns**: 
- Platform: `github` or `gitlab`
- Deployment: `linux-swarm`, `azure-aci`, `azure-appservice`, or `build-only`

---

### deployment-config.sh
**Purpose**: Deployment-specific configuration collection

**Functions**:
- `configure_linux_deployment()` - Collect Linux/Swarm settings
- `configure_azure_aci_deployment()` - Collect Azure ACI settings
- `configure_azure_appservice_deployment()` - Collect Azure App Service settings
- `get_deployment_config(target)` - Routes to appropriate config function

**Dependencies**: user-prompts.sh

**Returns**: Pipe-separated deployment configuration
- Linux: `server|user|path|port`
- Azure ACI: `resource_group|container_name|location`
- Azure App Service: `resource_group|app_name|location`

---

### secret-manager.sh
**Purpose**: Step-by-step secret creation guidance

**Functions**:
- `guide_secret_creation(platform, deployment, url, config)` - Main orchestrator
- `create_docker_secrets(platform)` - Guide Docker registry secrets
- `create_linux_secrets(platform, config)` - Guide SSH secrets
- `create_azure_secrets(platform)` - Guide Azure credentials
- `display_env_warnings(env_file)` - Show environment variable warnings

**Dependencies**: user-prompts.sh

**Features**:
- Shows current local values with security assessment
- Explains whether local values are safe to use
- Provides step-by-step instructions
- Waits for user confirmation at each step
- Displays copy-paste commands

---

### template-builder.sh
**Purpose**: Build CI/CD configuration files from templates

**Functions**:
- `build_ci_env(version, project_root)` - Creates .ci.env with IMAGE_VERSION only
- `build_github_workflow(deployment, branches, image, root, config)` - Creates GitHub Actions workflow
- `build_gitlab_ci(deployment, branches, image, root, config)` - Creates GitLab CI config
- `update_env_image_version(env_file, version)` - Updates .env IMAGE_VERSION

**Dependencies**: 
- user-prompts.sh
- branch-selector.sh (for format functions)

**Output Files**:
- `.ci.env` - Contains only IMAGE_VERSION
- `.github/workflows/ci-cd.yml` - GitHub Actions workflow
- `.gitlab-ci.yml` - GitLab CI configuration

---

## Design Principles

1. **Single Responsibility**: Each module handles one specific concern
2. **Pure Functions**: Functions return values via stdout, use stderr for messages
3. **No Side Effects**: Functions don't modify global state unexpectedly
4. **Composability**: Modules can be sourced and used independently
5. **Error Handling**: Functions return proper exit codes
6. **User Feedback**: All user-facing messages go to stderr, data to stdout

## Usage Pattern

```bash
# Source required modules
source "modules/user-prompts.sh"
source "modules/git-detector.sh"

# Use functions
GIT_INFO=$(detect_git_info)
IFS='|' read -r platform owner repo url <<< "$GIT_INFO"

if prompt_yes_no "Continue?" "Y"; then
    success_message "Proceeding..."
fi
```

## Adding New Modules

When creating a new module:

1. Create a descriptive filename: `feature-name.sh`
2. Add a header comment explaining the purpose
3. Document all functions with usage examples
4. List dependencies at the top
5. Use stderr for user messages, stdout for data
6. Return proper exit codes (0 = success, 1 = error)
7. Update this README with the new module

## Testing

Test modules individually:

```bash
# Source and test a module
source modules/user-prompts.sh
result=$(prompt_text "Enter name" "default")
echo "Got: $result"
```
