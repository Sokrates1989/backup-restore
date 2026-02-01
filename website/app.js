/**
 * Backup Manager Admin UI
 * 
 * Main application JavaScript for managing backup automation through the API.
 * This file handles tab loading, authentication, and global UI functionality.
 */

// State
let databases = [];
let remoteStorageLocations = [];
let backupSchedules = [];
let backupFiles = [];

const DEV_LIVE_RELOAD_POLL_MS = 1200;
let _devLiveReloadInterval = null;
let _devLiveReloadWatchUrls = [];
let _devLiveReloadLastSignatures = new Map();

// DOM Elements
const loginSection = document.getElementById('login-section');
const mainSection = document.getElementById('main-section');
const loginBtn = document.getElementById('login-btn');
const loginError = document.getElementById('login-error');
const logoutBtn = document.getElementById('logout-btn');
const statusMessage = document.getElementById('status-message');
const statusMessageBottom = document.getElementById('status-message-bottom');
const tabContentContainer = document.getElementById('tab-content-container');

/**
 * Trim a value to remove whitespace.
 *
 * @param {any} value
 * @returns {string}
 */
function trimValue(value) {
    if (value === null || value === undefined) return '';
    return String(value).trim();
}

/**
 * Check if dev live reload should run.
 *
 * @returns {boolean} True when running in dev mode.
 */
function isDevLiveReloadEnabled() {
    return window.APP_IS_DEV === true;
}

/**
 * Build a signature string for a HEAD request.
 *
 * @param {Headers} headers Response headers.
 * @returns {string} Signature string.
 */
function buildDevLiveReloadSignature(headers) {
    if (!headers) return '';
    return (
        headers.get('etag') ||
        headers.get('last-modified') ||
        `${headers.get('content-length') || ''}:${headers.get('date') || ''}`
    );
}

/**
 * Fetch a resource HEAD signature to detect modifications.
 *
 * @param {string} url Resource URL.
 * @returns {Promise<string>} Signature.
 */
async function fetchDevLiveReloadSignature(url) {
    const response = await fetch(url, { method: 'HEAD', cache: 'no-store' });
    if (!response.ok) return '';
    return buildDevLiveReloadSignature(response.headers);
}

/**
 * Normalize a watch URL to a stable absolute URL string.
 *
 * @param {string} url Raw URL.
 * @returns {string} Absolute URL.
 */
function normalizeDevLiveReloadUrl(url) {
    try {
        return new URL(url, window.location.href).toString();
    } catch {
        return url;
    }
}

/**
 * Update the current set of watched URLs (deduped).
 *
 * @param {string[]} urls URLs to watch.
 * @returns {void}
 */
function setDevLiveReloadWatchUrls(urls) {
    const normalized = (urls || []).map(normalizeDevLiveReloadUrl);
    _devLiveReloadWatchUrls = [...new Set(normalized)];
}

/**
 * Add one URL to the watch list.
 *
 * @param {string} url URL to add.
 * @returns {void}
 */
function addDevLiveReloadWatchUrl(url) {
    setDevLiveReloadWatchUrls([..._devLiveReloadWatchUrls, url]);
}

/**
 * Poll watched URLs once and refresh the page when a signature changes.
 *
 * @returns {Promise<void>}
 */
async function pollDevLiveReloadOnce() {
    if (!isDevLiveReloadEnabled()) return;
    if (_devLiveReloadWatchUrls.length === 0) return;

    for (const url of _devLiveReloadWatchUrls) {
        try {
            const signature = await fetchDevLiveReloadSignature(url);
            if (!signature) continue;

            const previous = _devLiveReloadLastSignatures.get(url);
            if (previous && previous !== signature) {
                window.location.reload();
                return;
            }
            if (!previous) {
                _devLiveReloadLastSignatures.set(url, signature);
            }
        } catch {
        }
    }
}

/**
 * Start dev live reload polling.
 *
 * @returns {void}
 */
function startDevLiveReload() {
    if (!isDevLiveReloadEnabled()) return;
    if (_devLiveReloadInterval) return;

    setDevLiveReloadWatchUrls([
        '/',
        './styles.css',
        './app.js'
    ]);

    pollDevLiveReloadOnce();
    _devLiveReloadInterval = setInterval(pollDevLiveReloadOnce, DEV_LIVE_RELOAD_POLL_MS);
}

/**
 * Add the currently selected tab assets to the dev live reload watch list.
 *
 * @param {string} tabName Tab name.
 * @returns {void}
 */
function updateDevLiveReloadForTab(tabName) {
    if (!isDevLiveReloadEnabled()) return;
    if (!tabName) return;
    addDevLiveReloadWatchUrl(`./${tabName}/${tabName}.html`);
    addDevLiveReloadWatchUrl(`./${tabName}/${tabName}.js`);
}

/**
 * Hide global status messages.
 *
 * @param {boolean} force When true, also hides error/warning banners.
 */
function clearStatusMessages(force = false) {
    const shouldPreserve = (el) => {
        if (!el) return false;
        if (force) return false;
        return el.classList.contains('error') || el.classList.contains('warning');
    };

    if (statusMessage && !shouldPreserve(statusMessage)) statusMessage.classList.add('hidden');
    if (statusMessageBottom && !shouldPreserve(statusMessageBottom)) statusMessageBottom.classList.add('hidden');
}

window.clearStatusMessages = clearStatusMessages;
window.trimValue = trimValue;

async function loadAndDisplayAppVersion() {
    const versionEl = document.getElementById('app-version');
    if (!versionEl) return;

    const setVersion = (rawVersion) => {
        const version = trimValue(rawVersion) || 'unknown';
        versionEl.textContent = version;
        window.APP_VERSION = version;

        const versionLower = version.toLowerCase();
        window.APP_IS_DEV = versionLower === 'dev' || versionLower.includes('local');

        window.dispatchEvent(new Event('appVersionLoaded'));
    };

    try {
        const response = await fetch('./version.json', { cache: 'no-store' });
        if (response.ok) {
            const data = await response.json();
            setVersion(data.version);
            return;
        }
    } catch {
    }

    try {
        const response = await fetch('/version', { cache: 'no-store' });
        if (response.ok) {
            const data = await response.json();
            setVersion(data.IMAGE_TAG);
            return;
        }
    } catch {
    }

    setVersion('unknown');
}

// Tab Elements
const tabs = document.querySelectorAll('.tab');

// API Functions
/**
 * Execute an authenticated API call via Keycloak.
 *
 * @param {string} endpoint API endpoint.
 * @param {string} method HTTP method.
 * @param {Object|null} body Optional request body.
 * @returns {Promise<Object>} Parsed JSON response.
 */
async function apiCall(endpoint, method = 'GET', body = null) {
    if (typeof keycloakApiCall !== 'function') {
        throw new Error('Keycloak authentication is required but not available.');
    }

    return await keycloakApiCall(endpoint, method, body);
}

// UI Functions
function setStatusMessage(el, message, type, persist) {
    if (!el) return;
    if (el._hideTimeout) {
        clearTimeout(el._hideTimeout);
        el._hideTimeout = null;
    }
    const textEl = el.querySelector('.status-text');
    const closeEl = el.querySelector('.status-close');
    if (textEl) {
        textEl.textContent = message;
    } else {
        el.textContent = message;
    }

    el.className = `status ${type}`;
    el.classList.remove('hidden');

    if (closeEl) {
        closeEl.onclick = () => {
            clearStatusMessages(true);
        };
    }

    if (!persist) {
        el._hideTimeout = setTimeout(() => {
            el.classList.add('hidden');
            el._hideTimeout = null;
        }, 3500);
    }
}

function showStatus(message, type = 'success', persist = null) {
    const shouldPersist = persist === null ? (type === 'error' || type === 'warning') : Boolean(persist);
    setStatusMessage(statusMessage, message, type, shouldPersist);
    setStatusMessage(statusMessageBottom, message, type, shouldPersist);
}

/**
 * Show the login section and hide main content.
 *
 * @returns {void}
 */
function showLogin() {
    loginSection.classList.remove('hidden');
    mainSection.classList.add('hidden');
    // Hide logout button when logged out and reset text
    logoutBtn.classList.add('hidden');
    logoutBtn.textContent = 'Logout';
}

/**
 * Show the main application section.
 *
 * @returns {void}
 */
function showMain() {
    loginSection.classList.add('hidden');
    mainSection.classList.remove('hidden');
    // Show logout button when logged in
    logoutBtn.classList.remove('hidden');
    
    // Show username in logout button brackets
    if (typeof getKeycloakUser === 'function') {
        const user = getKeycloakUser();
        if (user && logoutBtn) {
            logoutBtn.textContent = `Logout (${user.username || 'User'})`;
        }
    }
    
    // Hide history tab if user doesn't have backup:history or backup:admin role
    updateHistoryTabVisibility();
}

/**
 * Update visibility of the history tab based on user roles.
 *
 * @returns {void}
 */
function updateHistoryTabVisibility() {
    const historyTab = document.querySelector('.tab[data-tab="history"]');
    if (!historyTab) return;
    
    if (typeof canViewHistory === 'function' && !canViewHistory()) {
        historyTab.classList.add('hidden');
    } else {
        historyTab.classList.remove('hidden');
    }
}

/**
 * Log a login event to the audit trail.
 * This is fire-and-forget; errors are logged but not shown to the user.
 *
 * @returns {Promise<void>}
 */
async function logLoginEvent() {
    try {
        await apiCall('/automation/audit/login', 'POST');
        console.log('[App] Login event logged to audit trail');
    } catch (error) {
        console.warn('[App] Failed to log login event:', error.message || error);
    }
}

// Track loaded scripts to avoid duplicate loading
const loadedScripts = new Set();

// Tab Navigation and Loading
async function loadTabContent(tabName) {
    try {
        const response = await fetch(`./${tabName}/${tabName}.html`);
        const html = await response.text();
        tabContentContainer.innerHTML = html;

        updateDevLiveReloadForTab(tabName);

        const tabRoot = tabContentContainer.querySelector('.tab-content');
        if (tabRoot) {
            tabRoot.classList.add('active');
            tabRoot.classList.remove('hidden');
        }
        
        // Check if script already loaded
        if (loadedScripts.has(tabName)) {
            // Script already loaded, just initialize
            initializeTab(tabName);
            return;
        }
        
        // Load and initialize tab-specific JavaScript
        const script = document.createElement('script');
        script.src = `./${tabName}/${tabName}.js`;
        script.onload = () => {
            loadedScripts.add(tabName);
            // Initialize the tab after script loads
            initializeTab(tabName);
        };
        script.onerror = () => {
            console.error(`Failed to load script for tab ${tabName}`);
            tabContentContainer.innerHTML += `<div class="status error">Error loading ${tabName} functionality.</div>`;
        };
        document.head.appendChild(script);
        
    } catch (error) {
        console.error(`Failed to load tab ${tabName}:`, error);
        tabContentContainer.innerHTML = `<div class="card"><p>Error loading ${tabName} tab content.</p></div>`;
    }
}

function initializeTab(tabName) {
    // Call tab-specific initialization function
    switch (tabName) {
        case 'databases':
            if (typeof initDatabasesTab === 'function') initDatabasesTab();
            break;
        case 'remote-storage-locations':
            if (typeof initRemoteStorageLocationsTab === 'function') initRemoteStorageLocationsTab();
            break;
        case 'backup-schedules':
            if (typeof initBackupSchedulesTab === 'function') initBackupSchedulesTab();
            break;
        case 'backup-files':
            if (typeof initBackupFilesTab === 'function') initBackupFilesTab();
            break;
        case 'history':
            if (typeof initHistoryTab === 'function') initHistoryTab();
            break;
    }
    
    // Load data for the tab
    loadTabData(tabName);
}

async function loadTabData(tabName) {
    try {
        switch (tabName) {
            case 'databases':
                await loadDatabasesData();
                if (typeof renderDatabases === 'function') {
                    renderDatabases();
                }
                break;
            case 'remote-storage-locations':
                await loadRemoteStorageLocationsData();
                if (typeof renderRemoteStorageLocations === 'function') {
                    renderRemoteStorageLocations();
                }
                break;
            case 'backup-schedules':
                await Promise.all([
                    loadDatabasesData(),
                    loadRemoteStorageLocationsData(),
                ]);
                await loadBackupSchedulesData();
                if (typeof renderBackupSchedules === 'function') {
                    renderBackupSchedules();
                }
                break;
            case 'backup-files':
                await Promise.all([
                    loadDatabasesData(),
                    loadRemoteStorageLocationsData(),
                ]);
                if (typeof updateBackupFilesDatabaseFilter === 'function') {
                    updateBackupFilesDatabaseFilter();
                }
                if (typeof updateBackupFilesStorageSelector === 'function') {
                    updateBackupFilesStorageSelector();
                }
                if (typeof loadBackupFiles === 'function') {
                    await loadBackupFiles();
                } else {
                    await loadBackupFilesData();
                    if (typeof renderBackupFiles === 'function') {
                        renderBackupFiles();
                    }
                }
                break;
            case 'history':
                await Promise.all([
                    loadDatabasesData(),
                    loadRemoteStorageLocationsData(),
                ]);
                if (typeof updateHistoryDatabaseFilter === 'function') {
                    updateHistoryDatabaseFilter();
                }
                if (typeof loadHistory === 'function') {
                    await loadHistory();
                }
                break;
        }
    } catch (error) {
        showStatus(`Failed to load ${tabName} data: ${error.message}`, 'error', true);
    }
}

// Tab Navigation
async function switchTab(tabName) {
    // Update active tab styling
    tabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });
    
    // Load tab content
    await loadTabContent(tabName);
}

// Event Handlers
/**
 * Trigger the Keycloak login flow.
 *
 * @returns {Promise<void>}
 */
async function handleLogin() {
    loginError.classList.add('hidden');

    if (typeof keycloakLogin !== 'function') {
        loginError.textContent = 'Keycloak is not available. Check configuration.';
        loginError.classList.remove('hidden');
        return;
    }

    try {
        await keycloakLogin();
    } catch (error) {
        loginError.textContent = `Login failed: ${error.message || error}`;
        loginError.classList.remove('hidden');
    }
}

/**
 * Trigger logout and reset the UI.
 *
 * @param {boolean} showStatusMessage Whether to show a status banner.
 * @param {string} statusType Status type for the banner.
 * @param {string} statusText Status text for the banner.
 * @returns {Promise<void>}
 */
async function handleLogout(showStatusMessage = true, statusType = 'success', statusText = 'Logged out') {
    if (typeof isKeycloakEnabled === 'function' && isKeycloakEnabled() && typeof keycloakLogout === 'function') {
        try {
            await keycloakLogout();
        } catch (error) {
            showStatus(`Logout failed: ${error.message || error}`, 'error', true);
        }
    }

    showLogin();
    if (showStatusMessage) {
        showStatus(statusText, statusType);
    }
}

// Global data loading functions (used only by app.js)
async function loadDatabasesData() {
    databases = await apiCall('/automation/targets');
}

async function loadRemoteStorageLocationsData() {
    remoteStorageLocations = await apiCall('/automation/destinations');
}

async function loadBackupSchedulesData() {
    backupSchedules = await apiCall('/automation/schedules');
}

async function loadBackupFilesData() {
    // Load both local backup files and backup runs from automation
    const [localBackups, backupRuns] = await Promise.all([
        apiCall('/backup/list'),
        apiCall('/automation/runs')
    ]);

    backupFiles = [];

    const localFiles = (localBackups && localBackups.files) ? localBackups.files : [];
    backupFiles = backupFiles.concat(localFiles.map(file => ({
        id: file.filename,
        ...file,
        type: 'local',
        source: 'Local Storage',
        destination_id: 'local'
    })));

    if (backupRuns && backupRuns.length > 0) {
        backupFiles = backupFiles.concat(backupRuns.map(run => ({
            id: run.id,
            filename: run.backup_filename || `backup_${run.id}`,
            created_at: run.created_at,
            size_mb: run.file_size_mb || 0,
            type: 'automation',
            source: `${run.target_name || 'Unknown'} → ${run.destination_name || 'Unknown'}`,
            status: run.status,
            schedule_name: run.schedule_name,
            destination_id: run.destination_id
        })));
    }
}

window.loadDatabasesData = loadDatabasesData;
window.loadRemoteStorageLocationsData = loadRemoteStorageLocationsData;
window.loadBackupSchedulesData = loadBackupSchedulesData;
window.loadBackupFilesData = loadBackupFilesData;

// Update schedule selects (used by schedules tab)
async function updateScheduleSelects() {
    try {
        await loadRemoteStorageLocationsData();
    } catch {
    }

    if (typeof window.updateBackupScheduleSelects === 'function') {
        window.updateBackupScheduleSelects();
    }
}

window.updateScheduleSelects = updateScheduleSelects;

// Initialize app
document.addEventListener('DOMContentLoaded', async () => {
    loadAndDisplayAppVersion();

    window.addEventListener('appVersionLoaded', () => {
        startDevLiveReload();
    });

    let keycloakAuthenticated = false;
    if (typeof initKeycloak !== 'function') {
        showLogin();
        showStatus('Keycloak authentication is required but not loaded.', 'error', true);
        setupEventListeners();
        return;
    }

    try {
        keycloakAuthenticated = await initKeycloak();
        if (keycloakAuthenticated) {
            console.log('[App] Keycloak authentication successful');
            const user = getKeycloakUser();
            if (user) {
                console.log('[App] Logged in as:', user.username, 'Roles:', user.roles);
            }
            showMain();
            await switchTab('databases');
            // Use only first name from display name, or username as fallback
            const displayName = user?.name || user?.username || 'User';
            const firstName = displayName.includes(' ') ? displayName.split(' ')[0] : displayName;
            showStatus(`Welcome, ${firstName}!`);
            
            // Log login event to audit trail (fire and forget)
            logLoginEvent();
            
            setupEventListeners();
            return;
        }
    } catch (error) {
        console.error('[App] Keycloak initialization failed:', error);
        showStatus(`Keycloak initialization failed: ${error.message || error}`, 'error', true);
    }

    showLogin();
    setupEventListeners();
});

/**
 * Set up event listeners for login, logout, and tab navigation.
 *
 * @returns {void}
 */
function setupEventListeners() {
    // Event listeners
    loginBtn.addEventListener('click', handleLogin);
    logoutBtn.addEventListener('click', handleLogout);
    
    // Tab navigation
    tabs.forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });
    
}
