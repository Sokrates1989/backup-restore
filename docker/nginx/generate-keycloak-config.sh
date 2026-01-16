#!/bin/sh
# Generate keycloak-config.js from environment variables
# This script runs at container startup before nginx starts

CONFIG_FILE="/usr/share/nginx/html/keycloak-config.js"

# Generate the config file
cat > "$CONFIG_FILE" << EOF
/**
 * Keycloak Configuration (auto-generated at container startup)
 */
window.KEYCLOAK_ENABLED = ${KEYCLOAK_ENABLED:-false};
window.KEYCLOAK_URL = '${KEYCLOAK_URL:-http://localhost:9090}';
window.KEYCLOAK_REALM = '${KEYCLOAK_REALM:-backup-restore}';
window.KEYCLOAK_CLIENT_ID = '${KEYCLOAK_CLIENT_ID:-backup-restore-frontend}';
EOF

echo "[keycloak-config] Generated $CONFIG_FILE with KEYCLOAK_ENABLED=${KEYCLOAK_ENABLED:-false}"

# Execute the original command (nginx)
exec "$@"
