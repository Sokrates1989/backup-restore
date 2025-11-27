# CI/CD Setup Wizard - Modular Architecture

This directory contains the modular CI/CD setup wizard that guides users through configuring continuous integration and deployment pipelines.

## Structure

```
setup/
├── setup-cicd-wizard.sh      # Main orchestrator script (Linux/Mac)
├── setup-cicd-wizard.ps1     # Main orchestrator script (Windows)
├── modules/                   # Reusable modules
│   ├── git-detector.sh        # Detects git remote and builds URLs
│   ├── branch-selector.sh     # Fetches and lets user select branches
│   ├── platform-config.sh     # Platform selection (GitHub/GitLab)
│   ├── deployment-config.sh   # Deployment target configuration
│   ├── secret-manager.sh      # Guides secret creation step-by-step
│   ├── template-builder.sh    # Builds CI/CD files from templates
│   └── user-prompts.sh        # Reusable prompt functions
└── templates/                 # CI/CD file templates
    ├── github/
    │   └── build-deploy-linux.yml
    └── gitlab/
        └── .gitlab-ci-linux.yml
```

## Design Principles

1. **Pure Orchestration**: The main script only orchestrates modules, doesn't implement logic
2. **Single Responsibility**: Each module handles one specific concern
3. **Reusability**: Functions can be sourced and used independently
4. **Maintainability**: Small, focused files are easier to update
5. **Step-by-Step**: User is guided through each step with confirmation

## Module Responsibilities

### git-detector.sh
- Detects git remote URL
- Parses GitHub/GitLab repository info
- Builds settings URLs for secrets/variables

### branch-selector.sh
- Fetches remote branches
- Presents selection menu
- Returns selected branches for CI/CD triggers

### platform-config.sh
- Platform selection (GitHub Actions / GitLab CI)
- Deployment target selection
- Returns configuration choices

### deployment-config.sh
- Collects deployment-specific settings
- Validates SSH hosts, Azure configs, etc.
- Returns deployment parameters

### secret-manager.sh
- Step-by-step secret creation guide
- Shows current local values with security warnings
- Provides copy-paste commands
- Waits for user confirmation at each step

### template-builder.sh
- Builds .ci.env with only IMAGE_VERSION
- Generates CI/CD workflow files
- Injects user configuration into templates

### user-prompts.sh
- Reusable prompt functions
- Input validation
- Yes/No prompts
- Selection menus

## Usage

```bash
# Run the setup wizard
docker compose -f ci-cd/docker-compose.cicd-setup.yml run --rm cicd-setup
```

## Flow

1. Welcome & prerequisites check
2. Detect git repository information
3. Select CI/CD platform
4. Select deployment target
5. Select branches for CI/CD triggers
6. Configure deployment settings
7. Build .ci.env (IMAGE_VERSION only)
8. Build CI/CD workflow files
9. Guide through secret creation (step-by-step)
10. Summary & next steps
