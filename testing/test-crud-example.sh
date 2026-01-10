#!/bin/bash
# Test script for CRUD example endpoints

BASE_URL="http://localhost:8000"
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Testing CRUD Example Endpoints${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to print test results
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
    fi
}

# Note: Table is created automatically via migrations on startup
# No initialization endpoint needed!

# 1. Create example
echo -e "${BLUE}1. Creating example...${NC}"
response=$(curl -s -X POST "$BASE_URL/examples/" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Example", "description": "This is a test"}')
echo "$response" | grep -q "success"
print_result $? "Create example"

# Extract ID from response
example_id=$(echo "$response" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
echo "Created example with ID: $example_id"
echo ""

# 2. Get example by ID
echo -e "${BLUE}2. Getting example by ID...${NC}"
response=$(curl -s "$BASE_URL/examples/$example_id")
echo "$response" | grep -q "Test Example"
print_result $? "Get example by ID"
echo ""

# 3. List all examples
echo -e "${BLUE}3. Listing all examples...${NC}"
response=$(curl -s "$BASE_URL/examples/")
echo "$response" | grep -q "Test Example"
print_result $? "List examples"
echo ""

# 4. Update example
echo -e "${BLUE}4. Updating example...${NC}"
response=$(curl -s -X PUT "$BASE_URL/examples/$example_id" \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Example", "description": "Updated description"}')
echo "$response" | grep -q "Updated Example"
print_result $? "Update example"
echo ""

# 5. Verify update
echo -e "${BLUE}5. Verifying update...${NC}"
response=$(curl -s "$BASE_URL/examples/$example_id")
echo "$response" | grep -q "Updated Example"
print_result $? "Verify update"
echo ""

# 6. Delete example
echo -e "${BLUE}6. Deleting example...${NC}"
response=$(curl -s -X DELETE "$BASE_URL/examples/$example_id")
echo "$response" | grep -q "success"
print_result $? "Delete example"
echo ""

# 7. Verify deletion
echo -e "${BLUE}7. Verifying deletion...${NC}"
response=$(curl -s "$BASE_URL/examples/$example_id")
echo "$response" | grep -q "not found"
print_result $? "Verify deletion"
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}All tests completed!${NC}"
echo -e "${BLUE}========================================${NC}"
