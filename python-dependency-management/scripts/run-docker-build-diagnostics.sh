#!/usr/bin/env bash

set -euo pipefail

# Change to project root (script is in python-dependency-management/scripts/)
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

show_diagnostics() {
    echo ""
    echo "🔧 Diagnostic Information:"
    echo "=========================="

    if command -v docker >/dev/null 2>&1; then
        echo "✅ Docker CLI available"
        if docker info >/dev/null 2>&1; then
            echo "✅ Docker daemon is running"
        else
            echo "❌ Docker daemon is not running"
        fi
    else
        echo "❌ Docker CLI not found"
    fi

    if docker compose version >/dev/null 2>&1; then
        echo "✅ docker compose command available"
    else
        echo "❌ docker compose command unavailable"
    fi

    if [[ -f .env ]]; then
        echo "✅ .env file exists"
        if grep -q '^PYTHON_VERSION' .env; then
            echo "✅ PYTHON_VERSION is defined -> $(grep '^PYTHON_VERSION' .env)"
        else
            echo "❌ PYTHON_VERSION missing in .env"
        fi
    else
        echo "❌ .env file does not exist"
    fi

    [[ -f Dockerfile ]] && echo "✅ Dockerfile exists" || echo "❌ Dockerfile missing"
    [[ -f python-dependency-management/Dockerfile ]] && echo "✅ python-dependency-management/Dockerfile exists" || echo "❌ python-dependency-management/Dockerfile missing"

    local compose_files=(
        "local-deployment/docker-compose.yml"
        "local-deployment/docker-compose.postgres.yml"
        "local-deployment/docker-compose.neo4j.yml"
    )

    for file in "${compose_files[@]}"; do
        if [[ -f "$file" ]]; then
            echo "✅ $file exists"
        else
            echo "❌ $file missing"
        fi
    done
}

run_docker_build() {
    local description="$1"
    shift

    echo ""
    echo "🐳 $description..."
    if docker "$@"; then
        echo "✅ $description succeeded"
    else
        echo "❌ $description failed"
        show_diagnostics
        exit 1
    fi
}

run_compose_build() {
    local compose_file="$1"
    local description="$2"

    echo "→ Building $description ($compose_file)"
    if docker compose -f "$compose_file" build --no-cache; then
        echo "✅ $description builds successfully"
    else
        echo "❌ $description build failed"
        show_diagnostics
        exit 1
    fi
    echo ""
}

echo "🔍 Running Docker build diagnostics"
echo "=================================="

if [[ -f .env ]]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
    if [[ -z "${PYTHON_VERSION:-}" ]]; then
        echo "❌ PYTHON_VERSION not defined in .env"
        show_diagnostics
        exit 1
    fi
    echo "✅ Loaded .env configuration (PYTHON_VERSION=$PYTHON_VERSION)"
else
    echo "❌ .env file not found"
    echo "   Please ensure .env exists in the project root"
    show_diagnostics
    exit 1
fi

run_docker_build "Building main Dockerfile" build --build-arg "PYTHON_VERSION=$PYTHON_VERSION" -t diagnostics-main .

pushd python-dependency-management >/dev/null
run_docker_build "Building python-dependency-management Dockerfile" build --build-arg "PYTHON_VERSION=$PYTHON_VERSION" -t diagnostics-dev .
popd >/dev/null

echo ""
echo "🐳 Testing docker compose builds..."
run_compose_build "local-deployment/docker-compose.yml" "base services"
run_compose_build "local-deployment/docker-compose.postgres.yml" "PostgreSQL stack"
run_compose_build "local-deployment/docker-compose.neo4j.yml" "Neo4j stack"

echo "🎉 Docker build diagnostics completed!"
echo "====================================="
 