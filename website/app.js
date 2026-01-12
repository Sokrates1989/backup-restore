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

function trimValue(value) {
    if (value === null || value === undefined) return '';
    return String(value).trim();
}

function clearStatusMessages() {
    if (statusMessage) statusMessage.classList.add('hidden');
    if (statusMessageBottom) statusMessageBottom.classList.add('hidden');
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
        if (response.status === 401 || response.status === 403) {
            handleLogout(!suppressLogoutStatus, 'error', 'Session expired or invalid token');
            throw new Error('Session expired or invalid token');
        }
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${response.status}`);
    }

    return await response.json();
}

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
            clearStatusMessages();
        };
    }

    if (!persist) {
        setTimeout(() => {
            el.classList.add('hidden');
        }, 5000);
    }
}

function showStatus(message, type = 'success', persist = null) {
    const shouldPersist = type === 'error' || type === 'warning';
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

// Tab Navigation and Loading
async function loadTabContent(tabName) {
    try {
        const response = await fetch(`./${tabName}/${tabName}.html`);
        const html = await response.text();
        tabContentContainer.innerHTML = html;
        
        // Load and initialize tab-specific JavaScript
        const script = document.createElement('script');
        script.src = `./${tabName}/${tabName}.js`;
        script.onload = () => {
            // Initialize the tab after script loads
            initializeTab(tabName);
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
                await loadDatabases();
                break;
            case 'remote-storage-locations':
                await loadRemoteStorageLocations();
                break;
            case 'backup-schedules':
                await loadBackupSchedules();
                break;
            case 'backup-files':
                await loadBackupFiles();
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

// Global data loading functions (used by tab scripts)
async function loadDatabases() {
    databases = await apiCall('/automation/targets');
}

async function loadRemoteStorageLocations() {
    remoteStorageLocations = await apiCall('/automation/destinations');
}

async function loadBackupSchedules() {
    backupSchedules = await apiCall('/automation/schedules');
}

async function loadBackupFiles() {
    // Load both local backup files and backup runs from automation
    const [localBackups, backupRuns] = await Promise.all([
        apiCall('/backup/list'),
        apiCall('/automation/runs')
    ]);
    
    backupFiles = localBackups.files || [];
}

// Update schedule selects (used by schedules tab)
function updateScheduleSelects() {
    // This function will be called by tab scripts when needed
    // The actual implementation is in backup-schedules.js
}

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
