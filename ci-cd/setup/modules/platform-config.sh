#!/bin/bash
# Platform configuration module
# Handles CI/CD platform and deployment target selection

# Select CI/CD platform
# Returns: github|gitlab
select_platform() {
    section_header "STEP 1: CI/CD Platform Selection"
    
    local choice=$(prompt_selection \
        "Which CI/CD platform would you like to use?" \
        "GitHub Actions" \
        "GitLab CI/CD")
    
    case $choice in
        0) echo "github" ;;
        1) echo "gitlab" ;;
        *) echo "github" ;;
    esac
}

# Select deployment target
# Returns: linux-swarm|azure-aci|azure-appservice|build-only
select_deployment_target() {
    section_header "STEP 2: Deployment Target Selection"
    
    local choice=$(prompt_selection \
        "Where would you like to deploy your application?" \
        "Linux Server / Docker Swarm Cluster" \
        "Azure Container Instances" \
        "Azure App Service" \
        "Build Only (no automatic deployment)")
    
    case $choice in
        0) echo "linux-swarm" ;;
        1) echo "azure-aci" ;;
        2) echo "azure-appservice" ;;
        3) echo "build-only" ;;
        *) echo "linux-swarm" ;;
    esac
}

# Get platform display name
# Usage: get_platform_name "github"
get_platform_name() {
    case "$1" in
        github) echo "GitHub Actions" ;;
        gitlab) echo "GitLab CI/CD" ;;
        *) echo "Unknown" ;;
    esac
}

# Get deployment target display name
# Usage: get_deployment_name "linux-swarm"
get_deployment_name() {
    case "$1" in
        linux-swarm) echo "Linux Server / Docker Swarm" ;;
        azure-aci) echo "Azure Container Instances" ;;
        azure-appservice) echo "Azure App Service" ;;
        build-only) echo "Build Only (No Deployment)" ;;
        *) echo "Unknown" ;;
    esac
}

# Display configuration summary
# Usage: display_config_summary "github" "linux-swarm"
display_config_summary() {
    local platform="$1"
    local deployment="$2"
    
    echo "" >&2
    echo "📋 Configuration Summary" >&2
    echo "------------------------" >&2
    echo "Platform: $(get_platform_name "$platform")" >&2
    echo "Deployment: $(get_deployment_name "$deployment")" >&2
    echo "" >&2
}
