/**
 * History Tab JavaScript
 *
 * Shows backup execution history (scheduled + manual runs).
 */

let historyRuns = [];

const HISTORY_DEFAULT_INITIAL_LIMIT = 20;
const HISTORY_DEFAULT_STEP_LIMIT = 50;
const HISTORY_INITIAL_LIMIT_STORAGE_KEY = 'history_initial_limit';
const HISTORY_STEP_LIMIT_STORAGE_KEY = 'history_step_limit';

let historyVisibleLimit = HISTORY_DEFAULT_INITIAL_LIMIT;
let historyPagingState = null;

/**
 * Normalize a history limit value to a positive integer.
 *
 * @param {string|number|null|undefined} value Raw limit value.
 * @param {number} fallback Fallback value when invalid.
 * @returns {number} Normalized limit value.
 */
function parseHistoryLimit(value, fallback) {
    const parsed = parseInt(String(value ?? '').trim(), 10);
    if (!Number.isFinite(parsed) || parsed <= 0) {
        return fallback;
    }
    return parsed;
}

/**
 * Get a history limit value from storage or the UI.
 *
 * @param {string} selectId Select element id.
 * @param {string} storageKey Storage key to check.
 * @param {number} fallback Fallback value.
 * @returns {number} Limit value.
 */
function getHistoryLimitValue(selectId, storageKey, fallback) {
    const storedRaw = storageKey ? localStorage.getItem(storageKey) : null;
    if (storedRaw !== null && storedRaw !== undefined && String(storedRaw).trim() !== '') {
        const storedValue = parseHistoryLimit(storedRaw, fallback);
        const select = document.getElementById(selectId);
        if (select) {
            const match = [...select.options].find(option => {
                return parseHistoryLimit(option.value, fallback) === storedValue;
            });
            if (match) {
                select.value = match.value;
            }
        }
        return storedValue;
    }

    const selectValue = document.getElementById(selectId)?.value;
    return parseHistoryLimit(selectValue, fallback);
}

/**
 * Persist the currently selected history limit selection.
 *
 * @param {string} selectId Select element id.
 * @param {string} storageKey Storage key to update.
 * @param {number} fallback Fallback value.
 * @returns {void}
 */
function saveHistoryLimitSelection(selectId, storageKey, fallback) {
    if (!storageKey) return;
    const value = parseHistoryLimit(document.getElementById(selectId)?.value, fallback);
    localStorage.setItem(storageKey, String(value));
}

/**
 * Return the selected initial load limit.
 *
 * @returns {number} Initial load limit.
 */
function getHistoryInitialLimit() {
    return getHistoryLimitValue(
        'history-initial-limit',
        HISTORY_INITIAL_LIMIT_STORAGE_KEY,
        HISTORY_DEFAULT_INITIAL_LIMIT
    );
}

/**
 * Return the selected step load limit.
 *
 * @returns {number} Step load limit.
 */
function getHistoryStepLimit() {
    return getHistoryLimitValue(
        'history-step-limit',
        HISTORY_STEP_LIMIT_STORAGE_KEY,
        HISTORY_DEFAULT_STEP_LIMIT
    );
}

/**
 * Get the currently selected history sort mode.
 *
 * @returns {string} Sort mode key.
 */
function getHistorySortValue() {
    return document.getElementById('history-sort')?.value || 'newest';
}

/**
 * Get the current history query filter values.
 *
 * @returns {{targetId: string, operation: string, trigger: string}} Current filter values.
 */
function getHistoryQueryParams() {
    return {
        targetId: document.getElementById('history-database-filter')?.value || '',
        operation: document.getElementById('history-operation-filter')?.value || '',
        trigger: document.getElementById('history-trigger-filter')?.value || ''
    };
}

/**
 * Parse a history run started_at into a timestamp.
 *
 * @param {Object} run History run.
 * @returns {number} Timestamp in ms since epoch.
 */
function getHistoryStartedAtMs(run) {
    const t = new Date(run?.started_at || 0).getTime();
    return Number.isFinite(t) ? t : 0;
}

/**
 * Parse a datetime-local input value into a timestamp.
 *
 * @param {string} value Input value.
 * @returns {number|null} Timestamp in ms (local time) or null.
 */
function parseDatetimeLocal(value) {
    const raw = String(value || '').trim();
    if (!raw) return null;
    const parts = raw.split('T');
    if (parts.length !== 2) return null;

    const datePart = parts[0];
    const timePart = parts[1];

    const dateBits = datePart.split('-').map(n => parseInt(n, 10));
    const timeBits = timePart.split(':').map(n => parseInt(n, 10));
    if (dateBits.length < 3) return null;
    if (timeBits.length < 2) return null;

    const [year, month, day] = dateBits;
    const [hour, minute] = timeBits;
    if (!year || !month || !day) return null;
    if (!Number.isFinite(hour) || !Number.isFinite(minute)) return null;

    const d = new Date(year, month - 1, day, hour, minute, 0, 0);
    const ms = d.getTime();
    return Number.isFinite(ms) ? ms : null;
}

/**
 * Get the configured date range filter for History.
 *
 * @returns {{startMs: number|null, endMs: number|null}} Range in ms.
 */
function getHistoryDateRangeFilter() {
    const startValue = document.getElementById('history-start-date')?.value || '';
    const endValue = document.getElementById('history-end-date')?.value || '';
    return {
        startMs: parseDatetimeLocal(startValue),
        endMs: parseDatetimeLocal(endValue)
    };
}

/**
 * Create a new paging state for the history list.
 *
 * @returns {{offset: number, total: number|null, loadAllActive: boolean, cancelLoadAllRequested: boolean, lastFetchCount: number, lastFetchLimit: number}} Paging state.
 */
function createHistoryPagingState() {
    return {
        offset: 0,
        total: null,
        loadAllActive: false,
        cancelLoadAllRequested: false,
        lastFetchCount: 0,
        lastFetchLimit: 0
    };
}

/**
 * Reset pagination to the first page.
 *
 * @returns {void}
 */
function resetHistoryPagination() {
    historyVisibleLimit = getHistoryInitialLimit();
    historyPagingState = null;
}

/**
 * Get the paging totals for the history list.
 *
 * @returns {{total: number|null, loaded: number, remaining: number|null}} Totals for paging.
 */
function getHistoryPagingTotals() {
    const loaded = historyRuns.length;
    if (!historyPagingState) {
        return { total: null, loaded, remaining: null };
    }

    const total = Number.isFinite(historyPagingState.total)
        ? Number(historyPagingState.total)
        : null;
    const remaining = total !== null ? Math.max(total - loaded, 0) : null;
    return { total, loaded, remaining };
}

/**
 * Return true when more history may be available without a known total.
 *
 * @returns {boolean} True when more items could be fetched.
 */
function hasMoreHistoryAvailable() {
    if (!historyPagingState) return false;
    if (historyPagingState.total !== null && historyPagingState.total !== undefined) {
        return historyRuns.length < historyPagingState.total;
    }
    if (!historyPagingState.lastFetchLimit) return true;
    return historyPagingState.lastFetchCount >= historyPagingState.lastFetchLimit;
}

/**
 * Fetch the next page of history runs.
 *
 * @param {number} limit Max items to request.
 * @returns {Promise<void>} Resolves when the page is loaded.
 */
async function fetchMoreHistory(limit) {
    if (!historyPagingState) return;

    const { targetId, operation, trigger } = getHistoryQueryParams();
    let url = `/automation/audit?limit=${limit}&offset=${historyPagingState.offset}&include_total=true`;
    if (targetId) url += `&target_id=${encodeURIComponent(targetId)}`;
    if (operation) url += `&operation=${encodeURIComponent(operation)}`;
    if (trigger) url += `&trigger=${encodeURIComponent(trigger)}`;

    const response = await apiCall(url);
    let items = [];
    if (response && Array.isArray(response.items)) {
        items = response.items;
        if (Number.isFinite(response.total)) {
            historyPagingState.total = Number(response.total);
        }
    } else if (Array.isArray(response)) {
        items = response;
    }

    historyPagingState.offset += items.length;
    historyPagingState.lastFetchCount = items.length;
    historyPagingState.lastFetchLimit = limit;
    historyRuns = historyRuns.concat(items);
}

/**
 * Show more items in the history list.
 *
 * @returns {Promise<void>} Resolves when finished.
 */
async function showMoreHistory() {
    const stepLimit = getHistoryStepLimit();
    if (!historyPagingState) {
        historyVisibleLimit += stepLimit;
        renderHistory();
        return;
    }

    const totals = getHistoryPagingTotals();
    if (totals.loaded > historyVisibleLimit) {
        historyVisibleLimit += stepLimit;
        renderHistory();
        return;
    }

    await fetchMoreHistory(stepLimit);
    historyVisibleLimit += stepLimit;
    renderHistory();
}

/**
 * Load all history entries until exhausted or cancelled.
 *
 * @returns {Promise<void>} Resolves when the load finishes.
 */
async function loadAllHistory() {
    if (!historyPagingState || historyPagingState.loadAllActive) return;

    historyPagingState.loadAllActive = true;
    historyPagingState.cancelLoadAllRequested = false;
    historyVisibleLimit = Number.MAX_SAFE_INTEGER;
    renderHistory();

    const stepLimit = getHistoryStepLimit();

    try {
        let guard = 0;
        while (!historyPagingState.cancelLoadAllRequested) {
            guard += 1;
            if (guard > 10000) break;

            const totals = getHistoryPagingTotals();
            if (totals.total !== null && totals.remaining === 0) {
                break;
            }
            if (totals.total === null && !hasMoreHistoryAvailable()) {
                break;
            }

            await fetchMoreHistory(stepLimit);
            renderHistory();
            await new Promise(resolve => setTimeout(resolve, 0));
        }
    } finally {
        if (historyPagingState) {
            historyPagingState.loadAllActive = false;
        }
        renderHistory();
    }
}

/**
 * Cancel a load-all operation for history.
 *
 * @returns {void}
 */
function cancelLoadAllHistory() {
    if (historyPagingState) {
        historyPagingState.cancelLoadAllRequested = true;
    }
}

/**
 * Render a single history run entry.
 *
 * @param {Object} run History run.
 * @returns {string} HTML.
 */
function renderHistoryRunItem(run) {
    const status = run.status || 'unknown';
    const title = run.backup_name || run.backup_id || `Event ${run.id}`;
    const created = run.started_at ? new Date(run.started_at).toLocaleString() : 'Unknown';
    const finished = run.finished_at ? new Date(run.finished_at).toLocaleString() : null;

    return `
        <div class="item">
            <div class="item-header">
                <h3>${title}</h3>
                <div class="item-actions">
                    <button class="btn btn-sm btn-secondary" data-action="history-details" data-id="${run.id}">Details</button>
                </div>
            </div>
            <div class="item-details">
                <p><strong>Database:</strong> ${run.target_name || 'Unknown'}</p>
                <p><strong>Destination:</strong> ${run.destination_name || 'Unknown'}</p>
                <p><strong>Operation:</strong> ${run.operation || 'unknown'}</p>
                <p><strong>Trigger:</strong> ${run.trigger || 'unknown'}</p>
                ${run.schedule_name ? `<p><strong>Schedule:</strong> ${run.schedule_name}</p>` : ''}
                <p><strong>Status:</strong> <span class="status ${status}">${status}</span></p>
                <p><strong>Started:</strong> ${created}</p>
                ${finished ? `<p><strong>Finished:</strong> ${finished}</p>` : ''}
                ${run.error_message ? `<p><strong>Error:</strong> <span class="error">${run.error_message}</span></p>` : ''}
            </div>
        </div>
    `;
}

/**
 * Load history data with paging.
 *
 * @returns {Promise<void>} Resolves when history is loaded.
 */
async function loadHistory() {
    try {
        resetHistoryPagination();
        historyRuns = [];
        historyPagingState = createHistoryPagingState();

        const initialLimit = getHistoryInitialLimit();
        historyVisibleLimit = initialLimit;
        await fetchMoreHistory(initialLimit);
        renderHistory();
    } catch (error) {
        showStatus(`Failed to load history: ${error.message}`, 'error', true);
    }
}

window.loadHistory = loadHistory;

function updateHistoryDatabaseFilter() {
    const select = document.getElementById('history-database-filter');
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

window.updateHistoryDatabaseFilter = updateHistoryDatabaseFilter;

/**
 * Render the history list and pagination controls.
 *
 * @returns {void}
 */
function renderHistory() {
    const container = document.getElementById('history-list');
    if (!container) return;

    const items = Array.isArray(historyRuns) ? historyRuns : [];
    const range = getHistoryDateRangeFilter();
    const filtered = items.filter(r => {
        const ts = getHistoryStartedAtMs(r);
        if (range.startMs !== null && ts < range.startMs) return false;
        if (range.endMs !== null && ts > range.endMs) return false;
        return true;
    });

    const sortValue = getHistorySortValue();
    const compareByString = (a, b) => String(a || '').localeCompare(String(b || ''), undefined, { sensitivity: 'base' });

    const sortedRuns = [...filtered];
    if (sortValue === 'oldest') {
        sortedRuns.sort((a, b) => getHistoryStartedAtMs(a) - getHistoryStartedAtMs(b));
    } else if (sortValue === 'operation') {
        sortedRuns.sort((a, b) => {
            const diff = compareByString(a.operation, b.operation);
            if (diff !== 0) return diff;
            return getHistoryStartedAtMs(b) - getHistoryStartedAtMs(a);
        });
    } else if (sortValue === 'status') {
        sortedRuns.sort((a, b) => {
            const diff = compareByString(a.status, b.status);
            if (diff !== 0) return diff;
            return getHistoryStartedAtMs(b) - getHistoryStartedAtMs(a);
        });
    } else if (sortValue === 'trigger') {
        sortedRuns.sort((a, b) => {
            const diff = compareByString(a.trigger, b.trigger);
            if (diff !== 0) return diff;
            return getHistoryStartedAtMs(b) - getHistoryStartedAtMs(a);
        });
    } else {
        // default newest
        sortedRuns.sort((a, b) => getHistoryStartedAtMs(b) - getHistoryStartedAtMs(a));
    }

    const totalCount = sortedRuns.length;
    const visibleRuns = sortedRuns.slice(0, Math.max(0, historyVisibleLimit));

    const totals = getHistoryPagingTotals();
    const hasMore = historyPagingState
        ? (totals.remaining !== null ? totals.remaining > 0 : hasMoreHistoryAvailable())
        : (visibleRuns.length < totalCount);

    const initialLimit = getHistoryInitialLimit();
    const stepLimit = getHistoryStepLimit();
    const limitOptions = [10, 25, 50, 100, 250, 500];

    /**
     * Render pagination option entries for the limit selectors.
     *
     * @param {number} selectedValue Currently selected limit value.
     * @returns {string} HTML options markup.
     */
    const renderLimitOptions = (selectedValue) => {
        return limitOptions.map(optionValue => {
            const selectedAttr = optionValue === selectedValue ? 'selected' : '';
            return `<option value="${optionValue}" ${selectedAttr}>${optionValue} items</option>`;
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
                    <label for="history-initial-limit">Initial Load</label>
                    <select id="history-initial-limit">
                        ${renderLimitOptions(initialLimit)}
                    </select>
                </div>
                <div class="form-group">
                    <label for="history-step-limit">Load More Step</label>
                    <select id="history-step-limit">
                        ${renderLimitOptions(stepLimit)}
                    </select>
                </div>
            </div>
        `;

        if (!hasMore) {
            return controls;
        }

        const loadAllActive = Boolean(historyPagingState && historyPagingState.loadAllActive);
        const cancelRequested = Boolean(historyPagingState && historyPagingState.cancelLoadAllRequested);
        const remainingLabel = (totals.remaining !== null) ? `${totals.remaining} remaining` : 'more available';

        return `
            ${controls}
            <div class="load-more-row">
                <button type="button" class="btn btn-secondary" id="history-load-more" ${loadAllActive ? 'disabled' : ''}>Load More (${remainingLabel})</button>
                <button type="button" class="btn btn-secondary" id="history-load-all" ${loadAllActive ? 'disabled' : ''}>Load All</button>
                ${loadAllActive ? `<button type="button" class="btn btn-secondary" id="history-cancel-load-all">${cancelRequested ? 'Cancelling...' : 'Cancel'}</button>` : ''}
            </div>
        `;
    };

    if (filtered.length === 0) {
        container.innerHTML = '<p class="no-items">No history entries found.</p>' + renderPaginationFooter();
        return;
    }

    if (sortValue !== 'db_name') {
        container.innerHTML = visibleRuns.map(r => renderHistoryRunItem(r)).join('') + renderPaginationFooter();
        return;
    }

    const groups = new Map();
    visibleRuns.forEach(r => {
        const key = r.target_name || 'Unknown';
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(r);
    });

    const totalGroups = new Map();
    sortedRuns.forEach(r => {
        const key = r.target_name || 'Unknown';
        totalGroups.set(key, (totalGroups.get(key) || 0) + 1);
    });

    const groupNames = [...groups.keys()].sort((a, b) => compareByString(a, b));

    container.innerHTML = groupNames.map(groupName => {
        const runs = groups.get(groupName) || [];
        runs.sort((a, b) => getHistoryStartedAtMs(b) - getHistoryStartedAtMs(a));

        const rendered = runs.map(run => renderHistoryRunItem(run)).join('');

        const totalInGroup = totalGroups.get(groupName) || runs.length;
        return `
            <div class="group-heading">Database: ${groupName} (${runs.length}/${totalInGroup})</div>
            ${rendered}
        `;
    }).join('') + renderPaginationFooter();
}

async function viewHistoryDetails(runId) {
    try {
        const details = await apiCall(`/automation/audit/${runId}`);
        showHistoryDetailsModal(details);
    } catch (error) {
        showStatus(`Failed to load history details: ${error.message}`, 'error');
    }
}

function showHistoryDetailsModal(details) {
    const modal = document.getElementById('history-details-modal');
    const content = document.getElementById('history-details-content');
    if (!modal || !content) return;

    content.innerHTML = `
        <div class="backup-details">
            <h4>${details.backup_filename || `Run ${details.id}`}</h4>
            <pre class="pre-wrap">${JSON.stringify(details, null, 2)}</pre>
        </div>
    `;

    modal.classList.remove('hidden');
}

function hideHistoryDetailsModal() {
    document.getElementById('history-details-modal')?.classList.add('hidden');
}

function initHistoryTab() {
    document.getElementById('refresh-history-btn')?.addEventListener('click', loadHistory);
    document.getElementById('history-database-filter')?.addEventListener('change', loadHistory);
    document.getElementById('history-operation-filter')?.addEventListener('change', loadHistory);
    document.getElementById('history-trigger-filter')?.addEventListener('change', loadHistory);
    document.getElementById('history-sort')?.addEventListener('change', loadHistory);

    document.getElementById('history-start-date')?.addEventListener('change', loadHistory);
    document.getElementById('history-end-date')?.addEventListener('change', loadHistory);

    document.querySelectorAll('#history-details-modal .modal-close').forEach(btn => {
        btn.addEventListener('click', hideHistoryDetailsModal);
    });

    document.getElementById('history-details-modal')?.addEventListener('click', (e) => {
        if (e.target.id === 'history-details-modal') {
            hideHistoryDetailsModal();
        }
    });

    const list = document.getElementById('history-list');
    if (list) {
        list.addEventListener('change', (e) => {
            const target = e.target;
            if (!(target instanceof HTMLSelectElement)) return;

            if (target.id === 'history-initial-limit') {
                saveHistoryLimitSelection(
                    'history-initial-limit',
                    HISTORY_INITIAL_LIMIT_STORAGE_KEY,
                    HISTORY_DEFAULT_INITIAL_LIMIT
                );
                loadHistory();
                return;
            }

            if (target.id === 'history-step-limit') {
                saveHistoryLimitSelection(
                    'history-step-limit',
                    HISTORY_STEP_LIMIT_STORAGE_KEY,
                    HISTORY_DEFAULT_STEP_LIMIT
                );
                loadHistory();
            }
        });

        list.addEventListener('click', async (e) => {
            const loadMoreBtn = e.target.closest('#history-load-more');
            if (loadMoreBtn) {
                await showMoreHistory();
                return;
            }

            const loadAllBtn = e.target.closest('#history-load-all');
            if (loadAllBtn) {
                await loadAllHistory();
                return;
            }

            const cancelBtn = e.target.closest('#history-cancel-load-all');
            if (cancelBtn) {
                cancelLoadAllHistory();
                renderHistory();
                return;
            }

            const btn = e.target.closest('button[data-action]');
            if (!btn) return;
            const action = btn.getAttribute('data-action');
            const id = btn.getAttribute('data-id');
            if (action === 'history-details' && id) {
                viewHistoryDetails(id);
            }
        });
    }

    updateHistoryDatabaseFilter();
}

window.initHistoryTab = initHistoryTab;
