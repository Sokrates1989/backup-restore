#!/bin/bash
# Test API endpoints

echo "========================================"
echo "Testing API Endpoints"
echo "========================================"
echo ""

API_URL="http://localhost:8000"

echo "1. Testing database connection..."
echo "GET $API_URL/test/db-test"
curl -s "$API_URL/test/db-test" | python3 -m json.tool 2>/dev/null || curl -s "$API_URL/test/db-test"
echo ""
echo ""

echo "2. Testing database info..."
echo "GET $API_URL/test/db-info"
curl -s "$API_URL/test/db-info" | python3 -m json.tool 2>/dev/null || curl -s "$API_URL/test/db-info"
echo ""
echo ""

echo "3. Testing sample query..."
echo "GET $API_URL/test/sample-query"
curl -s "$API_URL/test/sample-query" | python3 -m json.tool 2>/dev/null || curl -s "$API_URL/test/sample-query"
echo ""
echo ""

echo "4. Testing file count..."
echo "GET $API_URL/files/file-count"
curl -s "$API_URL/files/file-count" | python3 -m json.tool 2>/dev/null || curl -s "$API_URL/files/file-count"
echo ""
echo ""

echo "========================================"
echo "Testing complete!"
echo "========================================"
echo ""
echo "For more endpoints, visit:"
echo "  Swagger UI: $API_URL/docs"
echo "  ReDoc:      $API_URL/redoc"
