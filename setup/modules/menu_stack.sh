#!/bin/bash
#
# menu_stack.sh
#
# Stack operations module for Backup-Restore quick-start menu.
# This module provides functions for starting, stopping, and managing
# the Docker Compose stack for Backup-Restore.
#
# Author: Auto-generated
# Date: 2026-01-29
# Version: 1.0.0

MENU_STACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${MENU_STACK_DIR}/browser_helpers.sh" ]; then
    source "${MENU_STACK_DIR}/browser_helpers.sh"
fi

get_env_variable() {
    # Get an environment variable from .env file or environment.
    #
    # Args:
    #   $1: variable_name
    #   $2: env_file (default: .env)
    #   $3: default_value
    #
    # Returns:
    #   The variable value or default via stdout.
    local var_name="$1"
    local env_file="${2:-.env}"
    local default_value="${3:-}"
    
    local value="$default_value"
    
    if [ -f "$env_file" ]; then
        local line_value
        line_value=$(grep "^${var_name}=" "$env_file" 2>/dev/null | head -n1 | cut -d'=' -f2- | tr -d ' "')
        if [ -n "$line_value" ]; then
            value="$line_value"
        fi
    fi
    
    echo "$value"
}

handle_backend_start() {
    # Start the backend with database in foreground.
    #
    # Args:
    #   $1: port - API port number.
    #   $2: compose_file - Path to the Docker Compose file.
    local port="$1"
    local compose_file="$2"
    
    echo "🚀 Starting Backend with Database..."
    echo ""
    echo "========================================"
    echo "  Services starting:"
    echo "  - Backend API (port $port)"
    echo "  - PostgreSQL database"
    local web_port
    web_port=$(get_env_variable "WEB_PORT" ".env" "8086")
    echo "  - Web GUI at http://localhost:${web_port}/"
    echo "========================================"
    echo ""
    echo "🌐 Browser will open automatically when API is ready..."
    echo ""
    
    if command -v show_api_docs_delayed >/dev/null 2>&1; then
        show_api_docs_delayed "$port" "120"
    fi
    
    echo ""
    docker compose --env-file .env -f "$compose_file" up --build --no-cache
}

handle_backend_start_no_cache() {
    # Start backend directly with --no-cache build.
    #
    # Args:
    #   $1: port - API port number.
    #   $2: compose_file - Path to the Docker Compose file.
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
    
    if command -v show_api_docs_delayed >/dev/null 2>&1; then
        show_api_docs_delayed "$port" "120"
    fi
    
    echo ""
    docker compose --env-file .env -f "$compose_file" build --no-cache
    docker compose --env-file .env -f "$compose_file" up
}

handle_docker_compose_down() {
    # Stop and remove containers.
    #
    # Args:
    #   $1: compose_file - Path to the Docker Compose file.
    local compose_file="$1"
    
    echo "🛑 Stoppe und entferne Container..."
    echo "   Using compose file: $compose_file"
    echo ""
    docker compose --env-file .env -f "$compose_file" down --remove-orphans
    echo ""
    echo "✅ Container gestoppt und entfernt"
}

handle_deploy_all_services() {
    # Deploy all services (Backend + Runner + GUI).
    #
    # Args:
    #   $1: port - API port number.
    #   $2: compose_file - Path to the Docker Compose file.
    local port="$1"
    local compose_file="$2"
    
    echo "🚀 Starting all services..."
    echo ""
    echo "========================================"
    echo "  Services starting:"
    echo "  - Backend API (port $port)"
    echo "  - PostgreSQL database"
    echo "  - Backup runner"
    local web_port
    web_port=$(get_env_variable "WEB_PORT" ".env" "8086")
    echo "  - Web GUI at http://localhost:${web_port}/"
    echo "========================================"
    echo ""
    echo "🌐 Browser will open automatically when API is ready..."
    echo ""
    
    if command -v show_api_docs_delayed >/dev/null 2>&1; then
        show_api_docs_delayed "$port" "120"
    fi
    
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
    # Deploy all services in detached mode.
    #
    # Args:
    #   $1: port - API port number.
    #   $2: compose_file - Path to the Docker Compose file.
    local port="$1"
    local compose_file="$2"
    
    echo "🚀 Starting all services (detached)..."
    echo ""
    echo "========================================"
    echo "  Services starting (detached):"
    echo "  - Backend API (port $port)"
    echo "  - PostgreSQL database"
    echo "  - Backup runner"
    local web_port
    web_port=$(get_env_variable "WEB_PORT" ".env" "8086")
    echo "  - Web GUI at http://localhost:${web_port}/"
    echo "========================================"
    echo ""
    echo "🌐 Browser will open automatically when API is ready..."
    echo ""
    
    if command -v show_api_docs_delayed >/dev/null 2>&1; then
        show_api_docs_delayed "$port" "120"
    fi
    
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

handle_start_with_test_databases() {
    # Start all services with test databases for all supported DB types.
    #
    # Args:
    #   $1: port - API port number.
    #   $2: compose_file - Path to the Docker Compose file.
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
    
    local test_db_file="local-deployment/docker-compose.test-databases.yml"
    if [[ "$(uname)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
        test_db_file="local-deployment/docker-compose.test-databases.mac.yml"
        echo "🍎 Detected macOS ARM64, using ARM64-compatible test databases"
    fi
    
    local runner_file="local-deployment/docker-compose.runner.yml"
    
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
    echo "📋 Docker compose output will be written to: $compose_log_file"

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

        if command -v open_browser_incognito >/dev/null 2>&1; then
            open_browser_incognito "$port" "$compose_file" "test"
        fi
    ) &
    local browser_pid=$!

    cd "$project_root" || return 1
    
    docker compose --ansi never --progress plain --env-file .env -f "$compose_file" -f "$runner_file" -f "$test_db_file" up --build --watch > "$compose_log_file" 2>&1

    kill "$browser_pid" >/dev/null 2>&1 || true
    wait "$browser_pid" >/dev/null 2>&1 || true
}

handle_clean_test_data() {
    # Delete local test database data directories.
    echo "🧹 Cleaning Test Database Data..."
    echo ""
    echo "This will remove all test database data and configurations:"
    echo "  - Test PostgreSQL data"
    echo "  - Test MySQL data"
    echo "  - Test Neo4j data and logs"
    echo "  - Test SQLite data"
    echo "  - pgAdmin configuration"
    echo ""
    
    local confirm
    if [[ -r /dev/tty ]]; then
        read -r -p "Are you sure you want to continue? (y/N): " confirm < /dev/tty
    else
        read -r -p "Are you sure you want to continue? (y/N): " confirm
    fi
    
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        echo ""
        echo "🗑️  Removing test database data..."
        
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
