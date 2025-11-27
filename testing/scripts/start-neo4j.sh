#!/bin/bash
# Start API with Neo4j

cd "$(dirname "$0")/../.."

echo "========================================"
echo "Starting API with Neo4j"
echo "========================================"
echo ""

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "Copying Neo4j environment configuration..."
    cp config/.env.neo4j.example .env
    echo ""
fi

echo "Starting Docker services..."
docker compose -f local-deployment/docker-compose.neo4j.yml up --build

echo ""
echo "========================================"
echo "Services stopped"
echo "========================================"
