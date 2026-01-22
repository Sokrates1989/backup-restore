/**
 * Keycloak Authentication Module for Backup Manager Frontend
 * 
 * This module provides Keycloak integration for the Backup Manager UI.
 * It handles login, logout, token refresh, and API authentication.
 * 
 * Dependencies:
 * - Keycloak JS adapter (loaded dynamically from Keycloak server or CDN)
 */

// Keycloak configuration - will be set from environment or defaults
const KEYCLOAK_CONFIG = {
    url: window.KEYCLOAK_URL || 'http://localhost:9090',
    realm: window.KEYCLOAK_REALM || 'backup-restore',
    clientId: window.KEYCLOAK_CLIENT_ID || 'backup-restore-frontend'
};

/**
 * Load a script tag dynamically.
 *
 * @param {string} src - Script URL to load.
 * @returns {Promise<void>} Resolves when the script loads.
 */
function loadScript(src) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.async = true;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
        document.head.appendChild(script);
    });
}

/**
 * Ensure the Keycloak JS adapter is loaded.
 *
 * @returns {Promise<boolean>} True if the adapter is loaded.
 */
async function loadKeycloakAdapter() {
    if (typeof Keycloak !== 'undefined') {
        return true;
    }

    const baseUrl = KEYCLOAK_CONFIG.url.replace(/\/$/, '');
    const sources = [
        '/keycloak-adapter.js',
        `${baseUrl}/js/keycloak.js`,
        `${baseUrl}/auth/js/keycloak.js`,
        'https://cdn.jsdelivr.net/npm/keycloak-js@26.0.0/dist/keycloak.min.js'
    ];

    for (const src of sources) {
        try {
            await loadScript(src);
            if (typeof Keycloak !== 'undefined') {
                return true;
            }
        } catch (error) {
            console.warn('[Keycloak] Adapter load failed:', error.message || error);
        }
    }

    return false;
}

// Keycloak instance
let keycloak = null;
let keycloakInitialized = false;
let keycloakEnabled = false;

/**
 * Check if Keycloak is enabled.
 * 
 * @returns {boolean} True if Keycloak authentication is enabled
 */
function isKeycloakEnabled() {
    return keycloakEnabled && keycloak !== null;
}

/**
 * Initialize Keycloak authentication.
 * 
 * @returns {Promise<boolean>} True if initialization was successful
 */
async function initKeycloak() {
    // Check if Keycloak is enabled via environment
    keycloakEnabled = window.KEYCLOAK_ENABLED === true || window.KEYCLOAK_ENABLED === 'true';
    
    if (!keycloakEnabled) {
        console.log('[Keycloak] Keycloak authentication is disabled');
        return false;
    }

    const adapterLoaded = await loadKeycloakAdapter();
    if (!adapterLoaded) {
        throw new Error('Keycloak JS adapter is not loaded. Rebuild the web image to include /keycloak-adapter.js or allow CDN access.');
    }

    try {
        console.log('[Keycloak] Initializing with config:', KEYCLOAK_CONFIG);
        
        keycloak = new Keycloak(KEYCLOAK_CONFIG);

        // Set up token refresh
        keycloak.onTokenExpired = () => {
            console.log('[Keycloak] Token expired, refreshing...');
            keycloak.updateToken(30).catch(() => {
                console.warn('[Keycloak] Token refresh failed, logging out');
                handleKeycloakLogout();
            });
        };

        // Initialize Keycloak
        const authenticated = await keycloak.init({
            onLoad: 'check-sso',
            silentCheckSsoRedirectUri: window.location.origin + '/silent-check-sso.html',
            pkceMethod: 'S256',
            checkLoginIframe: false
        });

        keycloakInitialized = true;
        
        if (authenticated) {
            console.log('[Keycloak] User is authenticated:', keycloak.tokenParsed?.preferred_username);
            return true;
        } else {
            console.log('[Keycloak] User is not authenticated');
            return false;
        }
    } catch (error) {
        console.error('[Keycloak] Initialization failed:', error);
        keycloakEnabled = false;
        return false;
    }
}

/**
 * Trigger Keycloak login flow.
 * 
 * @returns {Promise<void>}
 */
async function keycloakLogin() {
    if (!isKeycloakEnabled()) {
        throw new Error('Keycloak is not enabled or not initialized.');
    }

    try {
        await keycloak.login({
            redirectUri: window.location.origin + window.location.pathname
        });
    } catch (error) {
        console.error('[Keycloak] Login failed:', error);
        throw error;
    }
}

/**
 * Trigger Keycloak logout flow.
 * 
 * @returns {Promise<void>}
 */
async function keycloakLogout() {
    if (!isKeycloakEnabled()) {
        throw new Error('Keycloak is not enabled or not initialized.');
    }

    try {
        await keycloak.logout({
            redirectUri: window.location.origin + window.location.pathname
        });
    } catch (error) {
        console.error('[Keycloak] Logout failed:', error);
        throw error;
    }
}

/**
 * Handle logout (called when token refresh fails).
 */
function handleKeycloakLogout() {
    if (typeof handleLogout === 'function') {
        handleLogout(true, 'warning', 'Session expired, please login again');
    }
}

/**
 * Get the current access token.
 * 
 * @returns {Promise<string|null>} Access token or null if not authenticated
 */
async function getKeycloakToken() {
    if (!isKeycloakEnabled() || !keycloak.authenticated) {
        return null;
    }

    try {
        // Refresh token if it expires in the next 30 seconds
        await keycloak.updateToken(30);
        return keycloak.token;
    } catch (error) {
        console.error('[Keycloak] Failed to get token:', error);
        return null;
    }
}

/**
 * Check if user is authenticated via Keycloak.
 * 
 * @returns {boolean} True if authenticated
 */
function isKeycloakAuthenticated() {
    return isKeycloakEnabled() && keycloak?.authenticated === true;
}

/**
 * Get current user information from Keycloak token.
 * 
 * @returns {Object|null} User info object or null
 */
function getKeycloakUser() {
    if (!isKeycloakAuthenticated()) {
        return null;
    }

    const token = keycloak.tokenParsed;
    return {
        id: token.sub,
        username: token.preferred_username,
        email: token.email,
        name: token.name || token.preferred_username,
        roles: extractKeycloakRoles(token)
    };
}

/**
 * Extract roles from Keycloak token.
 * 
 * @param {Object} token Parsed JWT token
 * @returns {string[]} Array of role names
 */
function extractKeycloakRoles(token) {
    const roles = [];
    
    // Get roles from custom 'roles' claim
    if (token.roles && Array.isArray(token.roles)) {
        roles.push(...token.roles);
    }
    
    // Get roles from realm_access
    if (token.realm_access?.roles) {
        roles.push(...token.realm_access.roles);
    }
    
    // Get roles from resource_access
    if (token.resource_access) {
        Object.values(token.resource_access).forEach(client => {
            if (client.roles) {
                roles.push(...client.roles);
            }
        });
    }
    
    // Remove duplicates
    return [...new Set(roles)];
}

/**
 * Check if current user has a specific role.
 * 
 * @param {string} role Role name to check
 * @returns {boolean} True if user has the role
 */
function hasKeycloakRole(role) {
    const user = getKeycloakUser();
    return user?.roles?.includes(role) || false;
}

/**
 * Check if current user has any of the specified roles.
 * 
 * @param {string[]} roles Array of role names
 * @returns {boolean} True if user has at least one role
 */
function hasAnyKeycloakRole(roles) {
    const user = getKeycloakUser();
    if (!user?.roles) return false;
    return roles.some(role => user.roles.includes(role));
}

/**
 * Make an authenticated API call using Keycloak token.
 * 
 * @param {string} endpoint API endpoint
 * @param {string} method HTTP method
 * @param {Object|null} body Request body
 * @returns {Promise<Object>} Response data
 */
async function keycloakApiCall(endpoint, method = 'GET', body = null) {
    const token = await getKeycloakToken();
    
    if (!token) {
        throw new Error('Not authenticated');
    }

    const options = {
        method,
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    };

    if (body) {
        options.body = JSON.stringify(body);
    }

    const response = await fetch(endpoint, options);

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const detail = data.detail || `HTTP ${response.status}`;

        if (response.status === 401) {
            // Token might be invalid, try to refresh
            try {
                await keycloak.updateToken(-1); // Force refresh
                // Retry the request
                return keycloakApiCall(endpoint, method, body);
            } catch {
                handleKeycloakLogout();
                throw new Error('Session expired');
            }
        }

        throw new Error(detail);
    }

    return await response.json();
}

/**
 * Make an authenticated DELETE API call.
 * 
 * @param {string} endpoint API endpoint
 * @returns {Promise<Object>} Response data
 */
async function keycloakApiDeleteCall(endpoint) {
    // Check if user has delete permission
    if (!hasAnyKeycloakRole(['admin'])) {
        throw new Error('You do not have permission to delete. Required role: admin');
    }

    const token = await getKeycloakToken();
    
    if (!token) {
        throw new Error('Not authenticated');
    }

    const response = await fetch(endpoint, {
        method: 'DELETE',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    });

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${response.status}`);
    }

    return await response.json().catch(() => ({}));
}

/**
 * Make an authenticated restore API call.
 * 
 * @param {string} endpoint API endpoint
 * @param {Object} body Request body
 * @returns {Promise<Object>} Response data
 */
async function keycloakApiRestoreCall(endpoint, body) {
    // Check if user has restore permission
    if (!hasAnyKeycloakRole(['admin', 'operator'])) {
        throw new Error('You do not have permission to restore. Required role: admin or operator');
    }

    const token = await getKeycloakToken();
    
    if (!token) {
        throw new Error('Not authenticated');
    }

    const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(body || {})
    });

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${response.status}`);
    }

    return await response.json().catch(() => ({}));
}

// Export functions to global scope
window.initKeycloak = initKeycloak;
window.isKeycloakEnabled = isKeycloakEnabled;
window.isKeycloakAuthenticated = isKeycloakAuthenticated;
window.keycloakLogin = keycloakLogin;
window.keycloakLogout = keycloakLogout;
window.getKeycloakToken = getKeycloakToken;
window.getKeycloakUser = getKeycloakUser;
window.hasKeycloakRole = hasKeycloakRole;
window.hasAnyKeycloakRole = hasAnyKeycloakRole;
window.keycloakApiCall = keycloakApiCall;
window.keycloakApiDeleteCall = keycloakApiDeleteCall;
window.keycloakApiRestoreCall = keycloakApiRestoreCall;
