/**
 * Backup Schedules Tab JavaScript
 * 
 * Handles backup schedule management for the Backup Manager.
 * Supports encryption, multiple destinations, retention policies, and notifications.
 */

// Backup Schedules Management Functions
async function loadBackupSchedules() {
    try {
        backupSchedules = await apiCall('/automation/schedules');
        renderBackupSchedules();
    } catch (error) {
        showStatus(`Failed to load backup schedules: ${error.message}`, 'error');
    }

}

/**
 * Update backup schedule UI controls based on permissions.
 * @returns {void}
 */
function updateBackupScheduleAccessUI() {
    // Always show all buttons - permission checks happen on click
    // This allows users to see the full UI capabilities even without permissions
}

/**
 * Map a legacy on_success/on_warning/on_failure config to a minimum severity.
 *
 * @param {Object} legacy Legacy channel config.
 * @returns {string} Minimum severity (info|warning|error).
 */
function legacyNotifyFlagsToMinSeverity(legacy) {
    if (!legacy || typeof legacy !== 'object') return 'error';
    if (legacy.on_success) return 'info';
    if (legacy.on_warning) return 'warning';
    if (legacy.on_failure) return 'error';
    return 'error';
}

/**
 * Normalize Telegram recipients from either the new recipients list or the legacy chat_id fields.
 *
 * @param {Object} telegramConfig Telegram notification config.
 * @returns {Array} Array of recipients in the form { chat_id, min_severity }.
 */
function normalizeTelegramRecipients(telegramConfig) {
    if (!telegramConfig || typeof telegramConfig !== 'object') return [];

    const recipients = Array.isArray(telegramConfig.recipients) ? telegramConfig.recipients : [];
    const normalized = recipients
        .map(r => ({
            chat_id: trimValue(r?.chat_id || ''),
            min_severity: trimValue(r?.min_severity || 'error')
        }))
        .filter(r => r.chat_id);

    if (normalized.length > 0) return normalized;

    const legacyChatId = trimValue(telegramConfig.chat_id || '');
    if (!legacyChatId) return [];

    return [{ chat_id: legacyChatId, min_severity: legacyNotifyFlagsToMinSeverity(telegramConfig) }];
}

/**
 * Normalize Email recipients from either the new recipients list or the legacy to fields.
 *
 * @param {Object} emailConfig Email notification config.
 * @returns {Array} Array of recipients in the form { to, min_severity }.
 */
function normalizeEmailRecipients(emailConfig) {
    if (!emailConfig || typeof emailConfig !== 'object') return [];

    const recipients = Array.isArray(emailConfig.recipients) ? emailConfig.recipients : [];
    const normalized = recipients
        .map(r => ({
            to: trimValue(r?.to || ''),
            min_severity: trimValue(r?.min_severity || 'error')
        }))
        .filter(r => r.to);

    if (normalized.length > 0) return normalized;

    const legacyTo = trimValue(emailConfig.to || '');
    if (!legacyTo) return [];

    return [{ to: legacyTo, min_severity: legacyNotifyFlagsToMinSeverity(emailConfig) }];
}

/**
 * Parse a notification attachment size limit in MB.
 *
 * @param {string|number|null|undefined} value Raw input value.
 * @param {number} fallback Default fallback value.
 * @returns {number} Parsed limit in MB.
 */
function parseNotificationAttachmentLimit(value, fallback) {
    const parsed = parseFloat(String(value ?? '').trim());
    if (!Number.isFinite(parsed) || parsed <= 0) {
        return fallback;
    }
    return parsed;
}

/**
 * Create a select element for minimum severity.
 *
 * @param {string} selected Selected severity.
 * @returns {HTMLSelectElement} Select element.
 */
function createMinSeveritySelect(selected) {
    const select = document.createElement('select');
    select.className = 'notification-min-severity';

    const options = [
        { value: 'info', label: 'Info' },
        { value: 'warning', label: 'Warning' },
        { value: 'error', label: 'Error' }
    ];

    options.forEach(opt => {
        const option = document.createElement('option');
        option.value = opt.value;
        option.textContent = opt.label;
        if (opt.value === selected) option.selected = true;
        select.appendChild(option);
    });

    return select;
}

/**
 * Create a recipient row with an input, severity selector, and remove button.
 *
 * @param {Object} params Row parameters.
 * @param {string} params.kind telegram|email.
 * @param {string} params.value Recipient value (chat_id or to).
 * @param {string} params.minSeverity Minimum severity.
 * @returns {HTMLDivElement} Row element.
 */
function createNotificationRecipientRow({ kind, value, minSeverity }) {
    const row = document.createElement('div');
    row.className = 'notification-recipient-row';
    row.dataset.recipientKind = kind;

    const input = document.createElement('input');
    input.type = kind === 'email' ? 'email' : 'text';
    input.placeholder = kind === 'email' ? 'admin@example.com' : 'e.g., -1001234567890';
    input.value = value || '';
    input.className = kind === 'email' ? 'notification-email-to' : 'notification-telegram-chat-id';

    const select = createMinSeveritySelect(minSeverity || 'error');

    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'btn btn-danger btn-sm';
    removeBtn.textContent = 'Remove';
    removeBtn.addEventListener('click', () => {
        row.remove();
    });

    row.appendChild(input);
    row.appendChild(select);
    row.appendChild(removeBtn);

    return row;
}

/**
 * Ensure at least one visible recipient row exists for a kind when notifications are enabled.
 *
 * @param {string} kind telegram|email.
 * @returns {void}
 */
function ensureAtLeastOneRecipientRow(kind) {
    const containerId = kind === 'email'
        ? 'backup-schedule-email-recipients'
        : 'backup-schedule-telegram-recipients';
    const container = document.getElementById(containerId);
    if (!container) return;

    const hasRow = container.querySelector('[data-recipient-kind]') !== null;
    if (hasRow) return;

    container.appendChild(createNotificationRecipientRow({ kind, value: '', minSeverity: 'error' }));
}

/**
 * Replace the current Telegram recipients UI with the given list.
 *
 * @param {Array} recipients Array of recipients.
 * @returns {void}
 */
function setTelegramRecipients(recipients) {
    const container = document.getElementById('backup-schedule-telegram-recipients');
    if (!container) return;
    container.innerHTML = '';
    (recipients || []).forEach(r => {
        container.appendChild(
            createNotificationRecipientRow({
                kind: 'telegram',
                value: r.chat_id,
                minSeverity: r.min_severity || 'error'
            })
        );
    });
}

/**
 * Replace the current Email recipients UI with the given list.
 *
 * @param {Array} recipients Array of recipients.
 * @returns {void}
 */
function setEmailRecipients(recipients) {
    const container = document.getElementById('backup-schedule-email-recipients');
    if (!container) return;
    container.innerHTML = '';
    (recipients || []).forEach(r => {
        container.appendChild(
            createNotificationRecipientRow({
                kind: 'email',
                value: r.to,
                minSeverity: r.min_severity || 'error'
            })
        );
    });
}

/**
 * Read Telegram recipients from the UI.
 *
 * @returns {Array} Array of recipients.
 */
function readTelegramRecipientsFromUI() {
    const container = document.getElementById('backup-schedule-telegram-recipients');
    if (!container) return [];

    return [...container.querySelectorAll('[data-recipient-kind="telegram"]')]
        .map(row => {
            const chatId = trimValue(row.querySelector('.notification-telegram-chat-id')?.value || '');
            const minSeverity = trimValue(row.querySelector('.notification-min-severity')?.value || 'error');
            return { chat_id: chatId, min_severity: minSeverity || 'error' };
        })
        .filter(r => r.chat_id);
}

/**
 * Read Email recipients from the UI.
 *
 * @returns {Array} Array of recipients.
 */
function readEmailRecipientsFromUI() {
    const container = document.getElementById('backup-schedule-email-recipients');
    if (!container) return [];

    return [...container.querySelectorAll('[data-recipient-kind="email"]')]
        .map(row => {
            const to = trimValue(row.querySelector('.notification-email-to')?.value || '');
            const minSeverity = trimValue(row.querySelector('.notification-min-severity')?.value || 'error');
            return { to, min_severity: minSeverity || 'error' };
        })
        .filter(r => r.to);
}

function updateScheduleTimeOfDayVisibility() {
    const intervalEl = document.getElementById('backup-schedule-interval');
    const groupEl = document.getElementById('backup-schedule-daily-time-group');
    const inputEl = document.getElementById('backup-schedule-daily-time');
    const hintEl = document.getElementById('backup-schedule-daily-time-hint');
    if (!intervalEl || !groupEl) return;

    const intervalSeconds = parseInt(intervalEl.value) || 86400;
    const shouldShow = intervalSeconds >= 3600;
    groupEl.classList.toggle('hidden', !shouldShow);

    if (!shouldShow) return;

    if (hintEl) {
        hintEl.textContent = intervalSeconds === 86400
            ? 'Anchor time for the schedule. For Daily, default: 03:30.'
            : 'Optional anchor time for Hourly/6h/12h/Weekly/Monthly schedules. Example: 12h + 03:30 -> 03:30 & 15:30.';
    }

    if (intervalSeconds === 86400 && inputEl && !trimValue(inputEl.value)) {
        inputEl.value = '03:30';
    }
}

/**
 * Trigger all enabled schedules to run immediately.
 * @returns {Promise<void>}
 */
async function runEnabledSchedulesNow() {
    if (typeof canRunBackups === 'function' && !canRunBackups()) {
        showStatus('You do not have permission to run schedules.', 'error', true);
        return;
    }

    if (!confirm('Run all enabled schedules now?')) return;

    try {
        const result = await apiCall('/automation/schedules/run-enabled-now', 'POST', { max_schedules: 1000 });
        const count = result && (result.count || result.executed) ? (result.count || result.executed) : 0;
        showStatus(`Triggered ${count} schedule(s)`, 'success');
        await loadBackupSchedules();
    } catch (error) {
        showStatus(`Failed to run schedules: ${error.message}`, 'error');
    }
}

function formatInterval(seconds) {
    if (seconds >= 2592000) return 'Monthly';
    if (seconds >= 604800) return 'Weekly';
    if (seconds >= 86400) return 'Daily';
    if (seconds >= 43200) return 'Every 12 Hours';
    if (seconds >= 21600) return 'Every 6 Hours';
    if (seconds >= 3600) return 'Hourly';
    return `Every ${seconds} seconds`;
}

function getDestinationNames(destinationIds) {
    if (!destinationIds || destinationIds.length === 0) return 'None';
    return destinationIds.map(id => {
        const dest = remoteStorageLocations.find(d => d.id === id);
        return dest ? dest.name : 'Unknown';
    }).join(', ');
}

/**
 * Format attachment settings summary for schedule notifications.
 *
 * @param {Object} notifications Notification configuration.
 * @returns {string} Summary string for attachments.
 */
function formatAttachmentSummary(notifications) {
    const telegram = notifications?.telegram || {};
    const email = notifications?.email || {};

    const telegramEnabled = Boolean(telegram.attach_backup);
    const telegramLimit = parseNotificationAttachmentLimit(telegram.attach_max_mb, 50);
    const emailEnabled = Boolean(email.attach_backup);
    const emailLimit = parseNotificationAttachmentLimit(email.attach_max_mb, 10);

    const telegramSummary = telegramEnabled ? `Yes (max ${telegramLimit} MB)` : 'No';
    const emailSummary = emailEnabled ? `Yes (max ${emailLimit} MB)` : 'No';

    return `Telegram: ${telegramSummary}, Email: ${emailSummary}`;
}

/**
 * Render the list of backup schedules.
 * @returns {void}
 */
function renderBackupSchedules() {
    const container = document.getElementById('backup-schedules-list');

    updateBackupScheduleAccessUI();
    
    if (backupSchedules.length === 0) {
        container.innerHTML = '<p class="no-items">No backup schedules configured. Add one to get started.</p>';
        return;
    }

    // Always show all buttons - permission checks happen on click
    container.innerHTML = backupSchedules.map(schedule => {
        const database = databases.find(d => d.id === schedule.target_id);
        const destinationNames = getDestinationNames(schedule.destination_ids);
        const retention = schedule.retention || {};
        const notifications = schedule.retention?.notifications || {};
        const retentionText = retention.smart ? `Smart (d/w/m/y=${retention.smart.daily || 0}/${retention.smart.weekly || 0}/${retention.smart.monthly || 0}/${retention.smart.yearly || 0})` :
                             retention.max_count ? `${retention.max_count} backups` :
                             retention.max_days ? `${retention.max_days} days` :
                             retention.max_size_mb ? `${retention.max_size_mb} MB` : 'Default';
        const hasNotifications = Boolean(
            schedule.retention?.notifications?.telegram?.enabled ||
            schedule.retention?.notifications?.email?.enabled ||
            schedule.retention?.notifications?.telegram?.chat_id ||
            schedule.retention?.notifications?.email?.to ||
            (Array.isArray(schedule.retention?.notifications?.telegram?.recipients)
                && schedule.retention.notifications.telegram.recipients.length > 0) ||
            (Array.isArray(schedule.retention?.notifications?.email?.recipients)
                && schedule.retention.notifications.email.recipients.length > 0)
        );
        const attachmentSummary = formatAttachmentSummary(notifications);
        
        return `
            <div class="item">
                <div class="item-header">
                    <h3>${schedule.name}</h3>
                    <div class="item-actions">
                        <button class="btn btn-sm btn-success" data-action="schedule-run-now" data-id="${schedule.id}">Run Now</button>
                        <button class="btn btn-sm btn-secondary" data-action="schedule-edit" data-id="${schedule.id}">Edit</button>
                        <button class="btn btn-sm btn-danger" data-action="schedule-delete" data-id="${schedule.id}">Delete</button>
                    </div>
                </div>
                <div class="item-details">
                    <p><strong>Database:</strong> ${database ? database.name : 'Unknown'}</p>
                    <p><strong>Storage:</strong> ${destinationNames}</p>
                    <p><strong>Interval:</strong> ${formatInterval(schedule.interval_seconds)}</p>
                    <p><strong>Retention:</strong> ${retentionText}</p>
                    <p><strong>Encryption:</strong> ${schedule.retention?.encrypt ? 'Yes' : 'No'}</p>
                    <p><strong>Notifications:</strong> ${hasNotifications ? 'Enabled' : 'Disabled'}</p>
                    <p><strong>Attachments:</strong> ${attachmentSummary}</p>
                    <p><strong>Status:</strong> <span class="status ${schedule.enabled ? 'active' : 'inactive'}">${schedule.enabled ? 'Active' : 'Inactive'}</span></p>
                    <p><strong>Next Run:</strong> ${schedule.next_run_at ? new Date(schedule.next_run_at).toLocaleString() : 'Not scheduled'}</p>
                    <p><strong>Last Run:</strong> ${schedule.last_run_at ? new Date(schedule.last_run_at).toLocaleString() : 'Never'}</p>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Show the schedule form for create/update.
 * @param {Object|null} schedule Existing schedule to edit.
 * @returns {void}
 */
function showBackupScheduleForm(schedule = null) {
    // Allow users to see the form UI - permission check happens on save

    const form = document.getElementById('backup-schedule-form');
    const title = document.getElementById('backup-schedule-form-title');
    const tabRoot = document.getElementById('backup-schedules-tab');
    
    // Update select options
    updateBackupScheduleSelects();

    if (tabRoot && tabRoot.firstElementChild !== form) {
        tabRoot.insertBefore(form, tabRoot.firstElementChild);
    }
    
    if (schedule) {
        title.textContent = 'Edit Backup Schedule';
        document.getElementById('backup-schedule-id').value = schedule.id;
        document.getElementById('backup-schedule-name').value = schedule.name;
        document.getElementById('backup-schedule-database').value = schedule.target_id || '';
        document.getElementById('backup-schedule-interval').value = schedule.interval_seconds || 86400;
        document.getElementById('backup-schedule-enabled').checked = schedule.enabled !== false;
        
        // Set destination checkboxes
        const destIds = schedule.destination_ids || [];
        document.querySelectorAll('#backup-schedule-destinations input[type="checkbox"]').forEach(cb => {
            cb.checked = destIds.includes(cb.value);
        });
        
        // Retention settings
        const retention = schedule.retention || {};

        const dailyTimeEl = document.getElementById('backup-schedule-daily-time');
        if (dailyTimeEl) {
            if (retention.run_at_time) {
                dailyTimeEl.value = retention.run_at_time;
            } else {
                dailyTimeEl.value = (schedule.interval_seconds === 86400) ? '03:30' : '';
            }
        }

        if (retention.smart) {
            document.getElementById('backup-schedule-retention-type').value = 'smart';
            const smartDailyEl = document.getElementById('backup-schedule-smart-daily');
            const smartWeeklyEl = document.getElementById('backup-schedule-smart-weekly');
            const smartMonthlyEl = document.getElementById('backup-schedule-smart-monthly');
            const smartYearlyEl = document.getElementById('backup-schedule-smart-yearly');
            if (smartDailyEl) smartDailyEl.value = retention.smart.daily || 7;
            if (smartWeeklyEl) smartWeeklyEl.value = retention.smart.weekly || 4;
            if (smartMonthlyEl) smartMonthlyEl.value = retention.smart.monthly || 6;
            if (smartYearlyEl) smartYearlyEl.value = retention.smart.yearly || 2;
        } else if (retention.max_count) {
            document.getElementById('backup-schedule-retention-type').value = 'count';
            document.getElementById('backup-schedule-retention-count').value = retention.max_count;
        } else if (retention.max_days) {
            document.getElementById('backup-schedule-retention-type').value = 'days';
            document.getElementById('backup-schedule-retention-days').value = retention.max_days;
        } else if (retention.max_size_mb) {
            document.getElementById('backup-schedule-retention-type').value = 'size';
            document.getElementById('backup-schedule-retention-size').value = retention.max_size_mb;
        }
        updateRetentionTypeVisibility();
        
        // Encryption settings
        document.getElementById('backup-schedule-encrypt').checked = retention.encrypt || false;
        document.getElementById('backup-schedule-encrypt-password').value = '';
        updateEncryptionVisibility();
        
        // Notification settings
        const notifications = retention.notifications || {};
        const telegram = notifications.telegram || {};
        const email = notifications.email || {};

        const telegramRecipients = normalizeTelegramRecipients(telegram);
        const emailRecipients = normalizeEmailRecipients(email);

        document.getElementById('backup-schedule-notify-telegram').checked = Boolean(
            telegram.enabled || telegramRecipients.length > 0
        );
        setTelegramRecipients(telegramRecipients);
        updateTelegramVisibility();
        const telegramAttachEl = document.getElementById('backup-schedule-telegram-attach');
        if (telegramAttachEl) {
            telegramAttachEl.checked = Boolean(telegram.attach_backup);
        }
        const telegramAttachMaxEl = document.getElementById('backup-schedule-telegram-attach-max');
        if (telegramAttachMaxEl) {
            telegramAttachMaxEl.value = parseNotificationAttachmentLimit(telegram.attach_max_mb, 50);
        }
        if (document.getElementById('backup-schedule-notify-telegram').checked) {
            ensureAtLeastOneRecipientRow('telegram');
        }

        document.getElementById('backup-schedule-notify-email').checked = Boolean(
            email.enabled || emailRecipients.length > 0
        );
        setEmailRecipients(emailRecipients);
        updateEmailVisibility();
        const emailAttachEl = document.getElementById('backup-schedule-email-attach');
        if (emailAttachEl) {
            emailAttachEl.checked = Boolean(email.attach_backup);
        }
        const emailAttachMaxEl = document.getElementById('backup-schedule-email-attach-max');
        if (emailAttachMaxEl) {
            emailAttachMaxEl.value = parseNotificationAttachmentLimit(email.attach_max_mb, 10);
        }
        if (document.getElementById('backup-schedule-notify-email').checked) {
            ensureAtLeastOneRecipientRow('email');
        }
    } else {
        title.textContent = 'Add Backup Schedule';
        document.getElementById('backup-schedule-id').value = '';
        document.getElementById('backup-schedule-name').value = '';
        document.getElementById('backup-schedule-database').value = '';
        document.getElementById('backup-schedule-interval').value = 86400;
        document.getElementById('backup-schedule-enabled').checked = true;
        
        // Reset destination checkboxes
        document.querySelectorAll('#backup-schedule-destinations input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
        
        // Reset retention
        document.getElementById('backup-schedule-retention-type').value = 'smart';
        document.getElementById('backup-schedule-retention-count').value = 7;
        document.getElementById('backup-schedule-retention-days').value = 30;
        document.getElementById('backup-schedule-retention-size').value = 1000;

        const dailyTimeEl = document.getElementById('backup-schedule-daily-time');
        if (dailyTimeEl) {
            dailyTimeEl.value = '';
        }
        const smartDailyEl = document.getElementById('backup-schedule-smart-daily');
        const smartWeeklyEl = document.getElementById('backup-schedule-smart-weekly');
        const smartMonthlyEl = document.getElementById('backup-schedule-smart-monthly');
        const smartYearlyEl = document.getElementById('backup-schedule-smart-yearly');
        if (smartDailyEl) smartDailyEl.value = 7;
        if (smartWeeklyEl) smartWeeklyEl.value = 4;
        if (smartMonthlyEl) smartMonthlyEl.value = 6;
        if (smartYearlyEl) smartYearlyEl.value = 2;
        updateRetentionTypeVisibility();
        
        // Reset encryption
        document.getElementById('backup-schedule-encrypt').checked = false;
        document.getElementById('backup-schedule-encrypt-password').value = '';
        updateEncryptionVisibility();
        
        // Reset notifications
        document.getElementById('backup-schedule-notify-telegram').checked = false;
        setTelegramRecipients([]);
        updateTelegramVisibility();
        const telegramAttachEl = document.getElementById('backup-schedule-telegram-attach');
        if (telegramAttachEl) {
            telegramAttachEl.checked = false;
        }
        const telegramAttachMaxEl = document.getElementById('backup-schedule-telegram-attach-max');
        if (telegramAttachMaxEl) {
            telegramAttachMaxEl.value = 50;
        }
        
        document.getElementById('backup-schedule-notify-email').checked = false;
        setEmailRecipients([]);
        updateEmailVisibility();
        const emailAttachEl = document.getElementById('backup-schedule-email-attach');
        if (emailAttachEl) {
            emailAttachEl.checked = false;
        }
        const emailAttachMaxEl = document.getElementById('backup-schedule-email-attach-max');
        if (emailAttachMaxEl) {
            emailAttachMaxEl.value = 10;
        }
    }

    updateScheduleTimeOfDayVisibility();
    
    form.classList.remove('hidden');
}

function hideBackupScheduleForm() {
    document.getElementById('backup-schedule-form').classList.add('hidden');
    if (typeof clearStatusMessages === 'function') {
        clearStatusMessages();
    }
}

function editBackupSchedule(id) {
    const schedule = backupSchedules.find(s => s.id === id);
    if (schedule) showBackupScheduleForm(schedule);
}

/**
 * Update select options for schedules based on current data.
 * @returns {void}
 */
function updateBackupScheduleSelects() {
    // Update database select
    const databaseSelect = document.getElementById('backup-schedule-database');
    databaseSelect.innerHTML = '<option value="">Select a database...</option>' +
        databases.map(database => `<option value="${database.id}">${database.name}</option>`).join('');
    
    // Update destinations checkbox group
    const destinationsContainer = document.getElementById('backup-schedule-destinations');
    const locations = Array.isArray(remoteStorageLocations) ? [...remoteStorageLocations] : [];
    if (!locations.find(l => l && (l.id === 'local' || l.destination_type === 'local'))) {
        locations.unshift({ id: 'local', name: 'Local Storage', destination_type: 'local', config: { path: '/app/backups' } });
    }

    const hasLocal = locations.some(l => l && (l.id === 'local' || l.destination_type === 'local'));
    const localWarning = hasLocal ? `
        <div class="warning-box">
            <strong>⚠️ Testing Only</strong>
            Local storage should only be used for testing and development.
            For production, use remote storage locations.
        </div>
    ` : '';

    destinationsContainer.innerHTML = locations.map(location => {
        const typeLabel = location.destination_type === 'local' ? '(Local)' : 
                         location.destination_type === 'sftp' ? '(SFTP)' : 
                         location.destination_type === 'google_drive' ? '(Google Drive)' : '';
        const optionHtml = `<label><input type="checkbox" value="${location.id}"> ${location.name} ${typeLabel}</label>`;
        if (location.destination_type === 'local' || location.id === 'local') {
            return `${localWarning}${optionHtml}`;
        }
        return optionHtml;
    }).join('');
}

function updateRetentionTypeVisibility() {
    const type = document.getElementById('backup-schedule-retention-type').value;
    document.getElementById('retention-count-options').classList.toggle('hidden', type !== 'count');
    document.getElementById('retention-days-options').classList.toggle('hidden', type !== 'days');
    document.getElementById('retention-size-options').classList.toggle('hidden', type !== 'size');
    const smartOptions = document.getElementById('retention-smart-options');
    if (smartOptions) {
        smartOptions.classList.toggle('hidden', type !== 'smart');
    }
}

function updateEncryptionVisibility() {
    const enabled = document.getElementById('backup-schedule-encrypt').checked;
    document.getElementById('backup-schedule-encrypt-options').classList.toggle('hidden', !enabled);
    if (!enabled) {
        const pwdEl = document.getElementById('backup-schedule-encrypt-password');
        if (pwdEl) {
            pwdEl.value = '';
        }
    }
}

function updateTelegramVisibility() {
    const enabled = document.getElementById('backup-schedule-notify-telegram').checked;
    document.getElementById('backup-schedule-telegram-options').classList.toggle('hidden', !enabled);
    if (enabled) {
        ensureAtLeastOneRecipientRow('telegram');
    }
}

function updateEmailVisibility() {
    const enabled = document.getElementById('backup-schedule-notify-email').checked;
    document.getElementById('backup-schedule-email-options').classList.toggle('hidden', !enabled);
    if (enabled) {
        ensureAtLeastOneRecipientRow('email');
    }
}

/**
 * Save a backup schedule (create or update).
 * @returns {Promise<void>}
 */
async function saveBackupSchedule() {
    if (typeof canConfigureBackups === 'function' && !canConfigureBackups()) {
        showStatus('You do not have permission to configure backup schedules. Required role: backup:admin or backup:configure', 'error', true);
        return;
    }

    const id = document.getElementById('backup-schedule-id').value;
    const name = trimValue(document.getElementById('backup-schedule-name').value);
    const databaseId = document.getElementById('backup-schedule-database').value;
    const intervalSeconds = parseInt(document.getElementById('backup-schedule-interval').value) || 86400;
    const enabled = document.getElementById('backup-schedule-enabled').checked;

    // Get selected destinations
    const destinationIds = [];
    document.querySelectorAll('#backup-schedule-destinations input[type="checkbox"]:checked').forEach(cb => {
        destinationIds.push(cb.value);
    });

    if (!name) {
        showStatus('Please enter a name', 'error');
        return;
    }
    
    if (!databaseId) {
        showStatus('Please select a database', 'error');
        return;
    }
    
    if (destinationIds.length === 0) {
        showStatus('Please select at least one storage location', 'error');
        return;
    }

    // Build retention object
    const retentionType = document.getElementById('backup-schedule-retention-type').value;
    const retention = {};

    const runAtTime = trimValue(document.getElementById('backup-schedule-daily-time')?.value);
    if (intervalSeconds === 86400) {
        retention.run_at_time = runAtTime || '03:30';
    } else if (runAtTime) {
        retention.run_at_time = runAtTime;
    }
    
    if (retentionType === 'count') {
        retention.max_count = parseInt(document.getElementById('backup-schedule-retention-count').value) || 7;
    } else if (retentionType === 'days') {
        retention.max_days = parseInt(document.getElementById('backup-schedule-retention-days').value) || 30;
    } else if (retentionType === 'size') {
        retention.max_size_mb = parseInt(document.getElementById('backup-schedule-retention-size').value) || 1000;
    } else if (retentionType === 'smart') {
        retention.smart = {
            daily: parseInt(document.getElementById('backup-schedule-smart-daily')?.value) || 7,
            weekly: parseInt(document.getElementById('backup-schedule-smart-weekly')?.value) || 4,
            monthly: parseInt(document.getElementById('backup-schedule-smart-monthly')?.value) || 6,
            yearly: parseInt(document.getElementById('backup-schedule-smart-yearly')?.value) || 2
        };
    }

    // Encryption
    if (document.getElementById('backup-schedule-encrypt').checked) {
        retention.encrypt = true;
        const password = trimValue(document.getElementById('backup-schedule-encrypt-password').value);
        if (password) {
            retention.encrypt_password = password;
        }
    }

    // Notifications
    retention.notifications = {};
    
    if (document.getElementById('backup-schedule-notify-telegram').checked) {
        const recipients = readTelegramRecipientsFromUI();
        if (recipients.length === 0) {
            showStatus('Please add at least one Telegram chat ID', 'error');
            return;
        }
        const attachBackup = document.getElementById('backup-schedule-telegram-attach')?.checked || false;
        const attachMax = parseNotificationAttachmentLimit(
            document.getElementById('backup-schedule-telegram-attach-max')?.value,
            50
        );
        retention.notifications.telegram = {
            enabled: true,
            recipients,
            attach_backup: attachBackup,
            attach_max_mb: attachMax,
        };
    }
    
    if (document.getElementById('backup-schedule-notify-email').checked) {
        const recipients = readEmailRecipientsFromUI();
        if (recipients.length === 0) {
            showStatus('Please add at least one email recipient', 'error');
            return;
        }
        const attachBackup = document.getElementById('backup-schedule-email-attach')?.checked || false;
        const attachMax = parseNotificationAttachmentLimit(
            document.getElementById('backup-schedule-email-attach-max')?.value,
            10
        );
        retention.notifications.email = {
            enabled: true,
            recipients,
            attach_backup: attachBackup,
            attach_max_mb: attachMax,
        };
    }

    const payload = {
        name,
        target_id: databaseId,
        destination_ids: destinationIds,
        interval_seconds: intervalSeconds,
        retention,
        enabled
    };

    try {
        if (id) {
            await apiCall(`/automation/schedules/${id}`, 'PUT', payload);
            showStatus('Backup schedule updated successfully');
        } else {
            await apiCall('/automation/schedules', 'POST', payload);
            showStatus('Backup schedule created successfully');
        }
        hideBackupScheduleForm();
        await loadBackupSchedules();
    } catch (error) {
        showStatus(`Failed to save backup schedule: ${error.message}`, 'error');
    }
}

/**
 * Delete a backup schedule by id.
 * @param {string} id Schedule id.
 * @returns {Promise<void>}
 */
async function deleteBackupSchedule(id) {
    if (
        typeof hasAnyKeycloakRole === 'function'
        && !hasAnyKeycloakRole([BACKUP_ADMIN_ROLE, BACKUP_DELETE_ROLE])
    ) {
        showStatus('You do not have permission to delete schedules. Required role: backup:admin or backup:delete', 'error', true);
        return;
    }

    if (!confirm('Are you sure you want to delete this backup schedule?')) return;
    
    try {
        if (typeof keycloakApiDeleteCall !== 'function') {
            throw new Error('Delete helper not available');
        }
        await keycloakApiDeleteCall(`/automation/schedules/${id}`);
        showStatus('Backup schedule deleted');
        await loadBackupSchedules();
    } catch (error) {
        showStatus(`Failed to delete backup schedule: ${error.message}`, 'error', true);
    }
}

/**
 * Run a schedule immediately.
 * @param {string} scheduleId Schedule id.
 * @returns {Promise<void>}
 */
async function runScheduleNow(scheduleId) {
    if (typeof canRunBackups === 'function' && !canRunBackups()) {
        showStatus('You do not have permission to run schedules. Required role: backup:admin, backup:run, or backup:create', 'error', true);
        return;
    }

    if (!confirm('Run this backup schedule now?')) return;
    
    try {
        showStatus('Starting backup...', 'info');
        const result = await apiCall(`/automation/schedules/${scheduleId}/run-now`, 'POST');
        showStatus(`Backup completed! File: ${result.backup_filename || 'N/A'}`, 'success');
        await loadBackupSchedules();
    } catch (error) {
        showStatus(`Backup failed: ${error.message}`, 'error');
    }
}

/**
 * Initialize event listeners for backup schedules tab.
 * @returns {void}
 */
function initBackupSchedulesTab() {
    // Backup schedule form
    document.getElementById('add-backup-schedule-btn').addEventListener('click', () => showBackupScheduleForm());
    document.getElementById('run-enabled-schedules-btn')?.addEventListener('click', runEnabledSchedulesNow);
    document.getElementById('save-backup-schedule-btn').addEventListener('click', saveBackupSchedule);
    document.getElementById('cancel-backup-schedule-btn').addEventListener('click', hideBackupScheduleForm);

    const closeBtn = document.getElementById('backup-schedule-form-close-btn');
    if (closeBtn) {
        closeBtn.addEventListener('click', hideBackupScheduleForm);
    }
    
    // Retention type change
    const retentionTypeEl = document.getElementById('backup-schedule-retention-type');
    if (retentionTypeEl) {
        retentionTypeEl.addEventListener('change', updateRetentionTypeVisibility);
    }

    const intervalEl = document.getElementById('backup-schedule-interval');
    if (intervalEl) {
        intervalEl.addEventListener('change', updateScheduleTimeOfDayVisibility);
        updateScheduleTimeOfDayVisibility();
    }
    
    // Encryption toggle
    const encryptEl = document.getElementById('backup-schedule-encrypt');
    if (encryptEl) {
        encryptEl.addEventListener('change', updateEncryptionVisibility);
    }
    
    // Telegram toggle
    const telegramEl = document.getElementById('backup-schedule-notify-telegram');
    if (telegramEl) {
        telegramEl.addEventListener('change', updateTelegramVisibility);
    }
    
    // Email toggle
    const emailEl = document.getElementById('backup-schedule-notify-email');
    if (emailEl) {
        emailEl.addEventListener('change', updateEmailVisibility);
    }

    const addTelegramRecipientBtn = document.getElementById('backup-schedule-add-telegram-recipient');
    if (addTelegramRecipientBtn) {
        addTelegramRecipientBtn.addEventListener('click', () => {
            const container = document.getElementById('backup-schedule-telegram-recipients');
            if (!container) return;
            container.appendChild(createNotificationRecipientRow({ kind: 'telegram', value: '', minSeverity: 'error' }));
        });
    }

    const addEmailRecipientBtn = document.getElementById('backup-schedule-add-email-recipient');
    if (addEmailRecipientBtn) {
        addEmailRecipientBtn.addEventListener('click', () => {
            const container = document.getElementById('backup-schedule-email-recipients');
            if (!container) return;
            container.appendChild(createNotificationRecipientRow({ kind: 'email', value: '', minSeverity: 'error' }));
        });
    }

    const list = document.getElementById('backup-schedules-list');
    if (list) {
        list.addEventListener('click', (e) => {
            const btn = e.target.closest('button[data-action]');
            if (!btn) return;
            const action = btn.getAttribute('data-action');
            const id = btn.getAttribute('data-id');
            if (!id) return;

            if (action === 'schedule-run-now') {
                runScheduleNow(id);
            } else if (action === 'schedule-edit') {
                editBackupSchedule(id);
            } else if (action === 'schedule-delete') {
                deleteBackupSchedule(id);
            }
        });
    }

    updateBackupScheduleAccessUI();
}

window.updateBackupScheduleSelects = updateBackupScheduleSelects;
