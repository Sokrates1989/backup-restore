@echo off
echo ========================================
echo Starting API with PostgreSQL
echo ========================================
echo.

REM Change to project root
cd /d "%~dp0..\.."

REM Copy environment file
if not exist .env (
    echo Copying PostgreSQL environment configuration...
    copy config\.env.postgres.example .env
    echo.
)

echo Starting Docker services...
docker-compose -f docker\docker-compose.postgres.yml up --build

echo.
echo ========================================
echo Services stopped
echo ========================================
