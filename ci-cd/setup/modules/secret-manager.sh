#!/bin/bash
# Secret manager module
# Guides users through creating repository secrets step-by-step

# Guide user through creating secrets
# Usage: guide_secret_creation "platform" "deployment_target" "secrets_url" "deploy_config"
guide_secret_creation() {
    local platform="$1"
    local deployment_target="$2"
    local secrets_url="$3"
    local deploy_config="$4"
    
    section_header "STEP 5: Repository Secrets Configuration"
    
    echo "Now we'll guide you through creating the required secrets in your repository." >&2
    echo "Each secret will be explained with:" >&2
    echo "  - What it's for" >&2
    echo "  - Whether you can use your local value" >&2
    echo "  - Security recommendations" >&2
    echo "" >&2
    
    if [ -n "$secrets_url" ] && [ "$secrets_url" != "none" ]; then
        echo "🔗 Open this URL to add secrets:" >&2
        echo "   $secrets_url" >&2
        echo "" >&2
    fi
    
    wait_for_enter "Press Enter when you're ready to start..."
    
    # Docker registry secrets
    create_docker_secrets "$platform"
    
    # Deployment-specific secrets
    case "$deployment_target" in
        linux-swarm)
            create_linux_secrets "$platform" "$deploy_config"
            ;;
        azure-aci|azure-appservice)
            create_azure_secrets "$platform"
            ;;
    esac
    
    echo "" >&2
    success_message "All secrets configured!"
    echo "" >&2
}

# Create Docker registry secrets
create_docker_secrets() {
    local platform="$1"
    
    section_header "Secret: DOCKER_USERNAME"
    
    echo "This is your Docker registry username." >&2
    echo "" >&2
    echo "📍 Where to find it:" >&2
    echo "   - Docker Hub: Your Docker Hub username" >&2
    echo "   - GitHub Container Registry: Your GitHub username" >&2
    echo "   - GitLab Container Registry: Your GitLab username" >&2
    echo "" >&2
    echo "💡 Can you use your local value?" >&2
    echo "   ✅ YES - This is safe to use from your local environment" >&2
    echo "" >&2
    
    echo "📝 Action Required:" >&2
    echo "   1. Go to your repository secrets page" >&2
    echo "   2. Create a new secret named: DOCKER_USERNAME" >&2
    echo "   3. Set the value to your Docker Hub/registry username" >&2
    echo "" >&2
    
    wait_for_enter "Press Enter when you've created DOCKER_USERNAME..."
    success_message "DOCKER_USERNAME configured"
    
    # Docker password
    section_header "Secret: DOCKER_PASSWORD"
    
    echo "This is your Docker registry password or access token." >&2
    echo "" >&2
    echo "🔒 Security Recommendation:" >&2
    echo "   ⚠️  DO NOT use your actual password!" >&2
    echo "   ✅ Use an access token instead" >&2
    echo "" >&2
    echo "📍 How to create an access token:" >&2
    echo "   - Docker Hub: https://hub.docker.com/settings/security" >&2
    echo "   - GitHub: https://github.com/settings/tokens (with write:packages scope)" >&2
    echo "   - GitLab: https://gitlab.com/-/profile/personal_access_tokens" >&2
    echo "" >&2
    echo "💡 Can you use your local value?" >&2
    echo "   ⚠️  NO - Generate a new token specifically for CI/CD" >&2
    echo "" >&2
    
    echo "📝 Action Required:" >&2
    echo "   1. Create a new access token (see URLs above)" >&2
    echo "   2. Go to your repository secrets page" >&2
    echo "   3. Create a new secret named: DOCKER_PASSWORD" >&2
    echo "   4. Set the value to your new access token" >&2
    echo "" >&2
    
    wait_for_enter "Press Enter when you've created DOCKER_PASSWORD..."
    success_message "DOCKER_PASSWORD configured"
}

# Create Linux deployment secrets
create_linux_secrets() {
    local platform="$1"
    local deploy_config="$2"
    
    IFS='|' read -r _ _ <<< "$deploy_config"  # compatibility with previous return value
    
    local configured_ssh_user=""
    
    # SSH private key
    section_header "Secret: SSH_PRIVATE_KEY"
    echo "This is the SSH private key dedicated to CI/CD deployments." >&2
    echo "" >&2
    echo "💡 Security Guidance" >&2
    echo "   - Generate a fresh key pair: ssh-keygen -t ed25519 -C 'ci-cd-deploy' -f ~/.ssh/cicd_deploy" >&2
    echo "   - Add the public key to the server: ssh-copy-id -i ~/.ssh/cicd_deploy.pub <user>@<server>" >&2
    echo "   - Test access: ssh -i ~/.ssh/cicd_deploy <user>@<server>" >&2
    echo "" >&2
    echo "📝 Action Required:" >&2
    echo "   1. Create / verify the dedicated CI/CD SSH key" >&2
    echo "   2. Copy the PRIVATE key content (cat ~/.ssh/cicd_deploy)" >&2
    echo "   3. Create repository secret: SSH_PRIVATE_KEY" >&2
    echo "   4. Paste the full key (including BEGIN/END lines)" >&2
    echo "" >&2
    wait_for_enter "Press Enter when you've created SSH_PRIVATE_KEY..."
    success_message "SSH_PRIVATE_KEY configured"

    # SSH host
    section_header "Secret: SSH_HOST"
    echo "This is the DNS name or public IP address reachable from the internet." >&2
    echo "" >&2
    echo "🛠️ How to find it:" >&2
    echo "   - Prefer DNS: e.g. api.example.com" >&2
    echo "   - Or use the public IP (check your hosting provider or run: curl ifconfig.me)" >&2
    echo "" >&2
    echo "📝 Action Required:" >&2
    echo "   1. Determine the hostname/IP used for SSH" >&2
    echo "   2. Create repository secret: SSH_HOST" >&2
    echo "   3. Paste the value exactly as you would connect via ssh" >&2
    echo "" >&2
    wait_for_enter "Press Enter when you've created SSH_HOST..."
    success_message "SSH_HOST configured"

    # SSH user
    section_header "Secret: SSH_USER"
    echo "This is the server user account used for deployment." >&2
    echo "Ensure this user can run docker commands (e.g. part of the docker group)." >&2
    echo "" >&2
    echo "We'll use this value later to generate the required chown/chmod commands." >&2
    echo "" >&2
    local ssh_user_value=$(prompt_text "Enter the deployment username you'll store in SSH_USER" "deploy")
    configured_ssh_user="$ssh_user_value"
    echo "" >&2
    echo "📝 Action Required:" >&2
    echo "   1. Decide which user performs deployments (e.g. deploy)" >&2
    echo "   2. Create repository secret: SSH_USER" >&2
    echo "   3. Set the value to: $ssh_user_value" >&2
    echo "" >&2
    wait_for_enter "Press Enter when you've created SSH_USER..."
    success_message "SSH_USER configured"
    
    # SSH port
    section_header "Secret: SSH_PORT"
    echo "This is the TCP port exposed for SSH (defaults to 22)." >&2
    echo "" >&2
    echo "🛠️ How to confirm:" >&2
    echo "   - Check your firewall / hosting panel" >&2
    echo "   - On the server: sudo ss -tnlp | grep ssh" >&2
    echo "" >&2
    echo "📝 Action Required:" >&2
    echo "   1. Confirm the SSH port" >&2
    echo "   2. Create repository secret: SSH_PORT" >&2
    echo "   3. Enter the port number (e.g. 22)" >&2
    echo "" >&2
    wait_for_enter "Press Enter when you've created SSH_PORT..."
    success_message "SSH_PORT configured"

    # Now create all repository variables
    section_header "📋 Repository Variables Configuration"
    echo "Now we'll create repository variables (non-sensitive configuration)." >&2
    echo "" >&2
    wait_for_enter "Press Enter to continue..."
    
    # IMAGE_NAME variable
    section_header "Repository Variable: IMAGE_NAME"
    echo "This variable tells the pipeline which Docker image to build and push." >&2
    echo "" >&2
    local suggested_image_name="${IMAGE_NAME:-your-docker-namespace/your-image}"
    echo "📍 Where to find it:" >&2
    echo "   - Check your local .env (IMAGE_NAME=$suggested_image_name)" >&2
    echo "   - Confirm the repository in Docker Hub / GHCR matches" >&2
    echo "" >&2
    echo "📝 Action Required:" >&2
    if [ "$platform" = "github" ]; then
        echo "   1. Open: Settings → Secrets and variables → Actions → Variables" >&2
        echo "      (URL: https://github.com/<owner>/<repo>/settings/variables/actions )" >&2
    else
        echo "   1. Open your CI/CD variables management page" >&2
    fi
    echo "   2. Create a variable named: IMAGE_NAME" >&2
    echo "   3. Set the value to your full image reference (e.g. $suggested_image_name)" >&2
    echo "" >&2
    wait_for_enter "Press Enter when you've created the IMAGE_NAME variable..."
    success_message "IMAGE_NAME repository variable configured"
    
    # Deployment path variable
    section_header "Repository Variable: DEPLOY_PATH"
    echo "This variable holds the absolute path to your deployment directory on the server." >&2
    echo "" >&2
    echo "🛠️ How to find it:" >&2
    echo "   - SSH into the server" >&2
    echo "   - cd to the directory hosting your stack" >&2
    echo "   - Run: pwd (copy the output)" >&2
    echo "" >&2
    echo "We'll reuse this path to generate chown/chmod commands in the next steps." >&2
    echo "" >&2

    local deploy_path=$(prompt_text "Enter the deployment path (e.g. /swarm/prod/react/ai-tut)" "")
    
    echo "" >&2
    echo "📝 Action Required:" >&2
    if [ "$platform" = "github" ]; then
        echo "   1. Open: Settings → Secrets and variables → Actions → Variables" >&2
    else
        echo "   1. Open your CI/CD variables management page" >&2
    fi
    echo "   2. Create a variable named: DEPLOY_PATH" >&2
    echo "   3. Set the value to: $deploy_path" >&2
    echo "" >&2
    wait_for_enter "Press Enter when you've created the DEPLOY_PATH variable..."
    success_message "DEPLOY_PATH repository variable configured"
    
    # Deployment directory ownership setup
    section_header "🔧 Server Setup: Directory Permissions"
    echo "The CI/CD pipeline needs to update .env in your deployment directory." >&2
    echo "You must grant ownership to the SSH_USER you configured earlier." >&2
    echo "" >&2

    local ssh_user="$configured_ssh_user"
    if [ -z "$ssh_user" ]; then
        ssh_user=$(prompt_text "Enter the SSH_USER you configured" "deploy")
    fi

    # Extract parent directory and directory name from deploy_path
    local parent_dir=$(dirname "$deploy_path")
    local dir_name=$(basename "$deploy_path")
    
    echo "" >&2
    echo "📝 Action Required (on your server):" >&2
    echo "   1. SSH into your server" >&2
    echo "" >&2
    echo "   2. Navigate to the parent directory:" >&2
    echo "      cd $parent_dir" >&2
    echo "" >&2
    echo "   3. Grant ownership to the deployment user:" >&2
    echo "      sudo chown -R $ssh_user:$ssh_user $dir_name" >&2
    echo "" >&2
    echo "   4. Set appropriate permissions (owner+group read/write/execute):" >&2
    echo "      sudo chmod -R 775 $dir_name" >&2
    echo "" >&2
    echo "   ✅ Verify with: ls -la" >&2
    echo "      Expected output: drwxrwxr-x ... $ssh_user $ssh_user ... $dir_name" >&2
    echo "" >&2
    wait_for_enter "Press Enter when you've set directory permissions..."
    success_message "Directory permissions configured"

    # Stack name variable
    section_header "Repository Variable: STACK_NAME"
    echo "This variable stores the name you pass to docker stack deploy." >&2
    echo "" >&2
    echo "🛠️ How to confirm:" >&2
    echo "   - On the server run: docker stack ls" >&2
    echo "   - Identify the stack handling this API" >&2
    echo "" >&2
    echo "📝 Action Required:" >&2
    if [ "$platform" = "github" ]; then
        echo "   1. Open: Settings → Secrets and variables → Actions → Variables" >&2
    else
        echo "   1. Open your CI/CD variables management page" >&2
    fi
    echo "   2. Create a variable named: STACK_NAME" >&2
    echo "   3. Set the value to the exact stack name (e.g. api-prod)" >&2
    echo "" >&2
    wait_for_enter "Press Enter when you've created the STACK_NAME variable..."
    success_message "STACK_NAME repository variable configured"

    # Stack file variable
    section_header "Repository Variable: STACK_FILE"
    echo "This variable points to the compose file used for docker stack deploy." >&2
    echo "" >&2
    echo "🛠️ How to find it:" >&2
    echo "   - Check your deployment directory for files (ls)." >&2
    echo "   - Common names: docker-stack.yml, swarm-stack.yml" >&2
    echo "" >&2
    echo "📝 Action Required:" >&2
    if [ "$platform" = "github" ]; then
        echo "   1. Open: Settings → Secrets and variables → Actions → Variables" >&2
        echo "   2. Create a variable named: STACK_FILE" >&2
    else
        echo "   1. Open your CI/CD variables management page" >&2
        echo "   2. Create a variable named: STACK_FILE" >&2
    fi
    echo "   3. Set the value to the stack file name (e.g. swarm-stack.yml)" >&2
    echo "" >&2
    wait_for_enter "Press Enter when you've created the STACK_FILE variable..."
    success_message "STACK_FILE repository variable configured"
}

# Create Azure secrets
create_azure_secrets() {
    local platform="$1"
    
    section_header "Secret 3/4: AZURE_CREDENTIALS"
    
    echo "This is your Azure service principal credentials in JSON format." >&2
    echo "" >&2
    echo "💡 Can you use your local Azure credentials?" >&2
    echo "   ⚠️  NO - Create a dedicated service principal for CI/CD" >&2
    echo "" >&2
    echo "📍 How to create Azure service principal:" >&2
    echo "   1. Login: az login" >&2
    echo "   2. Create SP:" >&2
    echo "      az ad sp create-for-rbac \\" >&2
    echo "        --name \"cicd-deploy\" \\" >&2
    echo "        --role contributor \\" >&2
    echo "        --scopes /subscriptions/{subscription-id}/resourceGroups/{resource-group} \\" >&2
    echo "        --sdk-auth" >&2
    echo "" >&2
    echo "📝 Action Required:" >&2
    echo "   1. Run the command above (replace {subscription-id} and {resource-group})" >&2
    echo "   2. Copy the entire JSON output" >&2
    echo "   3. Go to your repository secrets page" >&2
    echo "   4. Create a new secret named: AZURE_CREDENTIALS" >&2
    echo "   5. Paste the JSON output" >&2
    echo "" >&2
    
    wait_for_enter "Press Enter when you've created AZURE_CREDENTIALS..."
    success_message "AZURE_CREDENTIALS configured"
}

# Display environment variable warnings
display_env_warnings() {
    local env_file="$1"
    
    section_header "Environment Variables Review"
    
    echo "⚠️  IMPORTANT: Review your local .env file" >&2
    echo "" >&2
    echo "These values are used locally. You may need different values in production:" >&2
    echo "" >&2
    
    if [ -f "$env_file" ]; then
        # Extract and display key variables with warnings
        local db_url=$(grep "^DATABASE_URL=" "$env_file" | cut -d= -f2-)
        local redis_url=$(grep "^REDIS_URL=" "$env_file" | cut -d= -f2-)
        local debug=$(grep "^DEBUG=" "$env_file" | cut -d= -f2-)
        local admin_key=$(grep "^ADMIN_API_KEY=" "$env_file" | cut -d= -f2-)
        
        echo "  DATABASE_URL=$db_url" >&2
        echo "  ⚠️  Use a production database, not localhost!" >&2
        echo "" >&2
        echo "  REDIS_URL=$redis_url" >&2
        echo "  ⚠️  Use a production Redis instance!" >&2
        echo "" >&2
        echo "  DEBUG=$debug" >&2
        echo "  ⚠️  Should be 'false' in production!" >&2
        echo "" >&2
        echo "  ADMIN_API_KEY=$admin_key" >&2
        echo "  ⚠️  Generate a new secure key for production!" >&2
        echo "" >&2
    fi
    
    echo "💡 Recommendation: Add production environment variables as repository secrets" >&2
    echo "" >&2
}
