#!/bin/bash
#
# menu_browser.sh
#
# Module for browser-related menu actions
# Uses shared browser_helpers.sh for incognito mode with first-run suppression
#

open_browser_incognito() {
    local port="$1"
    local compose_file="$2"
    local test_databases="$3"  # Optional: "test" or "admin" for special modes

    local api_url="http://localhost:$port/docs"
    local web_port="${WEB_PORT:-}"
    if [ -z "$web_port" ] && [ -f ".env" ]; then
        web_port=$(grep "^WEB_PORT=" .env 2>/dev/null | head -n1 | cut -d'=' -f2- | tr -d ' "')
    fi
    web_port="${web_port:-8086}"

    local gui_url="http://localhost:${web_port}/"
    local neo4j_url="http://localhost:7474"

    echo "Opening browser..."

    # Open main URLs using shared helper (suppresses first-run prompts)
    open_url "$gui_url"
    sleep 1
    open_url "$api_url"

    if [[ "$compose_file" == *neo4j* ]]; then
        sleep 1
        open_url "$neo4j_url"
        echo "Neo4j Browser will open at $neo4j_url"
    fi

    # Add test database admin UIs if in test mode
    if [[ "$test_databases" == "test" ]]; then
        echo ""
        echo "🌐 Opening browser with all admin UIs:"
        echo "  - Backup Manager: $gui_url"
        echo "  - API Docs: $api_url"
        echo "  - pgAdmin: http://localhost:5050"
        echo "  - phpMyAdmin: http://localhost:8080"
        echo "  - Neo4j Browser: http://localhost:7475"
        echo "  - Adminer: http://localhost:8082"
        echo "  - Adminer (SQLite): http://localhost:8085"
        echo "  - SQLite Web: http://localhost:8084"
        echo "  - SQLite Browser (GUI): http://localhost:8090"

        sleep 1
        open_url "http://localhost:5050"
        sleep 0.5
        open_url "http://localhost:8080"
        sleep 0.5
        open_url "http://localhost:7475/browser?connectURL=neo4j://localhost:7688"
        sleep 0.5
        open_url "http://localhost:8082"
        sleep 0.5
        open_url "http://localhost:8085"
        sleep 0.5
        open_url "http://localhost:8084"
        sleep 0.5
        open_url "http://localhost:8090"
    fi

    # Add admin UIs if in admin mode
    if [[ "$test_databases" == "admin" ]]; then
        echo ""
        echo "🌐 Opening browser with admin UIs:"
        echo "  - Backup Manager: $gui_url"
        echo "  - API Docs: $api_url"
        if [[ "$compose_file" == *postgres* ]]; then
            echo "  - pgAdmin (app DB): http://localhost:5051"
            sleep 1
            open_url "http://localhost:5051"
        fi
        if [[ "$compose_file" == *neo4j* ]]; then
            echo "  - Neo4j Browser: http://localhost:7474"
        fi
    fi
}
