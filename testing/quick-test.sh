#!/bin/bash
# Quick Test Entry Script
# Simplified testing interface for the API

set -e

cd "$(dirname "$0")/.."

echo "========================================"
echo "FastAPI Quick Test"
echo "========================================"
echo ""

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running!"
    echo "🔄 Please start Docker Desktop or the Docker service"
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found!"
    echo ""
    echo "Please choose a database configuration:"
    echo "1) PostgreSQL (recommended for testing)"
    echo "2) Neo4j"
    echo "3) Exit and configure manually"
    echo ""
    read -p "Your choice (1-3): " db_choice
    
    case $db_choice in
        1)
            echo "📝 Copying PostgreSQL configuration..."
            cp config/.env.postgres.example .env
            echo "✅ Using PostgreSQL"
            ;;
        2)
            echo "📝 Copying Neo4j configuration..."
            cp config/.env.neo4j.example .env
            echo "✅ Using Neo4j"
            ;;
        3)
            echo "ℹ️  Please create .env file manually"
            echo "   You can copy from config/.env.postgres.example or config/.env.neo4j.example"
            exit 0
            ;;
        *)
            echo "❌ Invalid choice. Using PostgreSQL as default..."
            cp config/.env.postgres.example .env
            ;;
    esac
    echo ""
fi

# Read database configuration
DB_TYPE=$(grep "^DB_TYPE=" .env 2>/dev/null | cut -d'=' -f2 | tr -d ' "' || echo "neo4j")
DB_MODE=$(grep "^DB_MODE=" .env 2>/dev/null | cut -d'=' -f2 | tr -d ' "' || echo "local")

# Determine compose file
if [ "$DB_MODE" = "external" ]; then
    COMPOSE_FILE="local-deployment/docker-compose.yml"
    echo "🔌 Using external $DB_TYPE database"
elif [ "$DB_TYPE" = "neo4j" ]; then
    COMPOSE_FILE="local-deployment/docker-compose.neo4j.yml"
    echo "🗄️  Using local Neo4j database"
elif [ "$DB_TYPE" = "postgresql" ] || [ "$DB_TYPE" = "mysql" ]; then
    COMPOSE_FILE="local-deployment/docker-compose.postgres.yml"
    echo "🗄️  Using local PostgreSQL database"
else
    COMPOSE_FILE="local-deployment/docker-compose.yml"
    echo "⚠️  Unknown database type, using default"
fi

echo ""
echo "What would you like to do?"
echo "1) Start services and run tests"
echo "2) Just start services"
echo "3) Just run tests (services must be running)"
echo "4) Stop services"
echo ""
read -p "Your choice (1-4): " action_choice

case $action_choice in
    1)
        echo ""
        echo "🚀 Starting services..."
        docker compose -f "$COMPOSE_FILE" up -d --build
        
        echo ""
        echo "⏳ Waiting for services to be ready..."
        sleep 10
        
        echo ""
        echo "🧪 Running tests..."
        ./testing/scripts/test-api.sh
        
        echo ""
        echo "✅ Services are running!"
        echo "   API: http://localhost:8000/docs"
        echo ""
        echo "To stop services, run:"
        echo "   docker compose -f $COMPOSE_FILE down"
        ;;
    2)
        echo ""
        echo "🚀 Starting services..."
        docker compose -f "$COMPOSE_FILE" up --build
        ;;
    3)
        echo ""
        echo "🧪 Running tests..."
        ./testing/scripts/test-api.sh
        ;;
    4)
        echo ""
        echo "🛑 Stopping services..."
        docker compose -f "$COMPOSE_FILE" down
        echo "✅ Services stopped"
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac
