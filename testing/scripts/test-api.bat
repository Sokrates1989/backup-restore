@echo off
echo ========================================
echo Testing API Endpoints
echo ========================================
echo.

echo 1. Testing Database Connection...
curl -s http://localhost:8000/test/db-test
echo.
echo.

echo 2. Getting Database Info...
curl -s http://localhost:8000/test/db-info
echo.
echo.

echo 3. Executing Sample Query...
curl -s http://localhost:8000/test/db-sample-query
echo.
echo.

echo 4. Testing File Count...
curl -s http://localhost:8000/files/file-count
echo.
echo.

echo ========================================
echo All tests completed!
echo ========================================
echo.
echo Open Swagger UI: http://localhost:8000/docs
echo.
