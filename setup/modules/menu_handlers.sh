#!/bin/bash
#
# menu_handlers.sh
#
# Module for handling menu actions in quick-start script

read_prompt() {
    local prompt="$1"
    local var_name="$2"

    if [[ -r /dev/tty ]]; then
        read -r -p "$prompt" "$var_name" < /dev/tty
    else
        read -r -p "$prompt" "$var_name"
    fi
}

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

open_browser_incognito() {
    local port="$1"
    local compose_file="$2"
    local test_databases="$3"  # Optional: "test" to indicate test databases mode

    local api_url="http://localhost:$port/docs"
    local web_port="${WEB_PORT:-}"
    if [ -z "$web_port" ] && [ -f ".env" ]; then
        web_port=$(grep "^WEB_PORT=" .env 2>/dev/null | head -n1 | cut -d'=' -f2- | tr -d ' "')
    fi
    web_port="${web_port:-8086}"

    local gui_url="http://localhost:${web_port}/"
    local neo4j_url="http://localhost:7474"
    local urls=("$gui_url" "$api_url")

    if [[ "$compose_file" == *neo4j* ]]; then
        urls+=("$neo4j_url")
        echo "Neo4j Browser will open at $neo4j_url using the same private window."
    fi

    # Add test database admin UIs if in test mode
    if [[ "$test_databases" == "test" ]]; then
        urls+=("http://localhost:5050")  # pgAdmin
        urls+=("http://localhost:8080")  # phpMyAdmin
        urls+=("http://localhost:7475/browser?connectURL=neo4j://localhost:7688")  # Neo4j Browser (test)
        urls+=("http://localhost:8082/")  # Adminer
        urls+=("http://localhost:8085/")  # Adminer (SQLite)
        urls+=("http://localhost:8084")  # SQLite Web
        
        # Check if we're on macOS ARM64 (no SQLite Browser GUI)
        local sqlite_browser_note=""
        if [[ "$(uname)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
            sqlite_browser_note="  - SQLite Browser (GUI): not available on ARM64"
        else
            urls+=("http://localhost:8090")  # SQLite Browser (GUI) - Windows/Linux only
            sqlite_browser_note="  - SQLite Browser (GUI): http://localhost:8090"
        fi
        
        echo ""
        echo "🌐 Opening browser with all admin UIs:"
        echo "  - Backup Manager: $gui_url"
        echo "  - API Docs: $api_url"
        echo "  - pgAdmin: http://localhost:5050"
        echo "  - phpMyAdmin: http://localhost:8080"
        echo "  - Neo4j Browser: http://localhost:7475"
        echo "  - Adminer: http://localhost:8082"
        echo "  - Adminer (SQLite): http://localhost:8085"
        echo "  - SQLite Web: http://localhost:8084"
        echo "$sqlite_browser_note"
    fi

    # Add admin UIs if in admin mode
    if [[ "$test_databases" == "admin" ]]; then
        if [[ "$compose_file" == *postgres* ]]; then
            urls+=("http://localhost:5051")  # pgAdmin for app's postgres
        fi
        if [[ "$compose_file" == *neo4j* ]]; then
            urls+=("http://localhost:7474")  # Neo4j Browser (app's)
        fi
        
        echo ""
        echo "🌐 Opening browser with admin UIs:"
        echo "  - Backup Manager: $gui_url"
        echo "  - API Docs: $api_url"
        if [[ "$compose_file" == *postgres* ]]; then
            echo "  - pgAdmin (app DB): http://localhost:5051"
        fi
        if [[ "$compose_file" == *neo4j* ]]; then
            echo "  - Neo4j Browser: http://localhost:7474"
        fi
    fi

    echo "Opening browser..."

    local profile_base="${TMPDIR:-/tmp}"
    local edge_profile="${profile_base}/edge_incog_profile_backup_restore"
    local chrome_profile="${profile_base}/chrome_incog_profile_backup_restore"
    mkdir -p "$edge_profile" "$chrome_profile"

    # Best-effort: close prior windows using this profile so only fresh tabs remain
    stop_incognito_profile_procs() {
        local profile_dir="$1"; shift || true
        [ -z "$profile_dir" ] && return 0
        [ $# -eq 0 ] && return 0
        
        # Kill all browser processes using this profile
        for pname in "$@"; do
            # Find processes using the profile directory
            pkill -f "$pname.*--user-data-dir=$profile_dir" >/dev/null 2>&1 || true
            pkill -f "$pname.*--profile-directory=$profile_dir" >/dev/null 2>&1 || true
            
            # Also kill any processes that might be using temp directories
            pkill -f "$pname.*backup_restore" >/dev/null 2>&1 || true
        done
        
        # Wait a moment for processes to die
        sleep 1
        
        # Force kill any remaining processes
        for pname in "$@"; do
            pkill -9 -f "$pname.*--user-data-dir=$profile_dir" >/dev/null 2>&1 || true
            pkill -9 -f "$pname.*--profile-directory=$profile_dir" >/dev/null 2>&1 || true
        done
    }

    # Always restart browser processes for clean state
    stop_incognito_profile_procs "$edge_profile" "microsoft-edge"
    stop_incognito_profile_procs "$chrome_profile" "chrome" "google-chrome"
    
    # Additional cleanup for any Chrome/Edge processes with backup_restore in args
    pkill -f "chrome.*backup_restore" >/dev/null 2>&1 || true
    pkill -f "edge.*backup_restore" >/dev/null 2>&1 || true
    
    # Remove profile directories to ensure clean start
    rm -rf "$edge_profile" "$chrome_profile" 2>/dev/null || true
    mkdir -p "$edge_profile" "$chrome_profile"

    if command -v microsoft-edge &> /dev/null; then
        microsoft-edge --inprivate --user-data-dir="$edge_profile" "${urls[@]}" >/dev/null 2>&1 &
        return
    fi

    if command -v google-chrome &> /dev/null; then
        google-chrome --incognito --user-data-dir="$chrome_profile" "${urls[@]}" >/dev/null 2>&1 &
        return
    fi

    if command -v chromium-browser &> /dev/null; then
        # For chromium, we can't easily manage profiles, so just open normally
        chromium-browser --incognito "${urls[@]}" >/dev/null 2>&1 &
        return
    fi

    if command -v open &> /dev/null; then
        # macOS: Try Chrome first, then Safari, then default
        open -na "Google Chrome" --args --incognito --user-data-dir="$chrome_profile" "${urls[@]}" 2>/dev/null || \
        open -na "Safari" --args --private "${urls[@]}" 2>/dev/null || \
        open "${urls[0]}"
        return
    fi

    if command -v xdg-open &> /dev/null; then
        # Linux: Open each URL (may open in different browsers)
        for url in "${urls[@]}"; do
            xdg-open "$url" &
        done
    else
        echo "Could not detect browser command. Please open manually: $api_url"
        if [[ "$compose_file" == *neo4j* ]]; then
            echo "Neo4j Browser: $neo4j_url"
        fi
    fi
}

handle_backend_start() {
    local port="$1"
    local compose_file="$2"
    
    echo "🚀 Starting Backend with Database..."
    echo ""
    echo "========================================"
    echo "  Services starting:"
    echo "  - Backend API (port $port)"
    echo "  - PostgreSQL database"
    local web_port="${WEB_PORT:-}"
    if [ -z "$web_port" ] && [ -f ".env" ]; then
        web_port=$(grep "^WEB_PORT=" .env 2>/dev/null | head -n1 | cut -d'=' -f2- | tr -d ' "')
    fi
    web_port="${web_port:-8086}"
    echo "  - Web GUI at http://localhost:${web_port}/"
    echo "========================================"
    echo ""
    echo "🌐 Browser will open automatically when API is ready..."
    echo ""
    
    # Start browser opening in background
    show_api_docs_delayed "$port" "120"
    
    echo ""
    docker compose --env-file .env -f "$compose_file" up --build --no-cache
}

handle_dependency_management() {
    echo "📦 Öffne Dependency Management..."
    ./python-dependency-management/scripts/manage-python-project-dependencies.sh
    echo ""
    echo "ℹ️  Dependency Management beendet."
}

handle_dependency_and_backend() {
    local port="$1"
    local compose_file="$2"
    
    echo "📦 Öffne zuerst Dependency Management..."
    ./python-dependency-management/scripts/manage-python-project-dependencies.sh
    echo ""
    echo "🚀 Starte nun das Backend..."
    echo ""
    echo "========================================"
    echo "  API will be accessible at:"
    echo "  http://localhost:$port/docs"
    echo "  Web GUI will be accessible at:"
    local web_port="${WEB_PORT:-}"
    if [ -z "$web_port" ] && [ -f ".env" ]; then
        web_port=$(grep "^WEB_PORT=" .env 2>/dev/null | head -n1 | cut -d'=' -f2- | tr -d ' "')
    fi
    web_port="${web_port:-8086}"
    echo "  http://localhost:${web_port}/"
    echo "========================================"
    echo ""
    echo "🌐 Browser will open automatically when API is ready..."
    echo ""
    
    # Start browser opening in background
    show_api_docs_delayed "$port" "120"
    
    echo ""
    docker compose --env-file .env -f "$compose_file" up --build
}

handle_environment_diagnostics() {
    echo "🔍 Running Docker/build diagnostics..."
    local diagnostics_script="python-dependency-management/scripts/run-docker-build-diagnostics.sh"
    if [ -f "$diagnostics_script" ]; then
        ./$diagnostics_script
    else
        echo "❌ $diagnostics_script not found"
    fi
}

handle_rerun_setup_wizard() {
    echo "🔁 Re-running the interactive setup wizard"
    echo ""
    echo "To launch the wizard again, delete the .setup-complete file and restart quick-start."
    echo "The wizard automatically backs up your current .env before writing a new one."
    echo ""

    if [ ! -f .setup-complete ]; then
        echo ".setup-complete is already missing. The next quick-start run will start the wizard automatically."
    fi

    read_prompt "Delete .setup-complete and restart ./quick-start.sh now? (y/N): " rerun_choice
    if [[ ! "$rerun_choice" =~ ^[Yy]$ ]]; then
        echo "No changes were made. Remove .setup-complete manually and run ./quick-start.sh when you're ready."
        return 1
    fi

    if [ -f .setup-complete ]; then
        rm -f .setup-complete
        echo ".setup-complete removed."
    else
        echo ".setup-complete was not found, continuing."
    fi

    echo "Restarting ./quick-start.sh so you can walk through the wizard again..."
    ./quick-start.sh
    exit $?
}

handle_docker_compose_down() {
    local compose_file="$1"
    
    echo "🛑 Stoppe und entferne Container..."
    echo "   Using compose file: $compose_file"
    echo ""
    docker compose --env-file .env -f "$compose_file" down --remove-orphans
    echo ""
    echo "✅ Container gestoppt und entfernt"
}

handle_backend_start_no_cache() {
    local port="$1"
    local compose_file="$2"
    
    echo "🚀 Starte Backend direkt (mit --no-cache)..."
    echo ""
    echo "========================================"
    echo "  API will be accessible at:"
    echo "  http://localhost:$port/docs"
    echo "========================================"
    echo ""
    echo "🌐 Browser will open automatically when API is ready..."
    echo ""
    
    # Start browser opening in background
    show_api_docs_delayed "$port" "120"
    
    echo ""
    docker compose --env-file .env -f "$compose_file" build --no-cache
    docker compose --env-file .env -f "$compose_file" up
}

handle_build_production_image() {
    echo "🏗️  Building production Docker image..."
    echo ""
    if [ -f "build-image/docker-compose.build.yml" ]; then
        docker compose -f build-image/docker-compose.build.yml run --rm build-image
    else
        echo "❌ build-image/docker-compose.build.yml not found"
        echo "⚠️  Please ensure the build-image directory exists"
    fi
}

handle_cicd_setup() {
    echo "🚀 CI/CD Pipeline einrichten..."
    echo ""
    if [ -f "ci-cd/docker-compose.cicd-setup.yml" ]; then
        docker compose -f ci-cd/docker-compose.cicd-setup.yml run --rm cicd-setup
    else
        echo "❌ ci-cd/docker-compose.cicd-setup.yml not found"
        echo "⚠️  Please ensure the ci-cd directory exists"
    fi
}

handle_open_backup_gui() {
    local port="$1"
    echo "🌐 Opening Backup Manager GUI..."
    echo ""
    local web_port="${WEB_PORT:-}"
    if [ -z "$web_port" ] && [ -f ".env" ]; then
        web_port=$(grep "^WEB_PORT=" .env 2>/dev/null | head -n1 | cut -d'=' -f2- | tr -d ' "')
    fi
    web_port="${web_port:-8086}"

    echo "   URL: http://localhost:${web_port}/"
    echo ""
    
    local url="http://localhost:${web_port}/"
    
    if command -v open &> /dev/null; then
        open "$url"
    elif command -v xdg-open &> /dev/null; then
        xdg-open "$url" &
    else
        echo "Please open $url in your browser"
    fi
}

handle_run_backup_now() {
    local port="$1"
    echo "⚡ Run Backup Now"
    echo ""
    
    # Check if API is running
    if ! curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "❌ API is not running. Please start the backend first."
        return 1
    fi
    
    local access_token
    access_token=$(get_keycloak_access_token)
    if [ -z "$access_token" ]; then
        echo "❌ Missing Keycloak access token."
        return 1
    fi
    
    # List schedules
    echo "📋 Fetching schedules..."
    local schedules_response
    schedules_response=$(curl -s -H "Authorization: Bearer $access_token" "http://localhost:$port/automation/schedules")
    
    if echo "$schedules_response" | grep -q "detail"; then
        echo "❌ Failed to fetch schedules. Check your access token."
        return 1
    fi
    
    echo ""
    echo "Available schedules:"
    echo "$schedules_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data:
        print('  No schedules configured. Use the web GUI to create one.')
    else:
        for i, s in enumerate(data, 1):
            print(f\"  {i}) {s.get('name', 'Unknown')} (ID: {s.get('id', 'N/A')[:8]}...)\")
except:
    print('  Error parsing response')
"
    
    echo ""
    read_prompt "Enter schedule number to run (or 'q' to cancel): " schedule_choice
    
    if [ "$schedule_choice" = "q" ]; then
        echo "Cancelled."
        return 0
    fi
    
    # Get schedule ID
    local schedule_id
    schedule_id=$(echo "$schedules_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    idx = int('$schedule_choice') - 1
    if 0 <= idx < len(data):
        print(data[idx].get('id', ''))
except:
    pass
")
    
    if [ -z "$schedule_id" ]; then
        echo "❌ Invalid selection."
        return 1
    fi
    
    echo ""
    echo "🚀 Running backup..."
    local result
    result=$(curl -s -X POST -H "Authorization: Bearer $access_token" \
        "http://localhost:$port/automation/schedules/$schedule_id/run-now")
    
    if echo "$result" | grep -q "backup_filename"; then
        echo "✅ Backup completed successfully!"
        echo "$result" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"   Filename: {data.get('backup_filename', 'N/A')}\")
except:
    pass
"
    else
        echo "❌ Backup failed:"
        echo "$result"
    fi
}

handle_list_backups() {
    local port="$1"
    echo "📁 List Backup Files"
    echo ""
    
    # Check if API is running
    if ! curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "❌ API is not running. Please start the backend first."
        return 1
    fi
    
    local access_token
    access_token=$(get_keycloak_access_token)
    if [ -z "$access_token" ]; then
        echo "❌ Missing Keycloak access token."
        return 1
    fi

    echo "📋 Fetching backup files..."
    local response
    response=$(curl -s -H "Authorization: Bearer $access_token" "http://localhost:$port/backup/list")
    
    echo ""
    echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    files = data.get('files', [])
    if not files:
        print('  No backup files found.')
    else:
        print(f'  Found {len(files)} backup(s):')
        print('')
        for f in files:
            print(f\"  - {f.get('filename', 'Unknown')}\")
            print(f\"    Size: {f.get('size_mb', 'N/A')} MB | Created: {f.get('created_at', 'N/A')}\")
except Exception as e:
    print(f'  Error: {e}')
"
}

handle_start_with_test_databases() {
    local port="$1"
    local compose_file="$2"
    
    echo "🧪 Starting with Test Databases..."
    echo ""
    echo "========================================"
    echo "  Services starting:"
    echo "  - Backend API (port $port)"
    echo "  - App's database (PostgreSQL or Neo4j)"
    echo "  - Backup runner"
    echo ""
    echo "  Test Databases:"
    echo "  - PostgreSQL (port 5434)"
    echo "  - MySQL (port 3306)"
    echo "  - Neo4j (bolt: 7688, http: 7475)"
    echo ""
    echo "  Admin UIs:"
    echo "  - pgAdmin: http://localhost:5050"
    echo "  - phpMyAdmin: http://localhost:8080"
    echo "  - Neo4j Browser: http://localhost:7475"
    echo "  - Adminer: http://localhost:8082"
    echo "  - Adminer (SQLite): http://localhost:8085"
    echo "  - SQLite Web: http://localhost:8084"
    if [[ "$(uname)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
        echo "  - SQLite Browser (GUI): not available on ARM64"
    else
        echo "  - SQLite Browser (GUI): http://localhost:8090"
    fi
    echo "========================================"
    echo ""
    
    # Detect OS and choose appropriate test databases compose file
    local test_db_file="local-deployment/docker-compose.test-databases.yml"
    if [[ "$(uname)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
        test_db_file="local-deployment/docker-compose.test-databases.mac.yml"
        echo "🍎 Detected macOS ARM64, using ARM64-compatible test databases"
    fi
    
    local runner_file="local-deployment/docker-compose.runner.yml"
    local keycloak_enabled="false"
    local keycloak_url=""
    
    # Detect macOS ARM64 and use compatible compose file
    if [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
        local macos_test_db_file="local-deployment/docker-compose.test-databases-macos.yml"
        if [ -f "$macos_test_db_file" ]; then
            echo "🍎 Detected macOS ARM64 - using ARM64-compatible images"
            test_db_file="$macos_test_db_file"
        else
            echo "⚠️  macOS ARM64 detected but no compatible compose file found."
            echo "   Some images may fail to pull. Falling back to default."
        fi
    fi
    
    # Read KEYCLOAK_ENABLED from .env file (not shell environment)
    if [ -f ".env" ]; then
        keycloak_enabled=$(grep "^KEYCLOAK_ENABLED=" .env 2>/dev/null | head -n1 | cut -d'=' -f2- | tr -d ' "' | tr '[:upper:]' '[:lower:]')
        keycloak_url=$(grep "^KEYCLOAK_URL=" .env 2>/dev/null | head -n1 | cut -d'=' -f2- | tr -d ' "')
    fi
    
    if [ "$keycloak_enabled" = "true" ]; then
        keycloak_url="${keycloak_url:-http://localhost:9090}"
        if ! curl -s --connect-timeout 5 "$keycloak_url/" >/dev/null 2>&1; then
            echo ""
            echo "⚠️  KEYCLOAK_ENABLED=true but Keycloak is not reachable at $keycloak_url"
            echo "   Start Keycloak from the dedicated repo before logging in:"
            echo "   https://github.com/Sokrates1989/keycloak.git"
            echo ""
        fi
    fi
    
    if [ ! -f "$test_db_file" ]; then
        echo "❌ Test databases compose file not found: $test_db_file"
        return 1
    fi
    
    if [ ! -f "$runner_file" ]; then
        echo "❌ Runner compose file not found: $runner_file"
        return 1
    fi
    
    echo ""
    echo "🐳 Starting all services with test databases..."

    local project_root
    project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local log_dir="$project_root/logs/test-databases/$timestamp"
    mkdir -p "$log_dir"
    local compose_log_file="$log_dir/docker-compose.log"
    : > "$compose_log_file"
    echo "[LOG] Docker compose output will be written to: $compose_log_file"
    echo "[LOG] Live terminal output is disabled. Tail the log file if needed."

    # Start browser opener in background
    (
        local max_wait=120
        local wait_time=0
        while [ $wait_time -lt $max_wait ]; do
            if curl -s "http://localhost:$port/health" >/dev/null 2>&1; then
                break
            fi
            sleep 2
            wait_time=$((wait_time + 2))
        done

        open_browser_incognito "$port" "$compose_file" "test"
    ) &
    local browser_pid=$!

    cd "$project_root" || return 1
    
    # Use 'up --watch' to show logs AND watch for file changes (not 'watch' which only shows sync events)
    docker compose --ansi never --progress plain --env-file .env -f "$compose_file" -f "$runner_file" -f "$test_db_file" up --build --watch > "$compose_log_file" 2>&1

    kill "$browser_pid" >/dev/null 2>&1 || true
    wait "$browser_pid" >/dev/null 2>&1 || true
}

handle_start_admin_uis() {
    local port="$1"
    local compose_file="$2"
    
    echo "🖥️  Starting Admin UIs..."
    echo ""
    echo "========================================"
    echo "  Services starting:"
    echo "  - Backend API (port $port)"
    echo "  - App's database"
    echo ""
    echo "  Admin UIs:"
    if [[ "$compose_file" == *postgres* ]]; then
        echo "  - pgAdmin (app DB): http://localhost:5051"
    fi
    if [[ "$compose_file" == *neo4j* ]]; then
        echo "  - Neo4j Browser: http://localhost:7474"
    fi
    echo "========================================"
    echo ""
    
    local runner_file="local-deployment/docker-compose.runner.yml"
    
    if [ ! -f "$runner_file" ]; then
        echo "❌ Runner compose file not found: $runner_file"
        return 1
    fi
    
    echo ""
    echo "🐳 Starting services with admin profile (watch mode)..."

    (
        local max_wait=120
        local wait_time=0
        while [ $wait_time -lt $max_wait ]; do
            if curl -s "http://localhost:$port/health" >/dev/null 2>&1; then
                break
            fi
            sleep 2
            wait_time=$((wait_time + 2))
        done

        open_browser_incognito "$port" "$compose_file" "admin"
    ) &
    
    docker compose --env-file .env -f "$compose_file" -f "$runner_file" --profile admin up --build --watch
}

handle_clean_test_data() {
    echo "🧹 Cleaning Test Database Data..."
    echo ""
    echo "This will remove all test database data and configurations:"
    echo "  - Test PostgreSQL data"
    echo "  - Test MySQL data"
    echo "  - Test Neo4j data and logs"
    echo "  - Test SQLite data"
    echo "  - pgAdmin configuration"
    echo ""
    
    read_prompt "Are you sure you want to continue? (y/N): " confirm
    
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        echo ""
        echo "🗑️  Removing test database data..."
        
        # Remove test database data directories
        rm -rf .docker/test-*
        rm -rf .docker/pgadmin-data
        
        echo "✅ Test database data cleaned successfully!"
        echo ""
        echo "Next time you start with test databases, fresh databases will be created."
    else
        echo ""
        echo "❌ Cleanup cancelled."
    fi
}

handle_deploy_all_services() {
    local port="$1"
    local compose_file="$2"
    
    echo "🚀 Starting all services..."
    echo ""
    echo "========================================"
    echo "  Services starting:"
    echo "  - Backend API (port $port)"
    echo "  - PostgreSQL database"
    echo "  - Backup runner"
    local web_port="${WEB_PORT:-}"
    if [ -z "$web_port" ] && [ -f ".env" ]; then
        web_port=$(grep "^WEB_PORT=" .env 2>/dev/null | head -n1 | cut -d'=' -f2- | tr -d ' \"')
    fi
    web_port="${web_port:-8086}"
    echo "  - Web GUI at http://localhost:${web_port}/"
    echo "========================================"
    echo ""
    echo "🌐 Browser will open automatically when API is ready..."
    echo ""
    
    # Start browser opening in background
    show_api_docs_delayed "$port" "120"
    
    # Check if runner compose file exists
    local runner_file="local-deployment/docker-compose.runner.yml"
    if [ ! -f "$runner_file" ]; then
        echo "❌ Runner compose file not found: $runner_file"
        return 1
    fi
    
    echo ""
    echo "🐳 Starting services (watch mode)..."
    docker compose --env-file .env -f "$compose_file" -f "$runner_file" up --build --watch
    
    echo ""
    echo "✅ All services started!"
}

handle_deploy_all_services_detached() {
    local port="$1"
    local compose_file="$2"
    
    echo "🚀 Starting all services (detached)..."
    echo ""
    echo "========================================"
    echo "  Services starting (detached):"
    echo "  - Backend API (port $port)"
    echo "  - PostgreSQL database"
    echo "  - Backup runner"
    local web_port="${WEB_PORT:-}"
    if [ -z "$web_port" ] && [ -f ".env" ]; then
        web_port=$(grep "^WEB_PORT=" .env 2>/dev/null | head -n1 | cut -d'=' -f2- | tr -d ' \"')
    fi
    web_port="${web_port:-8086}"
    echo "  - Web GUI at http://localhost:${web_port}/"
    echo "========================================"
    echo ""
    echo "🌐 Browser will open automatically when API is ready..."
    echo ""
    
    # Start browser opening in background
    show_api_docs_delayed "$port" "120"
    
    # Check if runner compose file exists
    local runner_file="local-deployment/docker-compose.runner.yml"
    if [ ! -f "$runner_file" ]; then
        echo "❌ Runner compose file not found: $runner_file"
        return 1
    fi
    
    echo ""
    echo "🐳 Starting services in detached mode..."
    docker compose --env-file .env -f "$compose_file" -f "$runner_file" up --build -d
    
    echo ""
    echo "✅ All services started in detached mode!"
    echo ""
    echo "To view logs: docker compose -f $compose_file -f $runner_file logs -f"
    echo "To stop services: docker compose -f $compose_file -f $runner_file down"
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
    echo "   - backup:read      (view backups, stats)"
    echo "   - backup:create    (manual backup runs)"
    echo "   - backup:run       (run scheduled/manual backups)"
    echo "   - backup:configure (configure targets/destinations/schedules)"
    echo "   - backup:restore   (restore backups - CRITICAL)"
    echo "   - backup:delete    (delete backups)"
    echo "   - backup:admin     (full access)"
    echo ""
    
    read_prompt "Create default users (admin/operator/viewer)? (Y/n): " use_defaults
    local user_args=""
    if [[ ! "$use_defaults" =~ ^[Nn]$ ]]; then
        user_args="--user admin:admin:backup:admin --user operator:operator:backup:read,backup:create,backup:run,backup:restore --user viewer:viewer:backup:read"
    else
        echo "Role format: backup:read, backup:create, backup:run, backup:configure, backup:restore, backup:delete, backup:admin"
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

show_main_menu() {
    local port="$1"
    local compose_file="$2"

    local summary_msg=""
    local exit_code=0
    local choice

    while true; do
        local MENU_NEXT=1
        local MENU_RUN_START=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))
        local MENU_RUN_START_DETACHED=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))

        local MENU_MONITOR_LOGS=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))

        local MENU_MAINT_DOWN=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))
        local MENU_MAINT_DB_REINSTALL=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))

        local MENU_BUILD_IMAGE=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))

        local MENU_RUN_BACKUP=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))
        local MENU_LIST_BACKUPS=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))

        local MENU_TEST_DBS=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))
        local MENU_TEST_DBS_ADMIN=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))
        local MENU_CLEAN_TEST_DATA=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))

        local MENU_SETUP=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))
        local MENU_KEYCLOAK_BOOTSTRAP=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))

        local MENU_EXIT=$MENU_NEXT

        echo ""
        echo "================ Main Menu ================"
        echo ""
        echo "Run:"
        echo "  ${MENU_RUN_START}) Start all services"
        echo "  ${MENU_RUN_START_DETACHED}) Start all services (detached)"
        echo ""
        echo "Monitoring:"
        echo "  ${MENU_MONITOR_LOGS}) View logs"
        echo ""
        echo "Maintenance:"
        echo "  ${MENU_MAINT_DOWN}) Docker Compose Down (stop containers)"
        echo "  ${MENU_MAINT_DB_REINSTALL}) DB Re-Install (reset database volume)"
        echo ""
        echo "Build:"
        echo "  ${MENU_BUILD_IMAGE}) Build Production Docker Image (API + Web)"
        echo ""
        echo "Backup Automation:"
        echo "  ${MENU_RUN_BACKUP}) Run backup now (CLI)"
        echo "  ${MENU_LIST_BACKUPS}) List backup files"
        echo ""
        echo "Testing (all DB types + admin UIs):"
        echo "  ${MENU_TEST_DBS}) Start with test databases"
        echo "  ${MENU_TEST_DBS_ADMIN}) Start with admin UIs only"
        echo "  ${MENU_CLEAN_TEST_DATA}) Clean test database data"
        echo ""
        echo "Setup:"
        echo "  ${MENU_SETUP}) Re-run setup wizard"
        echo "  ${MENU_KEYCLOAK_BOOTSTRAP}) Bootstrap Keycloak (realm, roles, users)"
        echo ""
        echo "  ${MENU_EXIT}) Exit"
        echo ""

        read_prompt "Deine Wahl (1-${MENU_EXIT}): " choice

        case $choice in
          ${MENU_RUN_START})
            handle_deploy_all_services "$port" "$compose_file"
            summary_msg="All services started"
            break
            ;;
          ${MENU_RUN_START_DETACHED})
            handle_deploy_all_services_detached "$port" "$compose_file"
            summary_msg="All services started (detached)"
            break
            ;;
          ${MENU_MONITOR_LOGS})
            handle_view_logs "$compose_file"
            summary_msg="Logs displayed"
            ;;
          ${MENU_MAINT_DOWN})
            handle_docker_compose_down "$compose_file"
            summary_msg="Docker Compose Down ausgeführt"
            ;;
          ${MENU_MAINT_DB_REINSTALL})
            handle_db_reinstall "$compose_file"
            summary_msg="Database reinstalled"
            ;;
          ${MENU_BUILD_IMAGE})
            handle_build_production_image
            summary_msg="Production Docker Image Build ausgeführt"
            ;;
          ${MENU_RUN_BACKUP})
            handle_run_backup_now "$port"
            summary_msg="Backup operation completed"
            ;;
          ${MENU_LIST_BACKUPS})
            handle_list_backups "$port"
            summary_msg="Backup list displayed"
            ;;
          ${MENU_TEST_DBS})
            handle_start_with_test_databases "$port" "$compose_file"
            summary_msg="Test databases started"
            break
            ;;
          ${MENU_TEST_DBS_ADMIN})
            handle_start_admin_uis "$port" "$compose_file"
            summary_msg="Admin UIs started"
            break
            ;;
          ${MENU_CLEAN_TEST_DATA})
            handle_clean_test_data
            summary_msg="Test data cleaned"
            ;;
          ${MENU_SETUP})
            handle_rerun_setup_wizard
            summary_msg="Setup wizard restarted"
            ;;
          ${MENU_KEYCLOAK_BOOTSTRAP})
            handle_keycloak_bootstrap
            summary_msg="Keycloak bootstrap completed"
            ;;
          ${MENU_EXIT})
            echo "👋 Skript wird beendet."
            exit 0
            ;;
          *)
            echo "❌ Ungültige Auswahl. Bitte erneut versuchen."
            echo ""
            continue
            ;;
        esac
    done

    echo ""
    if [ -n "$summary_msg" ]; then
        echo "✅ $summary_msg"
    fi
    echo "ℹ️  Quick-Start beendet. Für weitere Aktionen bitte erneut aufrufen."
    echo ""
    exit $exit_code
}
