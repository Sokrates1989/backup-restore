#!/bin/bash
#
# quick-start.sh
#
# Vollständiges Onboarding-Tool für frisch geclonte Projekte:
# 1. Überprüft Docker-Installation
# 2. Erstellt .env aus .env.template
# 3. Startet Backend mit docker compose up
# 4. Bietet Dependency Management Optionen

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_DIR="${SCRIPT_DIR}/setup"

# Source modules
source "${SETUP_DIR}/modules/docker_helpers.sh"
source "${SETUP_DIR}/modules/version_manager.sh"
source "${SETUP_DIR}/modules/menu_handlers.sh"

# Source Cognito setup script if available
if [ -f "${SETUP_DIR}/modules/cognito_setup.sh" ]; then
    # shellcheck disable=SC1091
    source "${SETUP_DIR}/modules/cognito_setup.sh"
fi

echo "🚀 FastAPI Redis API Test - Quick Start"
echo "======================================"

# Docker-Verfügbarkeit prüfen
# Docker-Verfügbarkeit prüfen
if ! check_docker_installation; then
    exit 1
fi
echo ""

# Check if initial setup is needed
if [ ! -f .setup-complete ]; then
    echo "🚀 Erstmalige Einrichtung erkannt!"
    echo ""
    echo "Dies scheint das erste Mal zu sein, dass du dieses Projekt ausführst."
    echo "Möchtest du den interaktiven Setup-Assistenten ausführen?"
    echo ""
    echo "Der Setup-Assistent hilft dir bei der Konfiguration von:"
    echo "  • Docker Image-Name und Version"
    echo "  • Python-Version"
    echo "  • Datenbanktyp (PostgreSQL oder Neo4j)"
    echo "  • Datenbankmodus (lokal oder extern)"
    echo "  • API-Konfiguration"
    echo ""
    
    read -p "Setup-Assistenten jetzt ausführen? (Y/n): " runSetup
    if [[ ! "$runSetup" =~ ^[Nn]$ ]]; then
        echo ""
        echo "Starte Setup-Assistenten..."
        docker compose -f setup/docker-compose.setup.yml run --rm setup
        echo ""
        if declare -F run_cognito_setup >/dev/null; then
            run_cognito_setup
            echo ""
        fi
    else
        echo ""
        echo "Setup-Assistent übersprungen. Erstelle einfache .env aus Vorlage..."
        if [ -f setup/.env.template ]; then
            cp setup/.env.template .env
            echo "✅ .env wurde aus Vorlage erstellt."
            echo "⚠️  Bitte bearbeite .env, um deine Umgebung zu konfigurieren, bevor du fortfährst."
            if declare -F run_cognito_setup >/dev/null; then
                run_cognito_setup
                echo ""
            fi
        else
            echo "❌ setup/.env.template nicht gefunden!"
            exit 1
        fi
    fi
    echo ""
elif [ ! -f .env ]; then
    # Setup complete but .env missing - recreate from template
    echo "⚠️  .env Datei fehlt. Erstelle aus Vorlage..."
    if [ -f setup/.env.template ]; then
        cp setup/.env.template .env
        echo "✅ .env wurde aus Vorlage erstellt."
        echo "Bitte prüfe die Werte in .env bei Bedarf."
        if declare -F run_cognito_setup >/dev/null; then
            run_cognito_setup
            echo ""
        fi
    else
        echo "❌ setup/.env.template nicht gefunden!"
        exit 1
    fi
    echo ""
fi

# Port aus .env lesen (Standard: 8000)
PORT=$(read_env_variable "PORT" ".env" "8000")

# Database configuration aus .env lesen
DB_TYPE=$(read_env_variable "DB_TYPE" ".env" "neo4j")
DB_MODE=$(read_env_variable "DB_MODE" ".env" "local")

# Docker Compose Datei basierend auf DB_TYPE und DB_MODE bestimmen
COMPOSE_FILE=$(determine_compose_file "$DB_TYPE" "$DB_MODE")

if [ "$DB_MODE" = "external" ]; then
    echo "🔌 Detected external database mode"
    echo "   Database Type: $DB_TYPE"
    echo "   Will connect to external database (no local DB container)"
elif [ "$DB_TYPE" = "neo4j" ]; then
    echo "🗄️  Detected local Neo4j database"
    echo "   Will start Neo4j container"
elif [ "$DB_TYPE" = "postgresql" ] || [ "$DB_TYPE" = "mysql" ]; then
    echo "🗄️  Detected local $DB_TYPE database"
    echo "   Will start PostgreSQL container"
else
    echo "⚠️  Unknown DB_TYPE: $DB_TYPE, using default compose file"
fi

echo "   Using: $COMPOSE_FILE"
echo ""

# Prüfen, ob dies der erste Setup-Lauf ist
if [ ! -f ".setup-complete" ]; then
    echo "🎯 Erstes Setup erkannt - Führe automatische Dependency-Konfiguration durch..."
    echo "⚡ Beim ersten Start kann es etwas länger dauern, danach geht es meist deutlich schneller."
    echo ""
    
    # Run diagnostics to validate Docker/build configuration first
    echo "🔍 Running Docker/Build diagnostics..."
    DIAGNOSTICS_SCRIPT="python-dependency-management/scripts/run-docker-build-diagnostics.sh"
    if [ -f "$DIAGNOSTICS_SCRIPT" ]; then
        echo "Collecting diagnostic information..."
        if ./$DIAGNOSTICS_SCRIPT; then
            echo "✅ Diagnostics completed successfully"
        else
            echo ""
            echo "❌ Diagnostics reported issues with your Docker or build configuration!"
            echo "Please address the reported problems before continuing."
            echo ""
            echo "🔧 Troubleshooting steps:"
            echo "1. Ensure Docker Desktop/daemon is running"
            echo "2. Verify .env values (especially PYTHON_VERSION and DB settings)"
            echo "3. Review missing files noted in the diagnostics output"
            echo "4. Re-run manually via: ./$DIAGNOSTICS_SCRIPT"
            echo ""
            echo "Subsequent steps may fail until the diagnostics succeed."
            read -p "Continue anyway? (y/N): " continue_anyway
            if [[ ! "$continue_anyway" =~ ^[Yy]$ ]]; then
                echo "Setup aborted. Please fix the reported diagnostics issues first."
                exit 1
            fi
            echo "⚠️  Continuing with potentially broken configuration..."
        fi
    else
        echo "⚠️  $DIAGNOSTICS_SCRIPT not found - skipping diagnostics"
    fi
    echo ""
    echo "📦 Starte Dependency Management für initiales Setup..."
    
    # Führe das Dependency Management im initial-run Modus aus
    ./python-dependency-management/scripts/manage-python-project-dependencies.sh initial-run
    
    # Markiere Setup als abgeschlossen
    touch .setup-complete
    
    echo ""
    echo "🎉 Erstes Setup abgeschlossen!"
    echo "🐳 Starte nun das Backend..."
    echo ""
    echo "========================================"
    echo "  API will be accessible at:"
    echo "  http://localhost:$PORT/docs"
    echo "========================================"
    echo ""
    echo "Press ENTER to open the API documentation in your browser..."
    echo "(The API may take a few seconds to start. Please refresh the page if needed.)"
    read -r
    
    # Open browser in incognito/private mode
    echo "Opening browser..."
    if command -v xdg-open &> /dev/null; then
        # Linux
        xdg-open "http://localhost:$PORT/docs" &
    elif command -v open &> /dev/null; then
        # macOS - try to open in incognito mode
        open -na "Google Chrome" --args --incognito "http://localhost:$PORT/docs" 2>/dev/null || \
        open -na "Safari" --args --private "http://localhost:$PORT/docs" 2>/dev/null || \
        open "http://localhost:$PORT/docs"
    else
        echo "Could not detect browser command. Please open manually: http://localhost:$PORT/docs"
    fi
    
    echo ""
    docker compose --env-file .env -f "$COMPOSE_FILE" up --build
else
    echo "🐳 Starte Backend mit Docker Compose..."
    echo "Backend wird verfügbar sein auf: http://localhost:$PORT"
    echo ""

    show_main_menu "$PORT" "$COMPOSE_FILE"
fi