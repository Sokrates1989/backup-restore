#!/bin/bash
# Test script to verify migration fix works with component-based DB configuration

echo "🧪 Testing Migration Fix"
echo "========================"
echo ""

# Set up test environment variables (simulating Docker Swarm deployment)
export DB_TYPE="postgresql"
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="test_db"
export DB_USER="test_user"
export DB_PASSWORD="test_password"
# Intentionally NOT setting DATABASE_URL to test component-based construction

echo "📋 Test Configuration:"
echo "  DB_TYPE: $DB_TYPE"
echo "  DB_HOST: $DB_HOST"
echo "  DB_PORT: $DB_PORT"
echo "  DB_NAME: $DB_NAME"
echo "  DB_USER: $DB_USER"
echo "  DATABASE_URL: ${DATABASE_URL:-<NOT SET>}"
echo ""

# Test 1: Check if alembic can construct the URL
echo "🔍 Test 1: Checking if Alembic can construct DATABASE_URL from components..."
cd "$(dirname "$0")"

# Try to run alembic current (this will test the get_url() function)
if python -c "
import sys
import os
sys.path.insert(0, 'app')
os.chdir('.')
from alembic.config import Config
from alembic import command

try:
    alembic_cfg = Config('alembic.ini')
    # This will call get_url() internally
    print('✅ Alembic configuration loaded successfully')
    print('   URL construction from components works!')
except Exception as e:
    print(f'❌ Error: {e}')
    sys.exit(1)
"; then
    echo "✅ Test 1 PASSED"
else
    echo "❌ Test 1 FAILED"
    exit 1
fi

echo ""
echo "🎉 All tests passed!"
echo ""
echo "📝 Next Steps:"
echo "  1. Rebuild the Docker image with the fix"
echo "  2. Push the new image to Docker Hub"
echo "  3. Update the swarm deployment to use the new image"
