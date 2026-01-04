#!/bin/bash
#
# menu_handlers.sh
#
# Module for handling menu actions in quick-start script

read_prompt() {
    local prompt="$1"
    local var_name="$2"

    if [[ -r /dev/tty ]]; then
        read -r -p "$prompt" "$var_name" < /dev/tty
    else
        read -r -p "$prompt" "$var_name"
    fi
}

open_browser_incognito() {
    local port="$1"
    local compose_file="$2"

    local api_url="http://localhost:$port/docs"
    local neo4j_url="http://localhost:7474"
    local urls=("$api_url")

    if [[ "$compose_file" == *neo4j* ]]; then
        urls+=("$neo4j_url")
        echo "Neo4j Browser will open at $neo4j_url using the same private window."
    fi

    echo "Opening browser..."

    local profile_base="${TMPDIR:-/tmp}"
    local edge_profile="${profile_base}/edge_incog_profile_backup_restore"
    local chrome_profile="${profile_base}/chrome_incog_profile_backup_restore"
    mkdir -p "$edge_profile" "$chrome_profile"

    # Best-effort: close prior windows using this profile so only fresh tabs remain
    stop_incognito_profile_procs() {
        local profile_dir="$1"; shift || true
        [ -z "$profile_dir" ] && return 0
        [ $# -eq 0 ] && return 0
        for pname in "$@"; do
            pkill -f "$pname.*--user-data-dir=$profile_dir" >/dev/null 2>&1 || true
        done
    }

    if command -v microsoft-edge &> /dev/null; then
        stop_incognito_profile_procs "$edge_profile" "microsoft-edge"
        microsoft-edge --inprivate --user-data-dir="$edge_profile" "${urls[@]}" >/dev/null 2>&1 &
        return
    fi

    if command -v google-chrome &> /dev/null; then
        stop_incognito_profile_procs "$chrome_profile" "chrome" "google-chrome"
        google-chrome --incognito --user-data-dir="$chrome_profile" "${urls[@]}" >/dev/null 2>&1 &
        return
    fi

    if command -v chromium-browser &> /dev/null; then
        chromium-browser --incognito "${urls[@]}" >/dev/null 2>&1 &
        return
    fi

    if command -v open &> /dev/null; then
        open -na "Google Chrome" --args --incognito --user-data-dir="$chrome_profile" "${urls[@]}" 2>/dev/null || \
        open -na "Safari" --args --private "${urls[@]}" 2>/dev/null || \
        open "${urls[0]}"
        return
    fi

    if command -v xdg-open &> /dev/null; then
        for url in "${urls[@]}"; do
            xdg-open "$url" &
        done
    else
        echo "Could not detect browser command. Please open manually: $api_url"
        if [[ "$compose_file" == *neo4j* ]]; then
            echo "Neo4j Browser: $neo4j_url"
        fi
    fi
}

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
    
    # Open browser in incognito/private mode using shared window
    open_browser_incognito "$port" "$compose_file"
    
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
    
    # Open browser in incognito/private mode using shared window
    open_browser_incognito "$port" "$compose_file"
    
    echo ""
    docker compose --env-file .env -f "$compose_file" up --build
}

handle_environment_diagnostics() {
    echo "🔍 Running Docker/build diagnostics..."
    local diagnostics_script="python-dependency-management/scripts/run-docker-build-diagnostics.sh"
    if [ -f "$diagnostics_script" ]; then
        ./$diagnostics_script
    else
        echo "❌ $diagnostics_script not found"
    fi
}

handle_rerun_setup_wizard() {
    echo "🔁 Re-running the interactive setup wizard"
    echo ""
    echo "To launch the wizard again, delete the .setup-complete file and restart quick-start."
    echo "The wizard automatically backs up your current .env before writing a new one."
    echo ""

    if [ ! -f .setup-complete ]; then
        echo ".setup-complete is already missing. The next quick-start run will start the wizard automatically."
    fi

    read_prompt "Delete .setup-complete and restart ./quick-start.sh now? (y/N): " rerun_choice
    if [[ ! "$rerun_choice" =~ ^[Yy]$ ]]; then
        echo "No changes were made. Remove .setup-complete manually and run ./quick-start.sh when you're ready."
        return 1
    fi

    if [ -f .setup-complete ]; then
        rm -f .setup-complete
        echo ".setup-complete removed."
    else
        echo ".setup-complete was not found, continuing."
    fi

    echo "Restarting ./quick-start.sh so you can walk through the wizard again..."
    ./quick-start.sh
    exit $?
}

handle_docker_compose_down() {
    local compose_file="$1"
    
    echo "🛑 Stoppe und entferne Container..."
    echo "   Using compose file: $compose_file"
    echo ""
    docker compose --env-file .env -f "$compose_file" down --remove-orphans
    echo ""
    echo "✅ Container gestoppt und entfernt"
}

handle_backend_start_no_cache() {
    local port="$1"
    local compose_file="$2"
    
    echo "🚀 Starte Backend direkt (mit --no-cache)..."
    echo ""
    echo "========================================"
    echo "  API will be accessible at:"
    echo "  http://localhost:$port/docs"
    echo "========================================"
    echo ""
    echo "Press ENTER to open the API documentation in your browser..."
    echo "(The API may take a few seconds to start. Please refresh the page if needed.)"
    read -r
    
    # Open browser in incognito/private mode using shared window
    open_browser_incognito "$port" "$compose_file"
    
    echo ""
    docker compose --env-file .env -f "$compose_file" build --no-cache
    docker compose --env-file .env -f "$compose_file" up
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

    local summary_msg=""
    local exit_code=0
    local choice

    while true; do
        local MENU_NEXT=1
        local MENU_START=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))
        local MENU_START_NO_CACHE=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))
        local MENU_START_BOTH=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))

        local MENU_DOWN=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))
        local MENU_DEP_MGMT=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))
        local MENU_DIAGNOSTICS=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))

        local MENU_BUILD=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))
        local MENU_CICD=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))
        local MENU_BUMP_VERSION=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))

        local MENU_SETUP=$MENU_NEXT; MENU_NEXT=$((MENU_NEXT+1))

        local MENU_EXIT=$MENU_NEXT

        echo ""
        echo "================ Main Menu ================"
        echo ""
        echo "Start:"
        echo "  ${MENU_START}) Backend direkt starten (docker compose up)"
        echo "  ${MENU_START_NO_CACHE}) Backend starten mit --no-cache (behebt Caching-Probleme)"
        echo "  ${MENU_START_BOTH}) Beides - Dependency Management und dann Backend starten"
        echo ""
        echo "Maintenance:"
        echo "  ${MENU_DOWN}) Docker Compose Down (Container stoppen und entfernen)"
        echo "  ${MENU_DEP_MGMT}) Nur Dependency Management öffnen"
        echo "  ${MENU_DIAGNOSTICS}) Docker/Build Diagnose ausführen"
        echo ""
        echo "Build / CI/CD:"
        echo "  ${MENU_BUILD}) Production Docker Image bauen"
        echo "  ${MENU_CICD}) CI/CD Pipeline einrichten"
        echo "  ${MENU_BUMP_VERSION}) Bump release version for docker image"
        echo ""
        echo "Setup:"
        echo "  ${MENU_SETUP}) Re-run setup wizard"
        echo ""
        echo "  ${MENU_EXIT}) Exit"
        echo ""

        read_prompt "Deine Wahl (1-${MENU_EXIT}): " choice

        case $choice in
          ${MENU_START})
            handle_backend_start "$port" "$compose_file"
            summary_msg="Backend start ausgelöst (docker compose up)"
            break
            ;;
          ${MENU_START_NO_CACHE})
            handle_backend_start_no_cache "$port" "$compose_file"
            summary_msg="Backend start mit --no-cache ausgelöst"
            break
            ;;
          ${MENU_START_BOTH})
            handle_dependency_and_backend "$port" "$compose_file"
            summary_msg="Dependency Management und Backendstart ausgeführt"
            break
            ;;
          ${MENU_DOWN})
            handle_docker_compose_down "$compose_file"
            summary_msg="Docker Compose Down ausgeführt"
            break
            ;;
          ${MENU_DEP_MGMT})
            handle_dependency_management
            echo "💡 Um das Backend zu starten, führe aus: docker compose -f $compose_file up --build"
            summary_msg="Dependency Management ausgeführt"
            break
            ;;
          ${MENU_DIAGNOSTICS})
            handle_environment_diagnostics
            summary_msg="Docker/Build Diagnose gestartet"
            break
            ;;
          ${MENU_BUILD})
            handle_build_production_image
            summary_msg="Production Docker Image Build ausgeführt"
            break
            ;;
          ${MENU_CICD})
            handle_cicd_setup
            summary_msg="CI/CD Setup ausgeführt"
            break
            ;;
          ${MENU_BUMP_VERSION})
            update_image_version
            summary_msg="IMAGE_VERSION aktualisiert"
            break
            ;;
          ${MENU_SETUP})
            handle_rerun_setup_wizard
            summary_msg="Setup wizard restarted"
            break
            ;;
          ${MENU_EXIT})
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
