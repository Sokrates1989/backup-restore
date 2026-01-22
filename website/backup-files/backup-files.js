/**
 * Backup Files Tab JavaScript
 * 
 * Handles backup file management for the Backup Manager.
 * Supports browsing local and remote storage locations.
 */

let currentStorageLocation = 'all';
let currentModalBackup = null;

const BACKUP_FILES_PAGE_SIZE = 10;
const BACKUP_FILES_DEFAULT_INITIAL_LIMIT = 5;
const BACKUP_FILES_DEFAULT_STEP_LIMIT = 10;
const BACKUP_FILES_INITIAL_LIMIT_STORAGE_KEY = 'backup_files_initial_limit';
const BACKUP_FILES_STEP_LIMIT_STORAGE_KEY = 'backup_files_step_limit';

let backupFilesVisibleLimit = BACKUP_FILES_PAGE_SIZE;
let backupFilesPagingState = null;

/**
 * Fetch with Keycloak bearer authentication.
 *
 * @param {string} url Request URL.
 * @param {RequestInit} options Fetch options.
 * @returns {Promise<Response>} Fetch response.
 */
async function fetchWithKeycloakAuth(url, options = {}) {
    if (typeof getKeycloakToken !== 'function') {
        throw new Error('Keycloak authentication is required but not available.');
    }

    const token = await getKeycloakToken();
    if (!token) {
        throw new Error('Not authenticated');
    }

    const headers = {
        ...(options.headers || {}),
        Authorization: `Bearer ${token}`
    };

    return fetch(url, { ...options, headers });
}

/**
 * Get the currently selected backup files sort mode.
 *
 * @returns {string} Sort mode key.
 */
function getBackupFilesSortValue() {
    return document.getElementById('backup-files-sort')?.value || 'newest';
}

/**
 * Normalize a limit value to a positive integer.
 *
 * @param {string|number|null|undefined} value Raw limit value.
 * @param {number} fallback Fallback value when invalid.
 * @returns {number} Normalized limit value.
 */
function parseBackupFilesLimit(value, fallback) {
    const parsed = parseInt(String(value ?? '').trim(), 10);
    if (!Number.isFinite(parsed) || parsed <= 0) {
        return fallback;
    }
    return parsed;
}

/**
 * Get a backup files limit value from storage or the UI.
 *
 * @param {string} selectId Select element id.
 * @param {string} storageKey Storage key to check.
 * @param {number} fallback Fallback value.
 * @returns {number} Limit value.
 */
function getBackupFilesLimitValue(selectId, storageKey, fallback) {
    const storedRaw = storageKey ? localStorage.getItem(storageKey) : null;
    if (storedRaw !== null && storedRaw !== undefined && String(storedRaw).trim() !== '') {
        const storedValue = parseBackupFilesLimit(storedRaw, fallback);
        const select = document.getElementById(selectId);
        if (select) {
            const match = [...select.options].find(option => {
                return parseBackupFilesLimit(option.value, fallback) === storedValue;
            });
            if (match) {
                select.value = match.value;
            }
        }
        return storedValue;
    }

    const selectValue = document.getElementById(selectId)?.value;
    return parseBackupFilesLimit(selectValue, fallback);
}

/**
 * Persist the currently selected backup files limit selection.
 *
 * @param {string} selectId Select element id.
 * @param {string} storageKey Storage key to update.
 * @param {number} fallback Fallback value.
 * @returns {void}
 */
function saveBackupFilesLimitSelection(selectId, storageKey, fallback) {
    if (!storageKey) return;
    const value = parseBackupFilesLimit(document.getElementById(selectId)?.value, fallback);
    localStorage.setItem(storageKey, String(value));
}

/**
 * Return the selected initial load limit.
 *
 * @returns {number} Initial load limit.
 */
function getBackupFilesInitialLimit() {
    return getBackupFilesLimitValue(
        'backup-files-initial-limit',
        BACKUP_FILES_INITIAL_LIMIT_STORAGE_KEY,
        BACKUP_FILES_DEFAULT_INITIAL_LIMIT
    );
}

/**
 * Return the selected step load limit.
 *
 * @returns {number} Step load limit.
 */
function getBackupFilesStepLimit() {
    return getBackupFilesLimitValue(
        'backup-files-step-limit',
        BACKUP_FILES_STEP_LIMIT_STORAGE_KEY,
        BACKUP_FILES_DEFAULT_STEP_LIMIT
    );
}

/**
 * Return true when the backup details modal is currently visible.
 *
 * @returns {boolean} True when visible.
 */
function isBackupDetailsModalOpen() {
    const modal = document.getElementById('backup-details-modal');
    return Boolean(modal && !modal.classList.contains('hidden'));
}

/**
 * Set status text inside the backup details modal.
 *
 * @param {string} message Status message.
 * @param {string} type Status type (success|info|warning|error).
 * @param {boolean|null} persist When true, do not auto-hide; when null, defaults to persisting errors/warnings.
 * @returns {void}
 */
function setBackupDetailsStatus(message, type = 'success', persist = null) {
    const el = document.getElementById('backup-details-status');
    if (!el) return;

    if (el._hideTimeout) {
        clearTimeout(el._hideTimeout);
        el._hideTimeout = null;
    }

    const shouldPersist = persist === null ? (type === 'error' || type === 'warning') : Boolean(persist);
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
            clearBackupDetailsStatus(true);
        };
    }

    if (!shouldPersist) {
        el._hideTimeout = setTimeout(() => {
            el.classList.add('hidden');
            el._hideTimeout = null;
        }, 3500);
    }
}

/**
 * Hide the backup details modal status banner.
 *
 * @param {boolean} force When true also hides persistent banners.
 * @returns {void}
 */
function clearBackupDetailsStatus(force = false) {
    const el = document.getElementById('backup-details-status');
    if (!el) return;

    if (el._hideTimeout) {
        clearTimeout(el._hideTimeout);
        el._hideTimeout = null;
    }

    if (!force && (el.classList.contains('error') || el.classList.contains('warning'))) {
        return;
    }

    el.classList.add('hidden');
}

/**
 * Reset pagination to the first page.
 *
 * @returns {void}
 */
function resetBackupFilesPagination() {
    backupFilesVisibleLimit = getBackupFilesInitialLimit();
    backupFilesPagingState = null;
}

/**
 * Show more items in the Backup Files list.
 *
 * @returns {Promise<void>} Resolves when finished.
 */
async function showMoreBackupFiles() {
    const stepLimit = getBackupFilesStepLimit();
    if (!backupFilesPagingState) {
        backupFilesVisibleLimit += stepLimit;
        renderBackupFiles();
        return;
    }

    const totals = getBackupFilesPagingTotals();
    if (totals.loaded > backupFilesVisibleLimit) {
        backupFilesVisibleLimit += stepLimit;
        renderBackupFiles();
        return;
    }

    await fetchMoreBackupFiles(stepLimit);
    backupFilesVisibleLimit += stepLimit;
    renderBackupFiles();
}

/**
 * Get source ids based on current storage selection.
 *
 * @param {string} location Storage location selection.
 * @returns {string[]} Source ids ("local" or destination ids).
 */
function getBackupFilesSourceIds(location) {
    const loc = String(location || '').trim() || 'all';
    if (loc === 'local') return ['local'];
    if (loc !== 'all') return [loc];

    const remoteIds = (Array.isArray(remoteStorageLocations) ? remoteStorageLocations : [])
        .filter(d => d && d.id && d.id !== 'local' && d.destination_type !== 'local')
        .map(d => String(d.id));

    return ['local', ...remoteIds];
}

/**
 * Create a paging state for the Backup Files tab.
 *
 * @param {string[]} sourceIds Source ids.
 * @returns {Object} Paging state.
 */
function createBackupFilesPagingState(sourceIds) {
    const sources = {};
    (Array.isArray(sourceIds) ? sourceIds : []).forEach(id => {
        sources[id] = {
            offset: 0,
            total: null,
            items: []
        };
    });

    return {
        sources,
        sourceIds: Array.isArray(sourceIds) ? sourceIds : [],
        roundRobinIndex: 0,
        loadAllActive: false,
        cancelLoadAllRequested: false
    };
}

/**
 * Compute aggregate paging totals.
 *
 * @returns {{loaded: number, total: number|null, remaining: number|null}} Totals.
 */
function getBackupFilesPagingTotals() {
    if (!backupFilesPagingState || !backupFilesPagingState.sources) {
        return { loaded: 0, total: null, remaining: null };
    }

    let loaded = 0;
    let total = 0;
    let totalKnown = true;

    Object.values(backupFilesPagingState.sources).forEach(s => {
        const items = Array.isArray(s.items) ? s.items : [];
        loaded += items.length;

        if (typeof s.total === 'number' && Number.isFinite(s.total)) {
            total += s.total;
        } else {
            totalKnown = false;
        }
    });

    if (!totalKnown) {
        return { loaded, total: null, remaining: null };
    }

    const remaining = Math.max(0, total - loaded);
    return { loaded, total, remaining };
}

/**
 * Return true when the paging state indicates there may be more items to load.
 *
 * When totals are unknown for one or more sources (e.g. sources not fetched yet), this
 * returns true so the UI continues to offer pagination actions.
 *
 * @returns {boolean} True when more items may be available.
 */
function hasMoreBackupFilesAvailable() {
    if (!backupFilesPagingState || !backupFilesPagingState.sources) {
        return false;
    }

    return Object.values(backupFilesPagingState.sources).some(s => {
        if (!s) return false;
        if (typeof s.total === 'number' && Number.isFinite(s.total)) {
            return (parseInt(s.offset, 10) || 0) < s.total;
        }
        return true;
    });
}

/**
 * Allocate a fetch budget across sources in round-robin fashion.
 *
 * @param {number} totalBudget Total items to fetch.
 * @returns {Object<string, number>} Map of sourceId -> limit.
 */
function allocateBackupFilesBudget(totalBudget) {
    const budget = {};
    if (!backupFilesPagingState || !Array.isArray(backupFilesPagingState.sourceIds)) {
        return budget;
    }

    const ids = backupFilesPagingState.sourceIds;
    ids.forEach(id => {
        budget[id] = 0;
    });

    let remaining = Math.max(0, parseInt(totalBudget, 10) || 0);
    if (remaining === 0 || ids.length === 0) return budget;

    let idx = backupFilesPagingState.roundRobinIndex || 0;
    let guard = 0;
    const maxSteps = remaining * Math.max(1, ids.length) + 50;

    while (remaining > 0 && guard < maxSteps) {
        guard += 1;
        const sourceId = ids[idx % ids.length];
        idx += 1;

        const s = backupFilesPagingState.sources[sourceId];
        if (!s) continue;

        if (typeof s.total === 'number' && Number.isFinite(s.total) && s.offset >= s.total) {
            continue;
        }

        budget[sourceId] = (budget[sourceId] || 0) + 1;
        remaining -= 1;
    }

    backupFilesPagingState.roundRobinIndex = idx % Math.max(1, ids.length);
    return budget;
}

/**
 * Fetch a page of backups for a single source.
 *
 * @param {string} sourceId Source id.
 * @param {number} limit Page size.
 * @param {string} selectedTargetId Optional database filter.
 * @param {string} selectedTargetFolder Optional folder filter for local backups.
 * @returns {Promise<void>} Resolves when finished.
 */
async function fetchBackupFilesSourcePage(sourceId, limit, selectedTargetId, selectedTargetFolder) {
    const s = backupFilesPagingState && backupFilesPagingState.sources ? backupFilesPagingState.sources[sourceId] : null;
    if (!s) return;

    const pageLimit = Math.max(1, parseInt(limit, 10) || 0);
    const offset = Math.max(0, parseInt(s.offset, 10) || 0);

    if (sourceId === 'local') {
        let url = `/backup/list?limit=${pageLimit}&offset=${offset}`;
        if (selectedTargetFolder) {
            url += `&prefix=${encodeURIComponent(`${selectedTargetFolder}/`)}`;
        }

        const resp = await apiCall(url);
        const files = (resp && resp.files) ? resp.files : [];
        const total = resp && (typeof resp.total === 'number' ? resp.total : resp.count);
        if (typeof total === 'number' && Number.isFinite(total)) {
            s.total = total;
        }

        s.offset = offset + (Array.isArray(files) ? files.length : 0);
        s.items = s.items.concat(
            (Array.isArray(files) ? files : []).map(file => ({
                id: file.filename,
                ...file,
                type: 'local',
                source: 'Local Storage',
                destination_id: 'local'
            }))
        );
        return;
    }

    let url = `/automation/destinations/${sourceId}/backups?include_total=true&limit=${pageLimit}&offset=${offset}`;
    if (selectedTargetId) {
        url += `&target_id=${encodeURIComponent(selectedTargetId)}`;
    }

    const resp = await apiCall(url);
    const wrapper = (resp && Array.isArray(resp.items)) ? resp : { items: Array.isArray(resp) ? resp : [], total: Array.isArray(resp) ? resp.length : 0 };
    const files = Array.isArray(wrapper.items) ? wrapper.items : [];

    if (typeof wrapper.total === 'number' && Number.isFinite(wrapper.total)) {
        s.total = wrapper.total;
    }

    s.offset = offset + files.length;
    const dest = (Array.isArray(remoteStorageLocations) ? remoteStorageLocations : []).find(d => d && String(d.id) === String(sourceId));
    const sourceName = dest ? dest.name : 'Remote Storage';

    s.items = s.items.concat(
        files.map(file => {
            const sizeBytes = typeof file.size === 'number' ? file.size : parseInt(String(file.size || '0'), 10) || 0;
            const sizeMb = sizeBytes ? Number((sizeBytes / 1024 / 1024).toFixed(2)) : 0;

            return {
                id: file.id || file.name,
                backup_id: file.id || file.name,
                filename: file.name,
                created_at: file.created_at,
                size_mb: sizeMb,
                type: 'remote',
                source: sourceName,
                destination_id: sourceId
            };
        })
    );
}

/**
 * Rebuild the global backupFiles list from the paging state.
 *
 * @returns {void}
 */
function rebuildBackupFilesFromPagingState() {
    const state = backupFilesPagingState;
    if (!state || !state.sources) {
        backupFiles = [];
        return;
    }

    let all = [];
    Object.values(state.sources).forEach(s => {
        if (Array.isArray(s.items) && s.items.length > 0) {
            all = all.concat(s.items);
        }
    });

    backupFiles = enrichBackups(all);
}

/**
 * Fetch more backups across sources.
 *
 * @param {number} totalBudget Total items to fetch.
 * @returns {Promise<void>} Resolves when done.
 */
async function fetchMoreBackupFiles(totalBudget) {
    if (!backupFilesPagingState) return;

    const selectedTargetId = getSelectedTargetId();
    const selectedTargetFolder = getSelectedTargetFolder();
    const allocations = allocateBackupFilesBudget(totalBudget);

    const ids = Object.keys(allocations);
    for (const sourceId of ids) {
        const lim = allocations[sourceId] || 0;
        if (lim <= 0) continue;
        try {
            await fetchBackupFilesSourcePage(sourceId, lim, selectedTargetId, selectedTargetFolder);
        } catch (error) {
            console.log(`Error loading backups for source ${sourceId}:`, error);
            const src = backupFilesPagingState && backupFilesPagingState.sources ? backupFilesPagingState.sources[sourceId] : null;
            if (src && (src.total === null || src.total === undefined)) {
                src.total = parseInt(src.offset, 10) || 0;
            }
        }
    }

    rebuildBackupFilesFromPagingState();
}

/**
 * Cancel an in-progress load-all operation.
 *
 * @returns {void}
 */
function cancelLoadAllBackupFiles() {
    if (!backupFilesPagingState) return;
    backupFilesPagingState.cancelLoadAllRequested = true;
}

/**
 * Load all backup files from the backend, with the ability to cancel.
 *
 * @returns {Promise<void>} Resolves when finished.
 */
async function loadAllBackupFiles() {
    if (!backupFilesPagingState || backupFilesPagingState.loadAllActive) return;

    backupFilesPagingState.loadAllActive = true;
    backupFilesPagingState.cancelLoadAllRequested = false;
    backupFilesVisibleLimit = Number.MAX_SAFE_INTEGER;
    renderBackupFiles();
    const stepLimit = getBackupFilesStepLimit();

    try {
        let guard = 0;
        while (!backupFilesPagingState.cancelLoadAllRequested) {
            guard += 1;
            if (guard > 10000) break;

            const totals = getBackupFilesPagingTotals();
            if (totals.total !== null && totals.remaining === 0) {
                break;
            }

            await fetchMoreBackupFiles(stepLimit);
            renderBackupFiles();

            await new Promise(resolve => setTimeout(resolve, 0));
        }
    } finally {
        if (backupFilesPagingState) {
            backupFilesPagingState.loadAllActive = false;
        }
        renderBackupFiles();
    }
}

/**
 * Parse a backup size value into a numeric megabytes value.
 *
 * @param {Object} backup Backup entry.
 * @returns {number} Size in MB (0 when unknown).
 */
function getBackupSizeMb(backup) {
    const raw = backup?.size_mb;
    if (typeof raw === 'number') return raw;
    const parsed = parseFloat(String(raw || ''));
    return Number.isFinite(parsed) ? parsed : 0;
}

/**
 * Parse a backup created_at into a timestamp.
 *
 * @param {Object} backup Backup entry.
 * @returns {number} Timestamp in ms since epoch.
 */
function getBackupCreatedAtMs(backup) {
    const t = new Date(backup?.created_at || 0).getTime();
    return Number.isFinite(t) ? t : 0;
}

/**
 * Determine if a backup is likely encrypted based on its filename.
 *
 * @param {Object} backup Backup entry.
 * @returns {boolean} True when encrypted.
 */
function isBackupEncrypted(backup) {
    const name = String(backup?.filename || backup?.name || '').toLowerCase();
    return name.endsWith('.enc');
}

/**
 * Determine compatible database types for a backup.
 *
 * @param {Object} backup Backup entry.
 * @returns {string[]} List of compatible db_type values.
 */
function getCompatibleDbTypesForBackup(backup) {
    const rawName = String(backup?.filename || backup?.name || '').toLowerCase();
    const name = rawName.endsWith('.enc') ? rawName.slice(0, -4) : rawName;

    if (name.endsWith('.cypher') || name.endsWith('.cypher.gz')) {
        return ['neo4j'];
    }
    if (name.endsWith('.db') || name.endsWith('.db.gz')) {
        return ['sqlite'];
    }
    if (name.endsWith('.dump') || name.endsWith('.dump.gz')) {
        return ['postgresql'];
    }
    if (name.endsWith('.sql') || name.endsWith('.sql.gz')) {
        return ['postgresql', 'mysql'];
    }
    return [];
}

function sanitizeName(value) {
    const raw = String(value || '').trim();
    if (!raw) return '';
    return raw
        .replace(/[^\w\-]/g, '_')
        .replace(/_+/g, '_')
        .replace(/^_+|_+$/g, '')
        .toLowerCase();
}

function updateBackupFilesDatabaseFilter() {
    const select = document.getElementById('backup-files-database-filter');
    if (!select) return;

    const current = select.value;
    select.innerHTML = '<option value="">All Databases</option>';

    if (Array.isArray(databases)) {
        databases
            .filter(d => d && d.id)
            .forEach(d => {
                select.innerHTML += `<option value="${d.id}">${d.name}</option>`;
            });
    }

    if ([...select.options].some(o => o.value === current)) {
        select.value = current;
    }
}

function getSelectedTargetId() {
    return document.getElementById('backup-files-database-filter')?.value || '';
}

function getSelectedTargetFolder() {
    const targetId = getSelectedTargetId();
    if (!targetId) return '';
    const t = Array.isArray(databases) ? databases.find(d => d && d.id === targetId) : null;
    return t ? sanitizeName(t.name) : '';
}

// Backup Files Management Functions
async function loadBackupFiles() {
    try {
        resetBackupFilesPagination();
        const location = document.getElementById('backup-files-storage-location')?.value || 'all';
        currentStorageLocation = location;
        const initialLimit = getBackupFilesInitialLimit();
        backupFilesVisibleLimit = initialLimit;

        const sourceIds = getBackupFilesSourceIds(location);
        backupFilesPagingState = createBackupFilesPagingState(sourceIds);

        await fetchMoreBackupFiles(initialLimit);
        renderBackupFiles();
    } catch (error) {
        showStatus(`Failed to load backup files: ${error.message}`, 'error', true);
    }
}

function enrichBackups(items) {
    const folderToDbName = new Map();
    if (Array.isArray(databases)) {
        databases.forEach(d => {
            if (!d || !d.name) return;
            folderToDbName.set(sanitizeName(d.name), d.name);
        });
    }

    return (Array.isArray(items) ? items : []).map(b => {
        const filename = String(b.filename || b.name || '');
        const parts = filename.split('/');
        const folder = parts.length > 1 ? parts[0] : '';
        const displayFilename = parts.length > 1 ? parts.slice(1).join('/') : filename;
        const dbName = folderToDbName.get(folder) || (folder ? folder : 'Unknown');

        return {
            ...b,
            filename,
            display_filename: displayFilename,
            db_folder: folder,
            db_name: dbName,
            status: 'available'
        };
    });
}

async function downloadBackupDelegated(type, destinationId, backupId, fallbackFilename) {
    if (type !== 'remote') {
        return await downloadBackup(fallbackFilename);
    }

    try {
        if (!destinationId || !backupId) {
            throw new Error('Missing destinationId or backupId');
        }

        const url = `/automation/destinations/${destinationId}/backups/download?backup_id=${encodeURIComponent(backupId)}&filename=${encodeURIComponent(fallbackFilename || '')}`;
        const response = await fetchWithKeycloakAuth(url);

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || `HTTP ${response.status}`);
        }

        const blob = await response.blob();
        const urlObj = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = urlObj;
        a.download = fallbackFilename || 'backup';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(urlObj);
        document.body.removeChild(a);

        if (isBackupDetailsModalOpen()) {
            setBackupDetailsStatus('Backup downloaded successfully', 'success');
        } else {
            showStatus('Backup downloaded successfully', 'success');
        }
    } catch (error) {
        if (isBackupDetailsModalOpen()) {
            setBackupDetailsStatus(`Failed to download backup: ${error.message}`, 'error', true);
        } else {
            showStatus(`Failed to download backup: ${error.message}`, 'error');
        }
    }
}

function updateBackupFilesStorageSelector() {
    const select = document.getElementById('backup-files-storage-location');
    if (!select) return;
    
    // Preserve current selection
    const currentValue = select.value;
    
    // Rebuild options
    let html = `
        <option value="all">All Locations (Local + Remote)</option>
        <option value="local">Local Storage Only</option>
    `;
    
    remoteStorageLocations
        .filter(location => location && location.id !== 'local' && location.destination_type !== 'local')
        .forEach(location => {
        const typeLabel = location.destination_type === 'local' ? '(Local Dir)' : 
                         location.destination_type === 'sftp' ? '(SFTP)' : 
                         location.destination_type === 'google_drive' ? '(Google Drive)' : '';
        html += `<option value="${location.id}">${location.name} ${typeLabel}</option>`;
    });
    
    select.innerHTML = html;
    
    // Restore selection if still valid
    if ([...select.options].some(opt => opt.value === currentValue)) {
        select.value = currentValue;
    }
}

/**
 * Render the backup files list and pagination controls.
 *
 * @returns {void}
 */
function renderBackupFiles() {
    const container = document.getElementById('backup-files-list');
    if (!container) return;
    
    if (backupFiles.length === 0) {
        container.innerHTML = '<p class="no-items">No backup files found. Run a backup to get started.</p>';
        return;
    }

    const selectedTargetFolder = getSelectedTargetFolder();
    const filteredBackups = selectedTargetFolder
        ? backupFiles.filter(b => (b.db_folder || '') === selectedTargetFolder)
        : [...backupFiles];

    const sortValue = getBackupFilesSortValue();

    const compareByString = (a, b) => String(a || '').localeCompare(String(b || ''), undefined, { sensitivity: 'base' });

    const sortedBackups = [...filteredBackups];
    if (sortValue === 'oldest') {
        sortedBackups.sort((a, b) => getBackupCreatedAtMs(a) - getBackupCreatedAtMs(b));
    } else if (sortValue === 'largest') {
        sortedBackups.sort((a, b) => getBackupSizeMb(b) - getBackupSizeMb(a));
    } else if (sortValue === 'smallest') {
        sortedBackups.sort((a, b) => getBackupSizeMb(a) - getBackupSizeMb(b));
    } else if (sortValue === 'destination') {
        sortedBackups.sort((a, b) => {
            const diff = compareByString(a.source, b.source);
            if (diff !== 0) return diff;
            return getBackupCreatedAtMs(b) - getBackupCreatedAtMs(a);
        });
    } else if (sortValue === 'type') {
        sortedBackups.sort((a, b) => {
            const diff = compareByString(a.type, b.type);
            if (diff !== 0) return diff;
            return getBackupCreatedAtMs(b) - getBackupCreatedAtMs(a);
        });
    } else {
        // default newest
        sortedBackups.sort((a, b) => getBackupCreatedAtMs(b) - getBackupCreatedAtMs(a));
    }

    const totals = getBackupFilesPagingTotals();
    const totalCount = sortedBackups.length;
    const visibleBackups = sortedBackups.slice(0, Math.max(0, backupFilesVisibleLimit));

    const hasMore = backupFilesPagingState
        ? (totals.remaining !== null ? totals.remaining > 0 : hasMoreBackupFilesAvailable())
        : (visibleBackups.length < totalCount);

    const initialLimit = getBackupFilesInitialLimit();
    const stepLimit = getBackupFilesStepLimit();
    const limitOptions = [5, 10, 25, 50, 100];

    /**
     * Render pagination option entries for the limit selectors.
     *
     * @param {number} selectedValue Currently selected limit value.
     * @returns {string} HTML options markup.
     */
    const renderLimitOptions = (selectedValue) => {
        return limitOptions.map(optionValue => {
            const selectedAttr = optionValue === selectedValue ? 'selected' : '';
            return `<option value="${optionValue}" ${selectedAttr}>${optionValue} files</option>`;
        }).join('');
    };

    /**
     * Render the pagination footer containing limit selectors and actions.
     *
     * @returns {string} HTML footer markup.
     */
    const renderPaginationFooter = () => {
        const controls = `
            <div class="pagination-settings">
                <div class="form-group">
                    <label for="backup-files-initial-limit">Initial Load</label>
                    <select id="backup-files-initial-limit">
                        ${renderLimitOptions(initialLimit)}
                    </select>
                </div>
                <div class="form-group">
                    <label for="backup-files-step-limit">Load More Step</label>
                    <select id="backup-files-step-limit">
                        ${renderLimitOptions(stepLimit)}
                    </select>
                </div>
            </div>
        `;

        if (!hasMore) {
            return controls;
        }

        const loadAllActive = Boolean(backupFilesPagingState && backupFilesPagingState.loadAllActive);
        const cancelRequested = Boolean(backupFilesPagingState && backupFilesPagingState.cancelLoadAllRequested);
        const remainingLabel = (totals.remaining !== null) ? `${totals.remaining} remaining` : 'more available';

        return `
            ${controls}
            <div class="load-more-row">
                <button type="button" class="btn btn-secondary" id="backup-files-load-more" ${loadAllActive ? 'disabled' : ''}>Load More (${remainingLabel})</button>
                <button type="button" class="btn btn-secondary" id="backup-files-load-all" ${loadAllActive ? 'disabled' : ''}>Load All</button>
                ${loadAllActive ? `<button type="button" class="btn btn-secondary" id="backup-files-cancel-load-all">${cancelRequested ? 'Cancelling...' : 'Cancel'}</button>` : ''}
            </div>
        `;
    };

    if (sortValue !== 'db_name' && sortValue !== 'destination') {
        container.innerHTML = visibleBackups.map(backup => {
            const typeLabel = backup.type === 'local' ? 'Local File' : 'Remote Storage';
            const downloadFilename = backup.filename;
        const canDownload = true;
        const canRestore = true;

            const encodedId = encodeURIComponent(backup.id || '');
            const encodedType = encodeURIComponent(backup.type || '');
            const encodedDestId = encodeURIComponent(backup.destination_id || '');
            const encodedBackupId = encodeURIComponent(backup.backup_id || '');
            const encodedFilename = encodeURIComponent(backup.filename || '');
            const encodedDownloadFilename = encodeURIComponent(downloadFilename || '');
        
            return `
            <div class="item">
                <div class="item-header">
                    <h3>${backup.display_filename || backup.filename}</h3>
                    <div class="item-actions">
                        <button class="btn btn-sm btn-secondary" data-action="backup-details" data-id="${encodedId}" data-type="${encodedType}" data-destination-id="${encodedDestId}">Details</button>
                        ${canDownload ? `
                            <button class="btn btn-sm btn-primary" data-action="backup-download" data-type="${encodedType}" data-destination-id="${encodedDestId}" data-backup-id="${encodedBackupId}" data-filename="${encodedDownloadFilename}">Download</button>
                        ` : ''}
                        ${canRestore ? `
                            <button class="btn btn-sm btn-warning" data-action="backup-restore" data-id="${encodedId}" data-type="${encodedType}" data-destination-id="${encodedDestId}" data-backup-id="${encodedBackupId}" data-filename="${encodedFilename}">Restore</button>
                        ` : ''}
                        <button class="btn btn-sm btn-danger" data-action="backup-delete" data-id="${encodedId}" data-type="${encodedType}" data-destination-id="${encodedDestId}" data-backup-id="${encodedBackupId}" data-filename="${encodedFilename}">Delete</button>
                    </div>
                </div>
                <div class="item-details">
                    <p><strong>Database:</strong> ${backup.db_name || 'Unknown'}</p>
                    <p><strong>Type:</strong> ${typeLabel}</p>
                    <p><strong>Source:</strong> ${backup.source}</p>
                    <p><strong>Size:</strong> ${(backup.size_mb === 0 || backup.size_mb) ? `${backup.size_mb} MB` : 'Unknown'}</p>
                    <p><strong>Created:</strong> ${backup.created_at ? new Date(backup.created_at).toLocaleString() : 'Unknown'}</p>
                </div>
            </div>
            `;
        }).join('') + renderPaginationFooter();
        return;
    }

    const groupLabel = sortValue === 'destination' ? 'Destination' : 'Database';
    const groupKeyForBackup = (backup) => {
        if (sortValue === 'destination') {
            return backup.source || 'Unknown';
        }
        return backup.db_name || 'Unknown';
    };

    const groups = new Map();
    visibleBackups.forEach(b => {
        const key = groupKeyForBackup(b);
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(b);
    });

    const totalGroups = new Map();
    sortedBackups.forEach(b => {
        const key = groupKeyForBackup(b);
        totalGroups.set(key, (totalGroups.get(key) || 0) + 1);
    });

    const groupNames = [...groups.keys()].sort((a, b) => compareByString(a, b));

    container.innerHTML = groupNames.map(groupName => {
        const items = groups.get(groupName) || [];
        items.sort((a, b) => getBackupCreatedAtMs(b) - getBackupCreatedAtMs(a));

        const rendered = items.map(backup => {
            const typeLabel = backup.type === 'local' ? 'Local File' : 'Remote Storage';
            const downloadFilename = backup.filename;
        const canDownload = true;
        const canRestore = true;

            const encodedId = encodeURIComponent(backup.id || '');
            const encodedType = encodeURIComponent(backup.type || '');
            const encodedDestId = encodeURIComponent(backup.destination_id || '');
            const encodedBackupId = encodeURIComponent(backup.backup_id || '');
            const encodedFilename = encodeURIComponent(backup.filename || '');
            const encodedDownloadFilename = encodeURIComponent(downloadFilename || '');
        
            return `
            <div class="item">
                <div class="item-header">
                    <h3>${backup.display_filename || backup.filename}</h3>
                    <div class="item-actions">
                        <button class="btn btn-sm btn-secondary" data-action="backup-details" data-id="${encodedId}" data-type="${encodedType}" data-destination-id="${encodedDestId}">Details</button>
                        ${canDownload ? `
                            <button class="btn btn-sm btn-primary" data-action="backup-download" data-type="${encodedType}" data-destination-id="${encodedDestId}" data-backup-id="${encodedBackupId}" data-filename="${encodedDownloadFilename}">Download</button>
                        ` : ''}
                        ${canRestore ? `
                            <button class="btn btn-sm btn-warning" data-action="backup-restore" data-id="${encodedId}" data-type="${encodedType}" data-destination-id="${encodedDestId}" data-backup-id="${encodedBackupId}" data-filename="${encodedFilename}">Restore</button>
                        ` : ''}
                        <button class="btn btn-sm btn-danger" data-action="backup-delete" data-id="${encodedId}" data-type="${encodedType}" data-destination-id="${encodedDestId}" data-backup-id="${encodedBackupId}" data-filename="${encodedFilename}">Delete</button>
                    </div>
                </div>
                <div class="item-details">
                    <p><strong>Database:</strong> ${backup.db_name || 'Unknown'}</p>
                    <p><strong>Type:</strong> ${typeLabel}</p>
                    <p><strong>Source:</strong> ${backup.source}</p>
                    <p><strong>Size:</strong> ${(backup.size_mb === 0 || backup.size_mb) ? `${backup.size_mb} MB` : 'Unknown'}</p>
                    <p><strong>Created:</strong> ${backup.created_at ? new Date(backup.created_at).toLocaleString() : 'Unknown'}</p>
                </div>
            </div>
            `;
        }).join('');

        const totalInGroup = totalGroups.get(groupName) || items.length;
        return `
            <div class="group-heading">${groupLabel}: ${groupName} (${items.length}/${totalInGroup})</div>
            ${rendered}
        `;
    }).join('') + renderPaginationFooter();
}

async function viewBackupDetails(backupId, type, destinationId) {
    try {
        let details;
        
        if (type === 'remote') {
            const file = backupFiles.find(f => (f.type === 'remote') && (f.backup_id || f.id) === backupId && (f.destination_id || '') === (destinationId || f.destination_id || ''));
            details = {
                ...(file || {}),
                id: backupId,
                type: 'remote',
                filename: (file && file.filename) ? file.filename : backupId,
                status: (file && file.status) ? file.status : 'unknown',
                destination_name: (file && file.source) ? file.source : undefined
            };
        } else {
            // For local files, get basic info
            const file = backupFiles.find(f => (f.filename || '') === backupId);
            details = {
                ...(file || {}),
                id: backupId,
                type: 'local'
            };
        }
        
        showBackupDetailsModal(details);
    } catch (error) {
        showStatus(`Failed to load backup details: ${error.message}`, 'error');
    }
}

function showBackupDetailsModal(details) {
    const modal = document.getElementById('backup-details-modal');
    const content = document.getElementById('backup-details-content');
    
    content.innerHTML = `
        <div class="backup-details">
            <h4>${details.filename || `Backup #${details.id}`}</h4>
            <div class="detail-grid">
                <div class="detail-item">
                    <label>Type:</label>
                    <span>${details.type === 'remote' ? 'Remote Storage' : 'Local File'}</span>
                </div>
                <div class="detail-item">
                    <label>Status:</label>
                    <span class="status ${details.status || 'unknown'}">${details.status || 'Unknown'}</span>
                </div>
                <div class="detail-item">
                    <label>Created:</label>
                    <span>${details.created_at ? new Date(details.created_at).toLocaleString() : 'Unknown'}</span>
                </div>
                <div class="detail-item">
                    <label>Size:</label>
                    <span>${details.size_mb ? `${details.size_mb} MB` : 'Unknown'}</span>
                </div>
                ${details.db_name ? `
                    <div class="detail-item">
                        <label>Database:</label>
                        <span>${details.db_name}</span>
                    </div>
                ` : ''}
                ${details.target_name ? `
                    <div class="detail-item">
                        <label>Database:</label>
                        <span>${details.target_name}</span>
                    </div>
                ` : ''}
                ${details.destination_name ? `
                    <div class="detail-item">
                        <label>Remote Storage Location:</label>
                        <span>${details.destination_name}</span>
                    </div>
                ` : ''}
                ${details.schedule_name ? `
                    <div class="detail-item">
                        <label>Schedule:</label>
                        <span>${details.schedule_name}</span>
                    </div>
                ` : ''}
                ${details.error_message ? `
                    <div class="detail-item">
                        <label>Error:</label>
                        <span class="error">${details.error_message}</span>
                    </div>
                ` : ''}
            </div>
        </div>
    `;

    currentModalBackup = details;
    clearBackupDetailsStatus(true);
    updateRestoreTargetSelector();
    updateRestoreEncryptionVisibility();
    wireBackupDetailsModalFooter();
    modal.classList.remove('hidden');
}

function updateRestoreTargetSelector() {
    const select = document.getElementById('backup-restore-target-id');
    if (!select) return;

    const allowedTypes = getCompatibleDbTypesForBackup(currentModalBackup);
    select.innerHTML = '<option value="">Select a database...</option>';
    if (Array.isArray(databases)) {
        databases
            .filter(d => {
                if (!d || !d.id) return false;
                if (!allowedTypes || allowedTypes.length === 0) return true;
                return allowedTypes.includes(String(d.db_type || '').toLowerCase());
            })
            .forEach(d => {
                select.innerHTML += `<option value="${d.id}">${d.name}</option>`;
            });
    }
}

function wireBackupDetailsModalFooter() {
    const restoreBtn = document.getElementById('restore-backup-btn');
    const downloadBtn = document.getElementById('download-backup-btn');
    const deleteBtn = document.getElementById('delete-backup-btn');

    if (restoreBtn) {
        restoreBtn.onclick = async () => {
            if (!currentModalBackup) return;
            await restoreBackupFromModal();
        };
    }

    if (downloadBtn) {
        downloadBtn.onclick = async () => {
            if (!currentModalBackup) return;
            const b = currentModalBackup;
            const destId = b.destination_id || '';
            const bid = b.backup_id || b.id || '';
            await downloadBackupDelegated(b.type, destId, bid, b.filename || 'backup');
        };
    }

    if (deleteBtn) {
        deleteBtn.onclick = async () => {
            if (!currentModalBackup) return;
            const b = currentModalBackup;
            await deleteBackup(b.id, b.type, b.destination_id || '', b.backup_id || '', b.filename || '');
        };
    }
}

async function openRestoreFromFile(id, type, destinationId, backupId, filename) {
    const details = {
        id,
        type,
        destination_id: destinationId,
        backup_id: backupId,
        filename
    };
    showBackupDetailsModal(details);
}

async function restoreBackupFromModal() {
    const targetId = document.getElementById('backup-restore-target-id')?.value || '';
    if (!targetId) {
        setBackupDetailsStatus('Please select a database to restore to', 'error');
        return;
    }

    if (!currentModalBackup) return;
    const b = currentModalBackup;
    const restoreName = b.filename || b.id;

    if (!confirm(`Are you sure you want to restore from backup "${restoreName}"? This will overwrite the selected database!`)) {
        return;
    }

    const typedConfirmation = (prompt('Type RESTORE to confirm this restore operation:') || '').trim();
    if (typedConfirmation !== 'RESTORE') {
        setBackupDetailsStatus('Restore cancelled: confirmation text did not match RESTORE', 'error', true);
        return;
    }

    try {
        if (typeof keycloakApiRestoreCall !== 'function') {
            throw new Error('Restore helper not available');
        }

        setBackupDetailsStatus('Starting restore...', 'info', false);

        const encrypted = isBackupEncrypted(b);
        const encryptionPassword = trimValue(document.getElementById('backup-restore-encryption-password')?.value);
        if (encrypted && !encryptionPassword) {
            setBackupDetailsStatus('Selected backup is encrypted. Please provide the encryption password.', 'error', true);
            return;
        }

        const payload = {
            target_id: targetId,
            backup_id: b.type === 'remote' ? (b.backup_id || b.id) : (b.filename || b.id),
            confirmation: typedConfirmation,
            use_local_storage: b.type !== 'remote'
        };
        if (b.type === 'remote') {
            payload.destination_id = b.destination_id;
        }
        if (encrypted) {
            payload.encryption_password = encryptionPassword;
        }

        await keycloakApiRestoreCall('/automation/restore-now', payload);
        setBackupDetailsStatus('Restore completed successfully!', 'success', false);
        await loadBackupFiles();
        hideBackupDetailsModal();
    } catch (error) {
        setBackupDetailsStatus(`Failed to restore backup: ${error.message}`, 'error', true);
    }
}

/**
 * Toggle the encryption password input based on the currently selected backup.
 *
 * @returns {void}
 */
function updateRestoreEncryptionVisibility() {
    const group = document.getElementById('backup-restore-encryption-password-group');
    if (!group) return;

    const encrypted = isBackupEncrypted(currentModalBackup);
    group.classList.toggle('hidden', !encrypted);

    if (!encrypted) {
        const input = document.getElementById('backup-restore-encryption-password');
        if (input) input.value = '';
    }
}

function hideBackupDetailsModal() {
    clearBackupDetailsStatus(true);
    document.getElementById('backup-details-modal').classList.add('hidden');
}

async function downloadBackup(filename) {
    try {
        const response = await fetchWithKeycloakAuth(`/backup/download/${encodeURI(filename)}`);
        
        if (!response.ok) {
            throw new Error(`Download failed: ${response.statusText}`);
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        if (isBackupDetailsModalOpen()) {
            setBackupDetailsStatus('Backup downloaded successfully', 'success');
        } else {
            showStatus('Backup downloaded successfully', 'success');
        }
    } catch (error) {
        if (isBackupDetailsModalOpen()) {
            setBackupDetailsStatus(`Failed to download backup: ${error.message}`, 'error', true);
        } else {
            showStatus(`Failed to download backup: ${error.message}`, 'error');
        }
    }
}

async function deleteBackup(backupId, type, destinationId, remoteBackupId, remoteName) {
    if (!confirm('Are you sure you want to delete this backup?')) return;

    const preferModal = isBackupDetailsModalOpen() && currentModalBackup && String(currentModalBackup.id || '') === String(backupId || '');
    
    try {
        if (preferModal) {
            setBackupDetailsStatus('Deleting backup...', 'info', false);
        }
        if (type === 'remote') {
            if (typeof keycloakApiDeleteCall !== 'function') {
                throw new Error('Delete helper not available');
            }
            if (!destinationId || !remoteBackupId) {
                throw new Error('Missing destinationId or backupId');
            }

            const endpoint = `/automation/destinations/${destinationId}/backups/delete?backup_id=${encodeURIComponent(remoteBackupId)}&name=${encodeURIComponent(remoteName || '')}`;
            await keycloakApiDeleteCall(endpoint);
        } else {
            const file = backupFiles.find(f => (f.filename || '') === backupId);
            const filename = file ? file.filename : backupId;

            if (typeof keycloakApiDeleteCall !== 'function') {
                throw new Error('Delete helper not available');
            }
            await keycloakApiDeleteCall(`/backup/delete/${encodeURI(filename)}`);
        }
        
        if (preferModal) {
            setBackupDetailsStatus('Backup deleted successfully', 'success', false);
        } else {
            showStatus('Backup deleted successfully', 'success');
        }
        await loadBackupFiles();
        if (preferModal) {
            hideBackupDetailsModal();
        }
    } catch (error) {
        if (preferModal) {
            setBackupDetailsStatus(`Failed to delete backup: ${error.message}`, 'error', true);
        } else {
            showStatus(`Failed to delete backup: ${error.message}`, 'error');
        }
    }
}

// Initialize event listeners for backup files tab
function initBackupFilesTab() {
    // Backup actions
    document.getElementById('refresh-backup-files-btn').addEventListener('click', loadBackupFiles);
    
    // Storage location selector
    const storageSelect = document.getElementById('backup-files-storage-location');
    if (storageSelect) {
        storageSelect.addEventListener('change', loadBackupFiles);
    }

    const databaseSelect = document.getElementById('backup-files-database-filter');
    if (databaseSelect) {
        databaseSelect.addEventListener('change', loadBackupFiles);
    }

    const sortSelect = document.getElementById('backup-files-sort');
    if (sortSelect) {
        sortSelect.addEventListener('change', loadBackupFiles);
    }

    
    // Modal close buttons
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', hideBackupDetailsModal);
    });
    
    // Close modal when clicking outside
    document.getElementById('backup-details-modal').addEventListener('click', (e) => {
        if (e.target.id === 'backup-details-modal') {
            hideBackupDetailsModal();
        }
    });

    const list = document.getElementById('backup-files-list');
    if (list) {
        list.addEventListener('change', (e) => {
            const target = e.target;
            if (!(target instanceof HTMLSelectElement)) return;

            if (target.id === 'backup-files-initial-limit') {
                saveBackupFilesLimitSelection(
                    'backup-files-initial-limit',
                    BACKUP_FILES_INITIAL_LIMIT_STORAGE_KEY,
                    BACKUP_FILES_DEFAULT_INITIAL_LIMIT
                );
                loadBackupFiles();
                return;
            }

            if (target.id === 'backup-files-step-limit') {
                saveBackupFilesLimitSelection(
                    'backup-files-step-limit',
                    BACKUP_FILES_STEP_LIMIT_STORAGE_KEY,
                    BACKUP_FILES_DEFAULT_STEP_LIMIT
                );
                loadBackupFiles();
            }
        });

        list.addEventListener('click', async (e) => {
            const loadMoreBtn = e.target.closest('#backup-files-load-more');
            if (loadMoreBtn) {
                await showMoreBackupFiles();
                return;
            }

            const loadAllBtn = e.target.closest('#backup-files-load-all');
            if (loadAllBtn) {
                await loadAllBackupFiles();
                return;
            }

            const cancelBtn = e.target.closest('#backup-files-cancel-load-all');
            if (cancelBtn) {
                cancelLoadAllBackupFiles();
                renderBackupFiles();
                return;
            }

            const btn = e.target.closest('button[data-action]');
            if (!btn) return;

            const action = btn.getAttribute('data-action');
            const id = decodeURIComponent(btn.getAttribute('data-id') || '');
            const type = decodeURIComponent(btn.getAttribute('data-type') || '');
            const destinationId = decodeURIComponent(btn.getAttribute('data-destination-id') || '');
            const backupId = decodeURIComponent(btn.getAttribute('data-backup-id') || '');
            const filename = decodeURIComponent(btn.getAttribute('data-filename') || '');

            if (action === 'backup-details') {
                await viewBackupDetails(id, type, destinationId);
            } else if (action === 'backup-download') {
                await downloadBackupDelegated(type, destinationId, backupId, filename);
            } else if (action === 'backup-restore') {
                await openRestoreFromFile(id, type, destinationId, backupId, filename);
            } else if (action === 'backup-delete') {
                await deleteBackup(id, type, destinationId, backupId, filename);
            }
        });
    }
    
    // Update storage selector when destinations are loaded
    updateBackupFilesStorageSelector();
    updateBackupFilesDatabaseFilter();
}

window.updateRestoreEncryptionVisibility = updateRestoreEncryptionVisibility;
