#!/bin/bash
#
# menu_handlers.sh
#
# Module for handling menu actions in quick-start script

handle_backend_start() {
    local port="$1"
    local compose_file="$2"
    
    echo "🚀 Starte Backend direkt..."
    echo ""
    echo "========================================"
    echo "  API will be accessible at:"
    echo "  http://localhost:$port/docs"
    echo "========================================"
    echo ""
    echo "Press ENTER to open the API documentation in your browser..."
    echo "(The API may take a few seconds to start. Please refresh the page if needed.)"
    read -r
    
    # Open browser in incognito/private mode
    echo "Opening browser..."
    if command -v xdg-open &> /dev/null; then
        xdg-open "http://localhost:$port/docs" &
    elif command -v open &> /dev/null; then
        open -na "Google Chrome" --args --incognito "http://localhost:$port/docs" 2>/dev/null || \
        open -na "Safari" --args --private "http://localhost:$port/docs" 2>/dev/null || \
        open "http://localhost:$port/docs"
    else
        echo "Could not detect browser command. Please open manually: http://localhost:$port/docs"
    fi
    
    echo ""
    docker compose --env-file .env -f "$compose_file" up --build
}

handle_dependency_management() {
    echo "📦 Öffne Dependency Management..."
    ./python-dependency-management/scripts/manage-python-project-dependencies.sh
    echo ""
    echo "ℹ️  Dependency Management beendet."
}

handle_dependency_and_backend() {
    local port="$1"
    local compose_file="$2"
    
    echo "📦 Öffne zuerst Dependency Management..."
    ./python-dependency-management/scripts/manage-python-project-dependencies.sh
    echo ""
    echo "🚀 Starte nun das Backend..."
    echo ""
    echo "========================================"
    echo "  API will be accessible at:"
    echo "  http://localhost:$port/docs"
    echo "========================================"
    echo ""
    echo "Press ENTER to open the API documentation in your browser..."
    echo "(The API may take a few seconds to start. Please refresh the page if needed.)"
    read -r
    
    # Open browser in incognito/private mode
    echo "Opening browser..."
    if command -v xdg-open &> /dev/null; then
        xdg-open "http://localhost:$port/docs" &
    elif command -v open &> /dev/null; then
        open -na "Google Chrome" --args --incognito "http://localhost:$port/docs" 2>/dev/null || \
        open -na "Safari" --args --private "http://localhost:$port/docs" 2>/dev/null || \
        open "http://localhost:$port/docs"
    else
        echo "Could not detect browser command. Please open manually: http://localhost:$port/docs"
    fi
    
    echo ""
    docker compose --env-file .env -f "$compose_file" up --build
}

handle_environment_diagnostics() {
    echo "🔍 Starte Systemdiagnose für Docker-Setup..."
    local diagnostics_script="python-dependency-management/scripts/run-docker-build-diagnostics.sh"
    if [ -f "$diagnostics_script" ]; then
        ./"$diagnostics_script"
    else
        echo "❌ $diagnostics_script not found"
    fi
}

handle_build_production_image() {
    echo "🏗️  Building production Docker image..."
    echo ""
    if [ -f "build-image/docker-compose.build.yml" ]; then
        docker compose -f build-image/docker-compose.build.yml run --rm build-image
    else
        echo "❌ build-image/docker-compose.build.yml not found"
        echo "⚠️  Please ensure the build-image directory exists"
    fi
}

handle_cicd_setup() {
    echo "🚀 CI/CD Pipeline einrichten..."
    echo ""
    if [ -f "ci-cd/docker-compose.cicd-setup.yml" ]; then
        docker compose -f ci-cd/docker-compose.cicd-setup.yml run --rm cicd-setup
    else
        echo "❌ ci-cd/docker-compose.cicd-setup.yml not found"
        echo "⚠️  Please ensure the ci-cd directory exists"
    fi
}

show_main_menu() {
    local port="$1"
    local compose_file="$2"

    local has_cognito=0
    if declare -F run_cognito_setup >/dev/null; then
        has_cognito=1
    fi

    local summary_msg=""
    local exit_code=0
    local choice

    while true; do
        echo "Wähle eine Option:"
        echo "1) Backend direkt starten (docker compose up)"
        echo "2) Nur Dependency Management öffnen"
        echo "3) Beides - Dependency Management und dann Backend starten"
        echo "4) Docker/Build Diagnose ausführen"
        echo "5) AWS Cognito konfigurieren"
        echo "6) Production Docker Image bauen"
        echo "7) CI/CD Pipeline einrichten"
        echo "8) Bump release version for docker image"
        echo "9) Skript beenden"
        echo ""

        read -p "Deine Wahl (1-9): " choice

        case $choice in
          1)
            handle_backend_start "$port" "$compose_file"
            summary_msg="Backend start ausgelöst (docker compose up)"
            break
            ;;
          2)
            handle_dependency_management
            echo "💡 Um das Backend zu starten, führe aus: docker compose -f $compose_file up --build"
            summary_msg="Dependency Management ausgeführt"
            break
            ;;
          3)
            handle_dependency_and_backend "$port" "$compose_file"
            summary_msg="Dependency Management und Backendstart ausgeführt"
            break
            ;;
          4)
            handle_environment_diagnostics
            summary_msg="Docker/Build Diagnose gestartet"
            break
            ;;
          5)
            if [ $has_cognito -eq 1 ]; then
                run_cognito_setup
                echo ""
                summary_msg="AWS Cognito Setup ausgeführt"
            else
                echo "⚠️  AWS Cognito Modul wurde nicht geladen."
                echo "    Bitte stelle sicher, dass setup/modules/cognito_setup.sh eingebunden ist."
                summary_msg="AWS Cognito Setup konnte nicht ausgeführt werden"
                exit_code=1
            fi
            break
            ;;
          6)
            handle_build_production_image
            summary_msg="Production Docker Image Build ausgeführt"
            break
            ;;
          7)
            handle_cicd_setup
            summary_msg="CI/CD Setup ausgeführt"
            break
            ;;
          8)
            update_image_version
            summary_msg="IMAGE_VERSION aktualisiert"
            break
            ;;
          9)
            echo "👋 Skript wird beendet."
            exit 0
            ;;
          *)
            echo "❌ Ungültige Auswahl. Bitte erneut versuchen."
            echo ""
            continue
            ;;
        esac
    done

    echo ""
    if [ -n "$summary_msg" ]; then
        echo "✅ $summary_msg"
    fi
    echo "ℹ️  Quick-Start beendet. Für weitere Aktionen bitte erneut aufrufen."
    echo ""
    exit $exit_code
}
