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
source "${SETUP_DIR}/modules/browser_helpers.sh"
source "${SETUP_DIR}/modules/menu_io.sh"
source "${SETUP_DIR}/modules/menu_browser.sh"
source "${SETUP_DIR}/modules/menu_keycloak.sh"
source "${SETUP_DIR}/modules/menu_actions.sh"

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
    echo "  • ob eine lokale Datenbank in Docker gestartet werden soll oder nur die API (externe DB)"
    echo "  • API-Konfiguration"
    echo ""
    
    EXISTING_ENV_BEFORE_PROMPT=false
    if [ -f .env ]; then
        EXISTING_ENV_BEFORE_PROMPT=true
    fi
    
    read -p "Setup-Assistenten jetzt ausführen? (Y/n): " runSetup
    if [[ "$runSetup" =~ ^[Yy]$ ]]; then
        echo ""
        echo "Running interactive setup wizard..."
        docker compose -f setup/docker-compose.setup.yml run --rm setup
        echo ""
    else
        echo ""
        if [ "$EXISTING_ENV_BEFORE_PROMPT" = true ]; then
            echo "Skipping setup wizard. Existing .env detected, keeping current values."
        else
            echo "Skipping setup wizard. Creating basic .env from template..."
            if [ -f setup/.env.template ]; then
                cp setup/.env.template .env
                echo "✅ .env created from template."
                echo "⚠️  Please edit .env to configure your environment before continuing."

                EDITOR_CMD="${EDITOR:-nano}"
                if ! command -v "$EDITOR_CMD" >/dev/null 2>&1; then
                    EDITOR_CMD="vi"
                fi
                read -p "Open .env now in $EDITOR_CMD? (Y/n): " open_env
                if [[ ! "$open_env" =~ ^[Nn]$ ]]; then
                    "$EDITOR_CMD" .env
                fi
            else
                echo "❌ setup/.env.template not found!"
                exit 1
            fi
        fi

        if [ "$EXISTING_ENV_BEFORE_PROMPT" = true ]; then
            read -p "Detected .env existed before prompt. Re-create .setup-complete now and skip the wizard? (y/N): " recreate_setup
            if [[ "$recreate_setup" =~ ^[Yy]$ ]]; then
                touch .setup-complete
                echo ".setup-complete recreated from existing .env."
            fi
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

if [ "$DB_MODE" = "standalone" ]; then
    echo "🔌 Detected standalone database mode (API-only, no local DB container)"
    echo "   Database Type: $DB_TYPE"
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
    echo "🎯 First-time setup detected!"
    echo ""
    echo "Would you like to run optional diagnostics and dependency checks?"
    echo "  This can take 1-2 minutes but helps validate your configuration."
    echo "  You can skip this and dependencies will be installed during Docker build."
    echo ""
    read -p "Run diagnostics and dependency checks? (y/N): " run_diagnostics
    
    if [[ "$run_diagnostics" =~ ^[Yy]$ ]]; then
        echo ""
        echo "Running diagnostics and dependency configuration..."
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
    else
        echo ""
        echo "Skipping diagnostics and dependency checks."
        echo "Dependencies will be installed during Docker container build."
    fi
    
    # Markiere Setup als abgeschlossen
    touch .setup-complete
    
    echo ""
    echo "🎉 First setup completed!"
    echo "🐳 Starting backend..."
    echo "🐳 Starte nun das Backend..."
    echo ""
    echo "========================================"
    echo "  API will be accessible at:"
    echo "  http://localhost:$PORT/docs"
    echo "========================================"
    echo ""
    echo "🌐 Browser will open automatically when API is ready..."
    echo ""
    
    # Start browser opening in background
    show_api_docs_delayed "$PORT" "120"
    
    echo ""
    docker compose --env-file .env -f "$COMPOSE_FILE" up --build
else
    echo "🐳 Starte Backend mit Docker Compose..."
    echo "Backend wird verfügbar sein auf: http://localhost:$PORT"
    echo ""

    show_main_menu "$PORT" "$COMPOSE_FILE"
fi
