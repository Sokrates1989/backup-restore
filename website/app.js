/**
 * Backup Manager Admin UI
 * 
 * Main application JavaScript for managing backup automation through the API.
 * This file handles tab loading, authentication, and global UI functionality.
 */

// State
let adminToken = '';
let databases = [];
let remoteStorageLocations = [];
let backupSchedules = [];
let backupFiles = [];

const EPHEMERAL_KEY_TTL_MS = 15 * 60 * 1000;

// DOM Elements
const loginSection = document.getElementById('login-section');
const mainSection = document.getElementById('main-section');
const adminTokenInput = document.getElementById('admin-token');
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
 * Read a JSON value from sessionStorage.
 *
 * @param {string} key
 * @returns {any|null}
 */
function _getEphemeralCache(key) {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;
    try {
        return JSON.parse(raw);
    } catch {
        return null;
    }
}

/**
 * Store a JSON value in sessionStorage.
 *
 * @param {string} key
 * @param {any} value
 */
function _setEphemeralCache(key, value) {
    sessionStorage.setItem(key, JSON.stringify(value));
}

/**
 * Get a cached secret if it exists and is not expired.
 *
 * @param {string} keyName
 * @returns {string}
 */
function getEphemeralSecret(keyName) {
    const entry = _getEphemeralCache(keyName);
    if (!entry) return '';
    const expiresAt = Number(entry.expiresAt || 0);
    if (!expiresAt || Date.now() > expiresAt) {
        sessionStorage.removeItem(keyName);
        return '';
    }
    return trimValue(entry.value);
}

/**
 * Cache a secret in sessionStorage for a limited time.
 *
 * @param {string} keyName
 * @param {string} value
 * @param {number} ttlMs
 */
function setEphemeralSecret(keyName, value, ttlMs = EPHEMERAL_KEY_TTL_MS) {
    const v = trimValue(value);
    if (!v) {
        sessionStorage.removeItem(keyName);
        return;
    }
    _setEphemeralCache(keyName, { value: v, expiresAt: Date.now() + ttlMs });
}

/**
 * Prompt the user for the delete key once and cache it for 15 minutes.
 *
 * @returns {Promise<string>}
 */
async function getDeleteKey() {
    const cached = getEphemeralSecret('backup_delete_key');
    if (cached) return cached;

    const entered = trimValue(prompt('Enter Delete API Key (X-Delete-Key). It will be cached for 15 minutes:') || '');
    if (!entered) return '';
    setEphemeralSecret('backup_delete_key', entered);
    return entered;
}

window.getDeleteKey = getDeleteKey;

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
async function apiCall(endpoint, method = 'GET', body = null) {
    const suppressLogoutStatus = endpoint === '/automation/targets' && method === 'GET' && body === null;
    const options = {
        method,
        headers: {
            'X-Admin-Key': adminToken,
            'Content-Type': 'application/json'
        }
    };

    if (body) {
        options.body = JSON.stringify(body);
    }

    const response = await fetch(endpoint, options);
    
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const detail = data.detail || '';

        const looksLikeDeleteKeyError =
            typeof detail === 'string' &&
            (detail.toLowerCase().includes('x-delete-key') || detail.toLowerCase().includes('delete api key'));

        if ((response.status === 401 || response.status === 403) && !looksLikeDeleteKeyError) {
            handleLogout(!suppressLogoutStatus, 'error', 'Session expired or invalid token');
            throw new Error('Session expired or invalid token');
        }

        throw new Error(detail || `HTTP ${response.status}`);
    }

    return await response.json();
}

async function apiDeleteCall(endpoint) {
    const deleteKey = await getDeleteKey();
    if (!deleteKey) {
        throw new Error('Delete API key required');
    }

    const response = await fetch(endpoint, {
        method: 'DELETE',
        headers: {
            'X-Admin-Key': adminToken,
            'X-Delete-Key': deleteKey,
            'Content-Type': 'application/json'
        }
    });

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${response.status}`);
    }

    return await response.json().catch(() => ({}));
}

window.apiDeleteCall = apiDeleteCall;

// UI Functions
function setStatusMessage(el, message, type, persist) {
    if (!el) return;
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
        setTimeout(() => {
            el.classList.add('hidden');
        }, 5000);
    }
}

function showStatus(message, type = 'success', persist = null) {
    const shouldPersist = persist === null ? (type === 'error' || type === 'warning') : Boolean(persist);
    setStatusMessage(statusMessage, message, type, shouldPersist);
    setStatusMessage(statusMessageBottom, message, type, shouldPersist);
}

function showLogin() {
    loginSection.classList.remove('hidden');
    mainSection.classList.add('hidden');
    adminToken = '';
    localStorage.removeItem('backup_admin_token');
    // Hide logout button when logged out
    logoutBtn.style.display = 'none';
}

function showMain() {
    loginSection.classList.add('hidden');
    mainSection.classList.remove('hidden');
    // Show logout button when logged in
    logoutBtn.style.display = 'block';
}

// Track loaded scripts to avoid duplicate loading
const loadedScripts = new Set();

// Tab Navigation and Loading
async function loadTabContent(tabName) {
    try {
        const response = await fetch(`./${tabName}/${tabName}.html`);
        const html = await response.text();
        tabContentContainer.innerHTML = html;

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
                await loadRemoteStorageLocationsData();
                if (typeof updateBackupFilesStorageSelector === 'function') {
                    updateBackupFilesStorageSelector();
                }
                await loadBackupFilesData();
                if (typeof renderBackupFiles === 'function') {
                    renderBackupFiles();
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
async function handleLogin() {
    const token = adminTokenInput.value.trim();
    if (!token) {
        loginError.textContent = 'Please enter an API key';
        loginError.classList.remove('hidden');
        return;
    }

    adminToken = token;
    loginError.classList.add('hidden');

    // Test login by calling API
    try {
        await apiCall('/automation/targets');
        localStorage.setItem('backup_admin_token', token);
        showMain();
        showStatus('Login successful');
        
        // Load initial tab (databases)
        await switchTab('databases');
        
    } catch (error) {
        adminToken = '';
        loginError.textContent = error.message === 'Session expired or invalid token' ? 'Incorrect API key' : error.message;
        loginError.classList.remove('hidden');
    }
}

function handleLogout(showStatusMessage = true, statusType = 'success', statusText = 'Logged out') {
    showLogin();
    if (showStatusMessage) {
        showStatus(statusText, statusType, false);
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
document.addEventListener('DOMContentLoaded', () => {
    loadAndDisplayAppVersion();

    // Check for saved token
    const savedToken = localStorage.getItem('backup_admin_token');
    if (savedToken) {
        adminToken = savedToken;
        showMain();
        switchTab('databases');
    } else {
        // Hide logout button if not logged in
        logoutBtn.style.display = 'none';
    }
    
    // Event listeners
    loginBtn.addEventListener('click', handleLogin);
    logoutBtn.addEventListener('click', handleLogout);
    
    // Tab navigation
    tabs.forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });
    
    // Enter key on login
    adminTokenInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleLogin();
        }
    });
});
