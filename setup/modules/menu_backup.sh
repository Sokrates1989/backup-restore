#!/bin/bash
#
# menu_backup.sh
#
# Backup operations module for Backup-Restore quick-start menu.
# This module provides functions for backup-related operations including
# running backups, listing backup files, and managing backup schedules.
#
# Author: Auto-generated
# Date: 2026-01-29
# Version: 1.0.0

get_keycloak_access_token() {
    # Retrieve a Keycloak access token using client credentials.
    #
    # Returns:
    #   Access token string via stdout.
    local access_token="${ACCESS_TOKEN:-}"
    local keycloak_url="${KEYCLOAK_URL:-}"
    local keycloak_realm="${KEYCLOAK_REALM:-}"
    local keycloak_client_id="${KEYCLOAK_CLIENT_ID:-}"
    local keycloak_client_secret="${KEYCLOAK_CLIENT_SECRET:-}"

    if [ -f ".env" ]; then
        keycloak_url=$(grep "^KEYCLOAK_URL=" .env | head -n1 | cut -d'=' -f2- | tr -d ' "')
        keycloak_realm=$(grep "^KEYCLOAK_REALM=" .env | head -n1 | cut -d'=' -f2- | tr -d ' "')
        keycloak_client_id=$(grep "^KEYCLOAK_CLIENT_ID=" .env | head -n1 | cut -d'=' -f2- | tr -d ' "')
        keycloak_client_secret=$(grep "^KEYCLOAK_CLIENT_SECRET=" .env | head -n1 | cut -d'=' -f2- | tr -d ' "')
    fi

    if [ -z "$access_token" ] && [ -n "$keycloak_url" ] && [ -n "$keycloak_realm" ] && [ -n "$keycloak_client_id" ] && [ -n "$keycloak_client_secret" ]; then
        local token_endpoint="${keycloak_url%/}/realms/${keycloak_realm}/protocol/openid-connect/token"
        local token_response
        token_response=$(curl -s -X POST "$token_endpoint" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            -d "grant_type=client_credentials" \
            -d "client_id=$keycloak_client_id" \
            -d "client_secret=$keycloak_client_secret")
        access_token=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" <<< "$token_response")
    fi

    if [ -z "$access_token" ]; then
        local prompt_token
        if [[ -r /dev/tty ]]; then
            read -r -p "Enter Keycloak access token: " prompt_token < /dev/tty
        else
            read -r -p "Enter Keycloak access token: " prompt_token
        fi
        access_token="$prompt_token"
    fi

    echo "$access_token"
}

handle_run_backup_now() {
    # Interactively runs a backup schedule via CLI.
    #
    # Args:
    #   $1: port - API port number.
    local port="$1"
    echo "⚡ Run Backup Now"
    echo ""
    
    # Check if API is running
    if ! curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "❌ API is not running. Please start the backend first."
        return 1
    fi
    
    local access_token
    access_token=$(get_keycloak_access_token)
    if [ -z "$access_token" ]; then
        echo "❌ Missing Keycloak access token."
        return 1
    fi
    
    # List schedules
    echo "📋 Fetching schedules..."
    local schedules_response
    schedules_response=$(curl -s -H "Authorization: Bearer $access_token" "http://localhost:$port/automation/schedules")
    
    if echo "$schedules_response" | grep -q "detail"; then
        echo "❌ Failed to fetch schedules. Check your access token."
        return 1
    fi
    
    echo ""
    echo "Available schedules:"
    echo "$schedules_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data:
        print('  No schedules configured. Use the web GUI to create one.')
    else:
        for i, s in enumerate(data, 1):
            print(f\"  {i}) {s.get('name', 'Unknown')} (ID: {s.get('id', 'N/A')[:8]}...)\")
except:
    print('  Error parsing response')
"
    
    echo ""
    local schedule_choice
    if [[ -r /dev/tty ]]; then
        read -r -p "Enter schedule number to run (or 'q' to cancel): " schedule_choice < /dev/tty
    else
        read -r -p "Enter schedule number to run (or 'q' to cancel): " schedule_choice
    fi
    
    if [ "$schedule_choice" = "q" ]; then
        echo "Cancelled."
        return 0
    fi
    
    # Get schedule ID
    local schedule_id
    schedule_id=$(echo "$schedules_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    idx = int('$schedule_choice') - 1
    if 0 <= idx < len(data):
        print(data[idx].get('id', ''))
except:
    pass
")
    
    if [ -z "$schedule_id" ]; then
        echo "❌ Invalid selection."
        return 1
    fi
    
    echo ""
    echo "🚀 Running backup..."
    local result
    result=$(curl -s -X POST -H "Authorization: Bearer $access_token" \
        "http://localhost:$port/automation/schedules/$schedule_id/run-now")
    
    if echo "$result" | grep -q "backup_filename"; then
        echo "✅ Backup completed successfully!"
        echo "$result" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"   Filename: {data.get('backup_filename', 'N/A')}\")
except:
    pass
"
    else
        echo "❌ Backup failed:"
        echo "$result"
    fi
}

handle_list_backups() {
    # Lists available backup files.
    #
    # Args:
    #   $1: port - API port number.
    local port="$1"
    echo "📁 List Backup Files"
    echo ""
    
    # Check if API is running
    if ! curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "❌ API is not running. Please start the backend first."
        return 1
    fi
    
    local access_token
    access_token=$(get_keycloak_access_token)
    if [ -z "$access_token" ]; then
        echo "❌ Missing Keycloak access token."
        return 1
    fi

    echo "📋 Fetching backup files..."
    local response
    response=$(curl -s -H "Authorization: Bearer $access_token" "http://localhost:$port/backup/list")
    
    echo ""
    echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    files = data.get('files', [])
    if not files:
        print('  No backup files found.')
    else:
        print(f'  Found {len(files)} backup(s):')
        print('')
        for f in files:
            print(f\"  - {f.get('filename', 'Unknown')}\")
            print(f\"    Size: {f.get('size_mb', 'N/A')} MB | Created: {f.get('created_at', 'N/A')}\")
except Exception as e:
    print(f'  Error: {e}')
"
}

handle_open_backup_gui() {
    # Opens the Backup Manager GUI in the default browser.
    #
    # Args:
    #   $1: port - API port number.
    local port="$1"
    echo "🌐 Opening Backup Manager GUI..."
    echo ""
    local web_port="${WEB_PORT:-}"
    if [ -z "$web_port" ] && [ -f ".env" ]; then
        web_port=$(grep "^WEB_PORT=" .env 2>/dev/null | head -n1 | cut -d'=' -f2- | tr -d ' "')
    fi
    web_port="${web_port:-8086}"

    echo "   URL: http://localhost:${web_port}/"
    echo ""
    
    local url="http://localhost:${web_port}/"
    
    if command -v open &> /dev/null; then
        open "$url"
    elif command -v xdg-open &> /dev/null; then
        xdg-open "$url" &
    else
        echo "Please open $url in your browser"
    fi
}
