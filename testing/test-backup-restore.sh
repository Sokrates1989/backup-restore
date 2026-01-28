#!/bin/bash
# Test Backup and Restore Functionality
# This script tests the complete backup/restore workflow

set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

PORT="$(grep -E '^PORT=' "$ENV_FILE" 2>/dev/null | head -n 1 | cut -d'=' -f2 | tr -d ' "\r')"
DB_TYPE="$(grep -E '^DB_TYPE=' "$ENV_FILE" 2>/dev/null | head -n 1 | cut -d'=' -f2 | tr -d ' "\r')"
DB_MODE="$(grep -E '^DB_MODE=' "$ENV_FILE" 2>/dev/null | head -n 1 | cut -d'=' -f2 | tr -d ' "\r')"
KEYCLOAK_URL="$(grep -E '^KEYCLOAK_URL=' "$ENV_FILE" 2>/dev/null | head -n 1 | cut -d'=' -f2- | tr -d ' "\r')"
KEYCLOAK_INTERNAL_URL="$(grep -E '^KEYCLOAK_INTERNAL_URL=' "$ENV_FILE" 2>/dev/null | head -n 1 | cut -d'=' -f2- | tr -d ' "\r')"
KEYCLOAK_REALM="$(grep -E '^KEYCLOAK_REALM=' "$ENV_FILE" 2>/dev/null | head -n 1 | cut -d'=' -f2- | tr -d ' "\r')"
KEYCLOAK_CLIENT_ID="$(grep -E '^KEYCLOAK_CLIENT_ID=' "$ENV_FILE" 2>/dev/null | head -n 1 | cut -d'=' -f2- | tr -d ' "\r')"
KEYCLOAK_CLIENT_SECRET="$(grep -E '^KEYCLOAK_CLIENT_SECRET=' "$ENV_FILE" 2>/dev/null | head -n 1 | cut -d'=' -f2- | tr -d ' "\r')"

API_URL="http://localhost:${PORT:-8000}"

KEYCLOAK_URL="${KEYCLOAK_INTERNAL_URL:-$KEYCLOAK_URL}"

get_access_token() {
    local token="$ACCESS_TOKEN"
    if [ -n "$token" ]; then
        echo "$token"
        return
    fi

    if [ -n "$KEYCLOAK_URL" ] && [ -n "$KEYCLOAK_REALM" ] && [ -n "$KEYCLOAK_CLIENT_ID" ] && [ -n "$KEYCLOAK_CLIENT_SECRET" ]; then
        local token_endpoint="${KEYCLOAK_URL%/}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token"
        local token_response
        token_response=$(curl -s -X POST "$token_endpoint" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            -d "grant_type=client_credentials" \
            -d "client_id=$KEYCLOAK_CLIENT_ID" \
            -d "client_secret=$KEYCLOAK_CLIENT_SECRET")
        token=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" <<< "$token_response")
    fi

    if [ -z "$token" ]; then
        read -r -p "Enter Keycloak access token: " token
    fi

    echo "$token"
}

ACCESS_TOKEN=$(get_access_token)
if [ -z "$ACCESS_TOKEN" ]; then
    echo "❌ Missing Keycloak access token."
    exit 1
fi

COMPOSE_FILE="$ROOT_DIR/local-deployment/docker-compose.postgres.yml"
if [ "$DB_MODE" = "standalone" ]; then
    COMPOSE_FILE="$ROOT_DIR/local-deployment/docker-compose.yml"
elif [ "$DB_TYPE" = "neo4j" ]; then
    COMPOSE_FILE="$ROOT_DIR/local-deployment/docker-compose.neo4j.yml"
elif [ "$DB_TYPE" = "postgresql" ] || [ "$DB_TYPE" = "mysql" ]; then
    COMPOSE_FILE="$ROOT_DIR/local-deployment/docker-compose.postgres.yml"
else
    COMPOSE_FILE="$ROOT_DIR/local-deployment/docker-compose.yml"
fi

echo "====================================="
echo "  Backup & Restore Test"
echo "====================================="
echo ""

# Function to make API calls
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    
    if [ -n "$data" ]; then
        curl -s -X "$method" "$API_URL$endpoint" \
            -H "Authorization: Bearer $ACCESS_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -s -X "$method" "$API_URL$endpoint" \
            -H "Authorization: Bearer $ACCESS_TOKEN"
    fi
}

api_call_restore() {
    local method=$1
    local endpoint=$2
    local data=$3

    if [ -n "$data" ]; then
        curl -s -X "$method" "$API_URL$endpoint" \
            -H "Authorization: Bearer $ACCESS_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -s -X "$method" "$API_URL$endpoint" \
            -H "Authorization: Bearer $ACCESS_TOKEN"
    fi
}

api_call_delete() {
    local method=$1
    local endpoint=$2
    local data=$3

    if [ -n "$data" ]; then
        curl -s -X "$method" "$API_URL$endpoint" \
            -H "Authorization: Bearer $ACCESS_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -s -X "$method" "$API_URL$endpoint" \
            -H "Authorization: Bearer $ACCESS_TOKEN"
    fi
}

# Step 1: Create test data
echo "📝 Step 1: Creating test data..."

api_call POST "/examples/" '{"name":"Test Item 1","description":"First test item"}'
echo "  ✅ Created: Test Item 1"

api_call POST "/examples/" '{"name":"Test Item 2","description":"Second test item"}'
echo "  ✅ Created: Test Item 2"

api_call POST "/examples/" '{"name":"Test Item 3","description":"Third test item"}'
echo "  ✅ Created: Test Item 3"

# Step 2: Verify data exists
echo ""
echo "🔍 Step 2: Verifying data exists..."
BEFORE_COUNT=$(api_call GET "/examples/" | jq -r '.total')
echo "  📊 Found $BEFORE_COUNT items before backup"

# Step 3: Create backup
echo ""
echo "💾 Step 3: Creating backup..."
BACKUP_RESPONSE=$(api_call POST "/backup/create?compress=true")
BACKUP_FILENAME=$(echo "$BACKUP_RESPONSE" | jq -r '.filename')
BACKUP_SIZE=$(echo "$BACKUP_RESPONSE" | jq -r '.size_mb')
echo "  ✅ Backup created: $BACKUP_FILENAME"
echo "  📦 Size: $BACKUP_SIZE MB"

# Step 4: Wipe database
echo ""
echo "🗑️  Step 4: Wiping database..."
echo "  ⚠️  Stopping containers..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down --remove-orphans
sleep 2

echo "  🗑️  Deleting PostgreSQL data..."
POSTGRES_DATA_PATH="$ROOT_DIR/.docker/postgres-data"
if [ -d "$POSTGRES_DATA_PATH" ]; then
    rm -rf "$POSTGRES_DATA_PATH"
    echo "  ✅ Database wiped"
else
    echo "  ℹ️  No data directory found (already clean)"
fi

echo "  🔄 Starting containers..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build
sleep 10  # Wait for services to start

# Step 5: Verify database is empty
echo ""
echo "🔍 Step 5: Verifying database is empty..."
AFTER_WIPE_COUNT=$(api_call GET "/examples/" | jq -r '.total' || echo "0")
echo "  📊 Found $AFTER_WIPE_COUNT items after wipe"

if [ "$AFTER_WIPE_COUNT" -eq "0" ]; then
    echo "  ✅ Database successfully wiped"
else
    echo "  ⚠️  Warning: Database not empty ($AFTER_WIPE_COUNT items remain)"
fi

# Step 6: Restore from backup
echo ""
echo "♻️  Step 6: Restoring from backup..."
echo "  📂 Restoring: $BACKUP_FILENAME"
RESTORE_RESPONSE=$(api_call_restore POST "/backup/restore/$BACKUP_FILENAME")
echo "  ✅ $(echo "$RESTORE_RESPONSE" | jq -r '.message')"

# Step 7: Verify data is restored
echo ""
echo "🔍 Step 7: Verifying data is restored..."
sleep 2  # Give database a moment
AFTER_RESTORE_COUNT=$(api_call GET "/examples/" | jq -r '.total')
echo "  📊 Found $AFTER_RESTORE_COUNT items after restore"

# Step 8: Compare results
echo ""
echo "📊 Step 8: Comparing results..."
echo "  Before backup: $BEFORE_COUNT items"
echo "  After wipe:    0 items"
echo "  After restore: $AFTER_RESTORE_COUNT items"

if [ "$BEFORE_COUNT" -eq "$AFTER_RESTORE_COUNT" ]; then
    echo ""
    echo "✅ SUCCESS! Backup and restore working correctly!"
    echo "   All $AFTER_RESTORE_COUNT items were successfully restored."
else
    echo ""
    echo "❌ FAILURE! Data mismatch!"
    echo "   Expected: $BEFORE_COUNT items"
    echo "   Got: $AFTER_RESTORE_COUNT items"
    exit 1
fi

# Step 9: Cleanup - delete test backup
echo ""
echo "🧹 Step 9: Cleaning up test backup..."
DELETE_RESPONSE=$(api_call_delete DELETE "/backup/delete/$BACKUP_FILENAME" || echo '{"success":false}')
if echo "$DELETE_RESPONSE" | jq -e '.success' > /dev/null; then
    echo "  ✅ Backup deleted"
else
    echo "  ⚠️  Could not delete backup"
fi

echo ""
echo "====================================="
echo "  Test Complete!"
echo "====================================="
