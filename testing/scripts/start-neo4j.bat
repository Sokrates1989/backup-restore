@echo off
echo ========================================
echo Starting API with Neo4j
echo ========================================
echo.

REM Change to project root
cd /d "%~dp0..\.."

REM Copy environment file
if not exist .env (
    echo Copying Neo4j environment configuration...
    copy config\.env.neo4j.example .env
    echo.
)

echo Starting Docker services...
docker-compose -f docker\docker-compose.neo4j.yml up --build

echo.
echo ========================================
echo Services stopped
echo ========================================
