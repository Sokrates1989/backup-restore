#!/bin/bash
# Deployment configuration module
# Collects deployment-specific settings

# Configure Linux/Swarm deployment
# Returns: path|stack_name (pipe-separated)
configure_linux_deployment() {
    # section_header "STEP 3: Linux Server Configuration"
    
    # echo "We no longer collect server details here." >&2
    # echo "During the secrets step you'll document your SSH settings, deployment path, and stack name." >&2
    # echo "Make sure you know where your stack lives and which name you used when deploying." >&2
    # echo "" >&2
    # success_message "Server details will be handled during the secrets walkthrough"
    
    # Return empty placeholders to keep interface consistent
    echo "|"
}

# Configure Azure ACI deployment
# Returns: resource_group|container_name|location (pipe-separated)
configure_azure_aci_deployment() {
    section_header "STEP 3: Azure Container Instances Configuration"
    
    echo "Configure your Azure ACI settings:" >&2
    echo "" >&2
    
    local rg=$(prompt_text "Azure Resource Group name" "")
    while [ -z "$rg" ]; do
        error_message "Resource Group cannot be empty"
        rg=$(prompt_text "Azure Resource Group name" "")
    done
    
    local container=$(prompt_text "Azure Container Instance name" "")
    while [ -z "$container" ]; do
        error_message "Container name cannot be empty"
        container=$(prompt_text "Azure Container Instance name" "")
    done
    
    local location=$(prompt_text "Azure location" "westeurope")
    
    echo "" >&2
    success_message "Azure ACI configured"
    echo "  Resource Group: $rg" >&2
    echo "  Container: $container" >&2
    echo "  Location: $location" >&2
    
    echo "$rg|$container|$location"
}

# Configure Azure App Service deployment
# Returns: resource_group|app_name|location (pipe-separated)
configure_azure_appservice_deployment() {
    section_header "STEP 3: Azure App Service Configuration"
    
    echo "Configure your Azure App Service settings:" >&2
    echo "" >&2
    
    local rg=$(prompt_text "Azure Resource Group name" "")
    while [ -z "$rg" ]; do
        error_message "Resource Group cannot be empty"
        rg=$(prompt_text "Azure Resource Group name" "")
    done
    
    local app=$(prompt_text "Azure App Service name" "")
    while [ -z "$app" ]; do
        error_message "App Service name cannot be empty"
        app=$(prompt_text "Azure App Service name" "")
    done
    
    local location=$(prompt_text "Azure location" "westeurope")
    
    echo "" >&2
    success_message "Azure App Service configured"
    echo "  Resource Group: $rg" >&2
    echo "  App Service: $app" >&2
    echo "  Location: $location" >&2
    
    echo "$rg|$app|$location"
}

# Get deployment configuration based on target
# Usage: get_deployment_config "linux-swarm"
get_deployment_config() {
    local deployment_target="$1"
    
    case "$deployment_target" in
        linux-swarm)
            configure_linux_deployment
            ;;
        azure-aci)
            configure_azure_aci_deployment
            ;;
        azure-appservice)
            configure_azure_appservice_deployment
            ;;
        build-only)
            echo "|||"  # No deployment config needed
            ;;
        *)
            error_message "Unknown deployment target: $deployment_target"
            return 1
            ;;
    esac
}
