#!/bin/bash
#
# CI/CD Setup Wizard - Main Orchestrator
# This script only orchestrates modules and doesn't implement logic itself
#

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"

# Source all modules
source "$SCRIPT_DIR/modules/user-prompts.sh"
source "$SCRIPT_DIR/modules/git-detector.sh"
source "$SCRIPT_DIR/modules/branch-selector.sh"
source "$SCRIPT_DIR/modules/platform-config.sh"
source "$SCRIPT_DIR/modules/deployment-config.sh"
source "$SCRIPT_DIR/modules/secret-manager.sh"
source "$SCRIPT_DIR/modules/template-builder.sh"

# =============================================================================
# WELCOME
# =============================================================================

echo "🚀 CI/CD Pipeline Setup Wizard"
echo "================================"
echo ""
echo "This wizard will guide you through setting up a complete CI/CD pipeline"
echo "for your Python API project."
echo ""

# Check if running in Docker
if [ ! -f /.dockerenv ] && [ ! -f /run/.containerenv ]; then
    warning_message "This script should be run via docker-compose"
    echo "Please use: docker compose -f ci-cd/docker-compose.cicd-setup.yml run --rm cicd-setup"
    echo ""
    if ! prompt_yes_no "Continue anyway?" "N"; then
        exit 1
    fi
fi

# Load .env file
if [ ! -f .env ]; then
    error_message ".env file not found!"
    echo "Please create .env first. You can run the quick-start script."
    exit 1
fi

# Source .env file
set -a
while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ ! "$line" =~ = ]] && continue
    
    key=$(echo "$line" | cut -d= -f1 | xargs)
    value=$(echo "$line" | cut -d= -f2- | sed 's/#.*//' | xargs)
    
    [[ -z "$key" || "$key" =~ [[:space:]] ]] && continue
    
    export "$key=$value"
done < .env
set +a

# =============================================================================
# GIT REPOSITORY DETECTION
# =============================================================================

section_header "Repository Detection"

if ! check_git_repository; then
    exit 1
fi

# Detect git info
GIT_INFO=$(detect_git_info)
IFS='|' read -r GIT_PLATFORM GIT_OWNER GIT_REPO GIT_REMOTE <<< "$GIT_INFO"

display_git_info "$GIT_PLATFORM" "$GIT_OWNER" "$GIT_REPO" "$GIT_REMOTE"

# Build secrets URL
SECRETS_URL="none"
if [ "$GIT_PLATFORM" = "github" ]; then
    SECRETS_URL=$(build_github_secrets_url "$GIT_OWNER" "$GIT_REPO")
elif [ "$GIT_PLATFORM" = "gitlab" ]; then
    SECRETS_URL=$(build_gitlab_variables_url "$GIT_OWNER" "$GIT_REPO")
fi

echo ""

# =============================================================================
# PLATFORM SELECTION (Auto-detected when possible)
# =============================================================================

if [ "$GIT_PLATFORM" = "github" ] || [ "$GIT_PLATFORM" = "gitlab" ]; then
    PLATFORM="$GIT_PLATFORM"
    PLATFORM_NAME=$(get_platform_name "$PLATFORM")
    success_message "Detected platform: $PLATFORM_NAME"
else
    PLATFORM=$(select_platform)
    PLATFORM_NAME=$(get_platform_name "$PLATFORM")
    success_message "Selected: $PLATFORM_NAME"
fi

echo ""

# =============================================================================
# DEPLOYMENT TARGET SELECTION
# =============================================================================

DEPLOYMENT=$(select_deployment_target)
DEPLOYMENT_NAME=$(get_deployment_name "$DEPLOYMENT")
success_message "Selected: $DEPLOYMENT_NAME"

echo ""

# =============================================================================
# BRANCH SELECTION
# =============================================================================

SELECTED_BRANCHES=$(select_cicd_branches)

echo ""

# =============================================================================
# DEPLOYMENT CONFIGURATION
# =============================================================================

DEPLOY_CONFIG=""
if [ "$DEPLOYMENT" != "build-only" ]; then
    DEPLOY_CONFIG=$(get_deployment_config "$DEPLOYMENT")
fi

echo ""

# =============================================================================
# DOCKER IMAGE CONFIGURATION
# =============================================================================

section_header "Docker Image Configuration"

echo "Current IMAGE_NAME from .env: $IMAGE_NAME" >&2
info_message "In CI/CD this value should come from the GitHub Actions repository variable IMAGE_NAME."
success_message "We'll read IMAGE_NAME from repository variables at pipeline runtime."

echo "" >&2
echo "Current IMAGE_VERSION from .env: $IMAGE_VERSION" >&2
IMAGE_VERSION=$(prompt_text "Initial image version" "$IMAGE_VERSION")

echo "" >&2
echo "Current PYTHON_VERSION from .env: ${PYTHON_VERSION:-3.13}" >&2
PYTHON_VERSION=$(prompt_text "Python version for Docker builds" "${PYTHON_VERSION:-3.13}")

success_message "Image: $IMAGE_NAME:$IMAGE_VERSION"

echo ""

# =============================================================================
# CONFIGURATION SUMMARY
# =============================================================================

display_config_summary "$PLATFORM" "$DEPLOYMENT"

echo "Branches: $SELECTED_BRANCHES" >&2
echo "Image: $IMAGE_NAME:$IMAGE_VERSION" >&2
echo "Python: $PYTHON_VERSION" >&2
echo "" >&2

if ! prompt_yes_no "Proceed with this configuration?" "Y"; then
    echo "Setup cancelled."
    exit 0
fi

# =============================================================================
# BUILD CONFIGURATION FILES
# =============================================================================

# Build .ci.env
build_ci_env "$IMAGE_VERSION" "$PYTHON_VERSION" "$PROJECT_ROOT"

# Build CI/CD workflow files
if [ "$PLATFORM" = "github" ]; then
    build_github_workflow "$DEPLOYMENT" "$SELECTED_BRANCHES" "$PROJECT_ROOT" "$DEPLOY_CONFIG"
elif [ "$PLATFORM" = "gitlab" ]; then
    build_gitlab_ci "$DEPLOYMENT" "$SELECTED_BRANCHES" "$IMAGE_NAME" "$PROJECT_ROOT" "$DEPLOY_CONFIG"
fi

# Update .env with IMAGE_VERSION
update_env_image_version "$PROJECT_ROOT/.env" "$IMAGE_VERSION"

echo ""
success_message "Configuration files created!"

# =============================================================================
# SECRET CREATION GUIDE
# =============================================================================

guide_secret_creation "$PLATFORM" "$DEPLOYMENT" "$SECRETS_URL" "$DEPLOY_CONFIG"

# Display environment warnings
display_env_warnings "$PROJECT_ROOT/.env"

# =============================================================================
# NEXT STEPS
# =============================================================================

section_header "Next Steps"

echo "✅ CI/CD pipeline configuration is complete!" >&2
echo "" >&2
echo "🚀 To activate your pipeline:" >&2
echo "" >&2

if [ "$DEPLOYMENT" = "linux-swarm" ]; then
    IFS='|' read -r server user path port <<< "$DEPLOY_CONFIG"
    echo "1. Set up your deployment server ($server):" >&2
    echo "   - Ensure Docker and Docker Compose are installed" >&2
    echo "   - Verify SSH access with the CI/CD key" >&2
    echo "   - Create deployment directory: mkdir -p $path" >&2
    echo "   - Copy your docker-stack.yml to $path" >&2
    echo "   - Create .env file on server with production values" >&2
    echo "" >&2
fi

echo "2. Commit and push your changes:" >&2
echo "   git add .ci.env .github/ .gitlab-ci.yml" >&2
echo "   git commit -m \"Add CI/CD pipeline configuration\"" >&2
echo "   git push origin main" >&2
echo "" >&2

echo "3. Your pipeline will automatically run on push to: $SELECTED_BRANCHES" >&2
echo "" >&2

echo "4. Monitor the pipeline:" >&2
if [ "$PLATFORM" = "github" ]; then
    if [ "$GIT_PLATFORM" = "github" ]; then
        echo "   https://github.com/$GIT_OWNER/$GIT_REPO/actions" >&2
    else
        echo "   Go to 'Actions' tab in your GitHub repository" >&2
    fi
elif [ "$PLATFORM" = "gitlab" ]; then
    if [ "$GIT_PLATFORM" = "gitlab" ]; then
        echo "   https://gitlab.com/$GIT_OWNER/$GIT_REPO/-/pipelines" >&2
    else
        echo "   Go to 'CI/CD' → 'Pipelines' in your GitLab project" >&2
    fi
fi
echo "" >&2

echo "📚 Additional Resources:" >&2
echo "  - CI/CD documentation: ci-cd/README.md" >&2
echo "  - Update image version: Edit .ci.env and .env, then commit" >&2
echo "  - Build locally: Use build-image/build-image.sh" >&2
echo "" >&2

echo "🎉 Setup complete! Your CI/CD pipeline is ready to use." >&2
echo "" >&2
