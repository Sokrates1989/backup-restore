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

function renderBackupSchedules() {
    const container = document.getElementById('backup-schedules-list');
    
    if (backupSchedules.length === 0) {
        container.innerHTML = '<p class="no-items">No backup schedules configured. Add one to get started.</p>';
        return;
    }

    container.innerHTML = backupSchedules.map(schedule => {
        const database = databases.find(d => d.id === schedule.target_id);
        const destinationNames = getDestinationNames(schedule.destination_ids);
        const retention = schedule.retention || {};
        const retentionText = retention.smart ? `Smart (d/w/m/y=${retention.smart.daily || 0}/${retention.smart.weekly || 0}/${retention.smart.monthly || 0}/${retention.smart.yearly || 0})` :
                             retention.max_count ? `${retention.max_count} backups` :
                             retention.max_days ? `${retention.max_days} days` :
                             retention.max_size_mb ? `${retention.max_size_mb} MB` : 'Default';
        const hasNotifications = schedule.retention?.notifications?.telegram?.enabled || 
                                 schedule.retention?.notifications?.email?.enabled;
        
        return `
            <div class="item">
                <div class="item-header">
                    <h3>${schedule.name}</h3>
                    <div class="item-actions">
                        <button class="btn btn-sm btn-success" onclick="runScheduleNow('${schedule.id}')">Run Now</button>
                        <button class="btn btn-sm btn-secondary" onclick="editBackupSchedule('${schedule.id}')">Edit</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteBackupSchedule('${schedule.id}')">Delete</button>
                    </div>
                </div>
                <div class="item-details">
                    <p><strong>Database:</strong> ${database ? database.name : 'Unknown'}</p>
                    <p><strong>Storage:</strong> ${destinationNames}</p>
                    <p><strong>Interval:</strong> ${formatInterval(schedule.interval_seconds)}</p>
                    <p><strong>Retention:</strong> ${retentionText}</p>
                    <p><strong>Encryption:</strong> ${schedule.retention?.encrypt ? 'Yes' : 'No'}</p>
                    <p><strong>Notifications:</strong> ${hasNotifications ? 'Enabled' : 'Disabled'}</p>
                    <p><strong>Status:</strong> <span class="status ${schedule.enabled ? 'active' : 'inactive'}">${schedule.enabled ? 'Active' : 'Inactive'}</span></p>
                    <p><strong>Next Run:</strong> ${schedule.next_run_at ? new Date(schedule.next_run_at).toLocaleString() : 'Not scheduled'}</p>
                    <p><strong>Last Run:</strong> ${schedule.last_run_at ? new Date(schedule.last_run_at).toLocaleString() : 'Never'}</p>
                </div>
            </div>
        `;
    }).join('');
}

function showBackupScheduleForm(schedule = null) {
    const form = document.getElementById('backup-schedule-form');
    const title = document.getElementById('backup-schedule-form-title');
    
    // Update select options
    updateBackupScheduleSelects();
    
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
        
        document.getElementById('backup-schedule-notify-telegram').checked = telegram.enabled || false;
        document.getElementById('backup-schedule-telegram-chat-id').value = telegram.chat_id || '';
        document.getElementById('backup-schedule-telegram-on-success').checked = telegram.on_success !== false;
        document.getElementById('backup-schedule-telegram-on-failure').checked = telegram.on_failure !== false;
        document.getElementById('backup-schedule-telegram-on-warning').checked = telegram.on_warning || false;
        updateTelegramVisibility();
        
        document.getElementById('backup-schedule-notify-email').checked = email.enabled || false;
        document.getElementById('backup-schedule-email-to').value = email.to || '';
        document.getElementById('backup-schedule-email-on-success').checked = email.on_success || false;
        document.getElementById('backup-schedule-email-on-failure').checked = email.on_failure !== false;
        document.getElementById('backup-schedule-email-on-warning').checked = email.on_warning !== false;
        updateEmailVisibility();
    } else {
        title.textContent = 'Add Backup Schedule';
        document.getElementById('backup-schedule-id').value = '';
        document.getElementById('backup-schedule-name').value = '';
        document.getElementById('backup-schedule-database').value = '';
        document.getElementById('backup-schedule-interval').value = '86400';
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
        document.getElementById('backup-schedule-telegram-chat-id').value = '';
        document.getElementById('backup-schedule-telegram-on-success').checked = true;
        document.getElementById('backup-schedule-telegram-on-failure').checked = true;
        document.getElementById('backup-schedule-telegram-on-warning').checked = false;
        updateTelegramVisibility();
        
        document.getElementById('backup-schedule-notify-email').checked = false;
        document.getElementById('backup-schedule-email-to').value = '';
        document.getElementById('backup-schedule-email-on-success').checked = false;
        document.getElementById('backup-schedule-email-on-failure').checked = true;
        document.getElementById('backup-schedule-email-on-warning').checked = true;
        updateEmailVisibility();
    }
    
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
    const localWarning = hasLocal && window.APP_IS_DEV ? `
        <div class="warning-box">
            <strong>⚠️ Testing Only</strong>
            Local storage should only be used for testing and development.
            For production, use SFTP or Google Drive.
        </div>
    ` : '';

    destinationsContainer.innerHTML = localWarning + locations.map(location => {
        const typeLabel = location.destination_type === 'local' ? '(Local)' : 
                         location.destination_type === 'sftp' ? '(SFTP)' : 
                         location.destination_type === 'google_drive' ? '(Google Drive)' : '';
        return `<label><input type="checkbox" value="${location.id}"> ${location.name} ${typeLabel}</label>`;
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
}

function updateTelegramVisibility() {
    const enabled = document.getElementById('backup-schedule-notify-telegram').checked;
    document.getElementById('backup-schedule-telegram-options').classList.toggle('hidden', !enabled);
}

function updateEmailVisibility() {
    const enabled = document.getElementById('backup-schedule-notify-email').checked;
    document.getElementById('backup-schedule-email-options').classList.toggle('hidden', !enabled);
}

async function saveBackupSchedule() {
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
        retention.notifications.telegram = {
            enabled: true,
            chat_id: trimValue(document.getElementById('backup-schedule-telegram-chat-id').value),
            on_success: document.getElementById('backup-schedule-telegram-on-success').checked,
            on_failure: document.getElementById('backup-schedule-telegram-on-failure').checked,
            on_warning: document.getElementById('backup-schedule-telegram-on-warning').checked,
        };
    }
    
    if (document.getElementById('backup-schedule-notify-email').checked) {
        retention.notifications.email = {
            enabled: true,
            to: trimValue(document.getElementById('backup-schedule-email-to').value),
            on_success: document.getElementById('backup-schedule-email-on-success').checked,
            on_failure: document.getElementById('backup-schedule-email-on-failure').checked,
            on_warning: document.getElementById('backup-schedule-email-on-warning').checked,
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

async function deleteBackupSchedule(id) {
    if (!confirm('Are you sure you want to delete this backup schedule?')) return;
    
    try {
        if (typeof apiDeleteCall !== 'function') {
            throw new Error('Delete helper not available');
        }
        await apiDeleteCall(`/automation/schedules/${id}`);
        showStatus('Backup schedule deleted');
        await loadBackupSchedules();
    } catch (error) {
        showStatus(`Failed to delete backup schedule: ${error.message}`, 'error', true);
    }
}

async function runScheduleNow(scheduleId) {
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

// Initialize event listeners for backup schedules tab
function initBackupSchedulesTab() {
    // Backup schedule form
    document.getElementById('add-backup-schedule-btn').addEventListener('click', () => showBackupScheduleForm());
    document.getElementById('save-backup-schedule-btn').addEventListener('click', saveBackupSchedule);
    document.getElementById('cancel-backup-schedule-btn').addEventListener('click', hideBackupScheduleForm);
    
    // Run now button
    const runNowBtn = document.getElementById('run-backup-schedule-now-btn');
    if (runNowBtn) {
        runNowBtn.addEventListener('click', async () => {
            const id = document.getElementById('backup-schedule-id').value;
            if (id) {
                await runScheduleNow(id);
            } else {
                showStatus('Please save the schedule first before running', 'error');
            }
        });
    }
    
    // Retention type change
    const retentionTypeEl = document.getElementById('backup-schedule-retention-type');
    if (retentionTypeEl) {
        retentionTypeEl.addEventListener('change', updateRetentionTypeVisibility);
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
}

window.updateBackupScheduleSelects = updateBackupScheduleSelects;
