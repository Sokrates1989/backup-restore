#!/bin/bash
# Test Backup and Restore Functionality
# This script tests the complete backup/restore workflow

set -e

API_URL="http://localhost:8081"
ADMIN_KEY="change-this-to-a-secure-random-key"  # Default from .env.template

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
            -H "X-Admin-Key: $ADMIN_KEY" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -s -X "$method" "$API_URL$endpoint" \
            -H "X-Admin-Key: $ADMIN_KEY"
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
docker compose down
sleep 2

echo "  🗑️  Deleting PostgreSQL data..."
POSTGRES_DATA_PATH=".docker/postgres-data"
if [ -d "$POSTGRES_DATA_PATH" ]; then
    rm -rf "$POSTGRES_DATA_PATH"
    echo "  ✅ Database wiped"
else
    echo "  ℹ️  No data directory found (already clean)"
fi

echo "  🔄 Starting containers..."
docker compose up -d
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
RESTORE_RESPONSE=$(api_call POST "/backup/restore/$BACKUP_FILENAME")
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
DELETE_RESPONSE=$(api_call DELETE "/backup/delete/$BACKUP_FILENAME" || echo '{"success":false}')
if echo "$DELETE_RESPONSE" | jq -e '.success' > /dev/null; then
    echo "  ✅ Backup deleted"
else
    echo "  ⚠️  Could not delete backup"
fi

echo ""
echo "====================================="
echo "  Test Complete!"
echo "====================================="
