#!/bin/bash

# Interactive Setup Script for Python API Template
# This script helps users configure their project on first setup

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/modules/cognito_setup.sh" ]; then
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/modules/cognito_setup.sh"
fi

echo "🚀 Python API Template - Initial Setup"
echo "======================================"
echo ""

# Check if setup is already complete
if [ -f .setup-complete ]; then
    echo "⚠️  Setup has already been completed."
    read -p "Do you want to run setup again? This will overwrite .env (y/N): " RERUN_SETUP
    if [[ ! "$RERUN_SETUP" =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 0
    fi
    echo ""
fi

# Backup existing .env if it exists
if [ -f .env ]; then
    BACKUP_FILE=".env.backup.$(date +%Y%m%d_%H%M%S)"
    cp .env "$BACKUP_FILE"
    echo "📋 Backed up existing .env to $BACKUP_FILE"
    echo ""
fi

# Start with template
cp "${SCRIPT_DIR}/.env.template" .env

echo "Let's configure your API project!"
echo ""

# =============================================================================
# DOCKER IMAGE CONFIGURATION
# =============================================================================
echo "📦 Docker Image Configuration"
echo "------------------------------"
echo "This is used for building production Docker images."
echo ""

read -p "Enter Docker image name (e.g., sokrates1989/python-api-template): " IMAGE_NAME
while [ -z "$IMAGE_NAME" ]; do
    echo "❌ Image name cannot be empty"
    read -p "Enter Docker image name (e.g., sokrates1989/python-api-template): " IMAGE_NAME
done

read -p "Enter initial image version [0.0.1]: " IMAGE_VERSION
IMAGE_VERSION="${IMAGE_VERSION:-0.0.1}"

# Update .env with image configuration
sed -i "s|^IMAGE_NAME=.*|IMAGE_NAME=$IMAGE_NAME|" .env
sed -i "s|^IMAGE_VERSION=.*|IMAGE_VERSION=$IMAGE_VERSION|" .env

echo "✅ Image: $IMAGE_NAME:$IMAGE_VERSION"
echo ""

# =============================================================================
# PYTHON VERSION
# =============================================================================
echo "🐍 Python Version"
echo "-----------------"
read -p "Enter Python version [3.13]: " PYTHON_VERSION
PYTHON_VERSION="${PYTHON_VERSION:-3.13}"

sed -i "s|^PYTHON_VERSION=.*|PYTHON_VERSION=$PYTHON_VERSION|" .env
echo "✅ Python version: $PYTHON_VERSION"
echo ""

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
echo "🗄️  Database Configuration"
echo "-------------------------"
echo "Choose database type:"
echo "1) PostgreSQL (recommended for relational data)"
echo "2) Neo4j (recommended for graph data)"
echo ""

read -p "Your choice (1-2) [1]: " DB_CHOICE
DB_CHOICE="${DB_CHOICE:-1}"

case $DB_CHOICE in
    1)
        DB_TYPE="postgresql"
        echo "✅ Selected: PostgreSQL"
        ;;
    2)
        DB_TYPE="neo4j"
        echo "✅ Selected: Neo4j"
        ;;
    *)
        DB_TYPE="postgresql"
        echo "⚠️  Invalid choice, defaulting to PostgreSQL"
        ;;
esac

sed -i "s|^DB_TYPE=.*|DB_TYPE=$DB_TYPE|" .env
echo ""

# Database mode
echo "Choose database mode:"
echo "1) Local (Docker container - recommended for development)"
echo "2) External (existing database server)"
echo ""

read -p "Your choice (1-2) [1]: " DB_MODE_CHOICE
DB_MODE_CHOICE="${DB_MODE_CHOICE:-1}"

case $DB_MODE_CHOICE in
    1)
        DB_MODE="local"
        echo "✅ Selected: Local Docker database"
        ;;
    2)
        DB_MODE="external"
        echo "✅ Selected: External database"
        ;;
    *)
        DB_MODE="local"
        echo "⚠️  Invalid choice, defaulting to local"
        ;;
esac

sed -i "s|^DB_MODE=.*|DB_MODE=$DB_MODE|" .env
echo ""

# Database credentials (for local mode)
if [ "$DB_MODE" = "local" ]; then
    if [ "$DB_TYPE" = "postgresql" ]; then
        echo "PostgreSQL Configuration:"
        echo ""
        
        read -p "Database name [apidb]: " DB_NAME
        DB_NAME="${DB_NAME:-apidb}"
        
        read -p "Database user [apiuser]: " DB_USER
        DB_USER="${DB_USER:-apiuser}"
        
        read -p "Database password [changeme]: " DB_PASSWORD
        DB_PASSWORD="${DB_PASSWORD:-changeme}"
        
        read -p "Database port [5432]: " DB_PORT
        DB_PORT="${DB_PORT:-5432}"
        
        sed -i "s|^DB_NAME=.*|DB_NAME=$DB_NAME|" .env
        sed -i "s|^DB_USER=.*|DB_USER=$DB_USER|" .env
        sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=$DB_PASSWORD|" .env
        sed -i "s|^DB_PORT=.*|DB_PORT=$DB_PORT|" .env
        
        echo "✅ PostgreSQL configured"
        echo ""
    elif [ "$DB_TYPE" = "neo4j" ]; then
        echo "Neo4j Configuration:"
        echo ""
        echo "ℹ️  Note: Neo4j requires username to be 'neo4j'"
        echo ""
        
        # Neo4j username must be 'neo4j'
        DB_USER="neo4j"
        
        read -p "Database password [neo4jpassword]: " DB_PASSWORD
        DB_PASSWORD="${DB_PASSWORD:-neo4jpassword}"
        
        read -p "Bolt port [7687]: " DB_PORT
        DB_PORT="${DB_PORT:-7687}"
        
        read -p "HTTP port [7474]: " NEO4J_HTTP_PORT
        NEO4J_HTTP_PORT="${NEO4J_HTTP_PORT:-7474}"
        
        # Update all Neo4j-related settings
        sed -i "s|^DB_USER=.*|DB_USER=$DB_USER|" .env
        sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=$DB_PASSWORD|" .env
        sed -i "s|^DB_PORT=.*|DB_PORT=$DB_PORT|" .env
        sed -i "s|^NEO4J_HTTP_PORT=.*|NEO4J_HTTP_PORT=$NEO4J_HTTP_PORT|" .env
        
        # Also update NEO4J_URL to use the configured password
        sed -i "s|^NEO4J_URL=.*|NEO4J_URL=bolt://neo4j:$DB_PORT|" .env
        
        echo "✅ Neo4j configured (username: neo4j, password: $DB_PASSWORD)"
        echo ""
    fi
fi

# External database configuration
if [ "$DB_MODE" = "external" ]; then
    echo "⚠️  External database mode selected."
    echo "Please manually configure the database connection in .env"
    echo ""
fi

# =============================================================================
# API CONFIGURATION
# =============================================================================
echo "🌐 API Configuration"
echo "-------------------"

read -p "API port [8000]: " PORT
PORT="${PORT:-8000}"

read -p "Enable debug mode? (true/false) [false]: " DEBUG
DEBUG="${DEBUG:-false}"

sed -i "s|^PORT=.*|PORT=$PORT|" .env
sed -i "s|^DEBUG=.*|DEBUG=$DEBUG|" .env

echo "✅ API will run on port $PORT"
echo ""

# =============================================================================
# OPTIONAL: AWS COGNITO CONFIGURATION
# =============================================================================
if declare -F run_cognito_setup >/dev/null; then
    if ! run_cognito_setup; then
        echo "⚠️  AWS Cognito configuration skipped or failed. You can configure it later via quick-start scripts."
        echo ""
    fi
fi

# =============================================================================
# SUMMARY
# =============================================================================
echo "📋 Configuration Summary"
echo "========================"
echo "Docker Image:    $IMAGE_NAME:$IMAGE_VERSION"
echo "Python Version:  $PYTHON_VERSION"
echo "Database Type:   $DB_TYPE"
echo "Database Mode:   $DB_MODE"
echo "API Port:        $PORT"
echo "Debug Mode:      $DEBUG"
echo ""

read -p "Save this configuration? (Y/n): " CONFIRM
if [[ "$CONFIRM" =~ ^[Nn]$ ]]; then
    echo "❌ Setup cancelled. .env not saved."
    if [ -f "$BACKUP_FILE" ]; then
        mv "$BACKUP_FILE" .env
        echo "Restored previous .env"
    fi
    exit 1
fi

# Mark setup as complete
touch .setup-complete
echo "✅ Setup complete! Configuration saved to .env"
echo ""

echo "🎉 Next Steps:"
echo "=============="
echo "1. Review and customize .env if needed"
echo "2. Run: .\quick-start.ps1 (Windows) or ./quick-start.sh (Linux/Mac)"
echo "3. Select option 1 to start the backend"
echo ""
echo "For production builds, select option 5 in the quick-start menu."
echo ""
