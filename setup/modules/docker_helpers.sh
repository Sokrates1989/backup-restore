#!/bin/bash
#
# docker_helpers.sh
#
# Module for Docker-related helper functions

check_docker_installation() {
    echo "🔍 Überprüfe Docker-Installation..."
    
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker ist nicht installiert!"
        echo "📥 Bitte installiere Docker von: https://www.docker.com/get-started"
        return 1
    fi

    if ! docker info &> /dev/null; then
        echo "❌ Docker-Daemon läuft nicht!"
        echo "🔄 Bitte starte Docker Desktop oder den Docker-Service"
        return 1
    fi

    if ! docker compose version &> /dev/null; then
        echo "❌ Docker Compose ist nicht verfügbar!"
        echo "📥 Bitte installiere eine aktuelle Docker-Version mit Compose-Plugin"
        return 1
    fi

    echo "✅ Docker ist installiert und läuft"
    return 0
}

read_env_variable() {
    local var_name="$1"
    local env_file="${2:-.env}"
    local default_value="${3:-}"
    
    local value
    value=$(grep "^${var_name}=" "$env_file" 2>/dev/null | head -n1 | cut -d'=' -f2- | tr -d ' "')
    
    if [ -z "$value" ]; then
        echo "$default_value"
    else
        echo "$value"
    fi
}

determine_compose_file() {
    local db_type="$1"
    local db_mode="$2"
    
    if [ "$db_mode" = "external" ]; then
        echo "local-deployment/docker-compose.yml"
    elif [ "$db_type" = "neo4j" ]; then
        echo "local-deployment/docker-compose.neo4j.yml"
    elif [ "$db_type" = "postgresql" ] || [ "$db_type" = "mysql" ]; then
        echo "local-deployment/docker-compose.postgres.yml"
    else
        echo "local-deployment/docker-compose.yml"
    fi
}
