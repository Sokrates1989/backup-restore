#!/bin/bash
# Start API with PostgreSQL

cd "$(dirname "$0")/../.."

echo "========================================"
echo "Starting API with PostgreSQL"
echo "========================================"
echo ""

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "Copying PostgreSQL environment configuration..."
    cp config/.env.postgres.example .env
    echo ""
fi

echo "Starting Docker services..."
docker compose -f local-deployment/docker-compose.postgres.yml up --build

echo ""
echo "========================================"
echo "Services stopped"
echo "========================================"
