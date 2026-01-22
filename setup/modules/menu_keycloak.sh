#!/bin/bash
#
# menu_keycloak.sh
#
# Module for Keycloak-related menu actions
#

# Retrieve a Keycloak access token using client credentials.
get_keycloak_access_token() {
    local access_token="${ACCESS_TOKEN:-}"
    local keycloak_url="${KEYCLOAK_URL:-}"
    local keycloak_realm="${KEYCLOAK_REALM:-}"
    local keycloak_client_id="${KEYCLOAK_CLIENT_ID:-}"
    local keycloak_client_secret="${KEYCLOAK_CLIENT_SECRET:-}"

    if [ -f ".env" ]; then
        keycloak_url=$(grep "^KEYCLOAK_URL=" .env | head -n1 | cut -d'=' -f2- | tr -d ' "')
        keycloak_realm=$(grep "^KEYCLOAK_REALM=" .env | head -n1 | cut -d'=' -f2- | tr -d ' "')
        keycloak_client_id=$(grep "^KEYCLOAK_CLIENT_ID=" .env | head -n1 | cut -d'=' -f2- | tr -d ' "')
        keycloak_client_secret=$(grep "^KEYCLOAK_CLIENT_SECRET=" .env | head -n1 | cut -d'=' -f2- | tr -d ' "')
    fi

    if [ -z "$access_token" ] && [ -n "$keycloak_url" ] && [ -n "$keycloak_realm" ] && [ -n "$keycloak_client_id" ] && [ -n "$keycloak_client_secret" ]; then
        local token_endpoint="${keycloak_url%/}/realms/${keycloak_realm}/protocol/openid-connect/token"
        local token_response
        token_response=$(curl -s -X POST "$token_endpoint" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            -d "grant_type=client_credentials" \
            -d "client_id=$keycloak_client_id" \
            -d "client_secret=$keycloak_client_secret")
        access_token=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" <<< "$token_response")
    fi

    if [ -z "$access_token" ]; then
        read_prompt "Enter Keycloak access token: " access_token
    fi

    echo "$access_token"
}

handle_keycloak_bootstrap() {
    local project_root
    project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    local scripts_dir="$project_root/scripts"
    local bootstrap_image="backup-restore-keycloak-bootstrap"
    
    echo "🔐 Keycloak Bootstrap"
    echo ""
    
    # Load .env defaults
    local keycloak_url="${KEYCLOAK_URL:-http://localhost:9090}"
    local keycloak_realm="${KEYCLOAK_REALM:-backup-restore}"
    if [ -f "$project_root/.env" ]; then
        keycloak_url=$(grep "^KEYCLOAK_URL=" "$project_root/.env" 2>/dev/null | head -n1 | cut -d'=' -f2- | tr -d ' "') || keycloak_url="http://localhost:9090"
        keycloak_realm=$(grep "^KEYCLOAK_REALM=" "$project_root/.env" 2>/dev/null | head -n1 | cut -d'=' -f2- | tr -d ' "') || keycloak_realm="backup-restore"
    fi
    
    # Check if Keycloak is reachable
    echo "🔍 Checking Keycloak at $keycloak_url..."
    if ! curl -s --connect-timeout 5 "$keycloak_url/" >/dev/null 2>&1; then
        echo ""
        echo "❌ Cannot reach Keycloak at $keycloak_url"
        echo ""
        echo "Please ensure Keycloak is running. Start it from the dedicated repo:"
        echo "  https://github.com/Sokrates1989/keycloak.git"
        echo ""
        return 1
    fi
    echo "✅ Keycloak is reachable"
    echo ""
    
    # Check if bootstrap image exists, build if not
    if ! docker image inspect "$bootstrap_image" >/dev/null 2>&1; then
        echo "🐳 Building bootstrap image..."
        docker build -t "$bootstrap_image" "$scripts_dir" || {
            echo "❌ Failed to build bootstrap image"
            return 1
        }
    fi
    
    # Collect configuration
    read_prompt "Keycloak base URL [$keycloak_url]: " input_url
    keycloak_url="${input_url:-$keycloak_url}"
    
    read_prompt "Keycloak admin username [admin]: " admin_user
    admin_user="${admin_user:-admin}"
    
    read_prompt "Keycloak admin password [admin]: " admin_password
    admin_password="${admin_password:-admin}"
    
    read_prompt "Realm name [$keycloak_realm]: " realm
    realm="${realm:-$keycloak_realm}"
    
    read_prompt "Frontend client ID [backup-restore-frontend]: " frontend_client
    frontend_client="${frontend_client:-backup-restore-frontend}"
    
    read_prompt "Backend client ID [backup-restore-backend]: " backend_client
    backend_client="${backend_client:-backup-restore-backend}"
    
    local web_port="${WEB_PORT:-8086}"
    read_prompt "Frontend root URL [http://localhost:$web_port]: " frontend_url
    frontend_url="${frontend_url:-http://localhost:$web_port}"
    
    local api_port="${PORT:-8000}"
    read_prompt "API root URL [http://localhost:$api_port]: " api_url
    api_url="${api_url:-http://localhost:$api_port}"
    
    echo ""
    echo "✅ Creating granular roles:"
    echo "   - backup:read    (view backups, stats)"
    echo "   - backup:create  (create backups)"
    echo "   - backup:restore (restore backups - CRITICAL)"
    echo "   - backup:delete  (delete backups)"
    echo "   - backup:admin   (full access)"
    echo ""
    
    read_prompt "Create default users (admin/operator/viewer)? (Y/n): " use_defaults
    local user_args=""
    if [[ ! "$use_defaults" =~ ^[Nn]$ ]]; then
        user_args="--user admin:admin:backup:admin --user operator:operator:backup:read,backup:create,backup:restore --user viewer:viewer:backup:read"
    else
        echo "Role format: backup:read, backup:create, backup:restore, backup:delete, backup:admin"
        read_prompt "Enter user spec (username:password:role1,role2): " custom_user
        if [ -n "$custom_user" ]; then
            user_args="--user $custom_user"
        fi
    fi
    
    if [ -z "$user_args" ]; then
        echo "❌ No users specified. Aborting bootstrap."
        return 1
    fi
    
    echo ""
    echo "🚀 Bootstrapping Keycloak realm..."
    
    # Run bootstrap in Docker
    # shellcheck disable=SC2086
    docker run --rm --network host "$bootstrap_image" \
        --base-url "$keycloak_url" \
        --admin-user "$admin_user" \
        --admin-password "$admin_password" \
        --realm "$realm" \
        --frontend-client-id "$frontend_client" \
        --backend-client-id "$backend_client" \
        --frontend-root-url "$frontend_url" \
        --api-root-url "$api_url" \
        $user_args
    
    local exit_code=$?
    
    echo ""
    if [ $exit_code -eq 0 ]; then
        echo "✅ Bootstrap complete! Update your .env with the client secret from output above."
    else
        echo "❌ Bootstrap failed. Check Keycloak logs for details."
    fi
    
    return $exit_code
}
