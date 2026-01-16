/**
 * Keycloak Configuration
 * 
 * This file is generated/replaced by the nginx container at runtime
 * with values from environment variables.
 * 
 * For local development without Docker, these defaults are used.
 */

// Keycloak settings (can be overridden by environment)
window.KEYCLOAK_ENABLED = false;  // Set to true to enable Keycloak
window.KEYCLOAK_URL = 'http://localhost:9090';
window.KEYCLOAK_REALM = 'backup-restore';
window.KEYCLOAK_CLIENT_ID = 'backup-restore-frontend';
