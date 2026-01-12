/**
 * Backup Schedules Tab JavaScript
 * 
 * Handles backup schedule management for the Backup Manager.
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

function renderBackupSchedules() {
    const container = document.getElementById('backup-schedules-list');
    
    if (backupSchedules.length === 0) {
        container.innerHTML = '<p class="no-items">No backup schedules configured. Add one to get started.</p>';
        return;
    }

    container.innerHTML = backupSchedules.map(schedule => {
        const database = databases.find(d => d.id === schedule.target_id);
        const remoteStorageLocation = remoteStorageLocations.find(l => l.id === schedule.destination_id);
        
        return `
            <div class="item">
                <div class="item-header">
                    <h3>${schedule.name}</h3>
                    <div class="item-actions">
                        <button class="btn btn-sm btn-secondary" onclick="editBackupSchedule('${schedule.id}')">Edit</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteBackupSchedule('${schedule.id}')">Delete</button>
                    </div>
                </div>
                <div class="item-details">
                    <p><strong>Database:</strong> ${database ? database.name : 'Unknown'}</p>
                    <p><strong>Remote Storage Location:</strong> ${remoteStorageLocation ? remoteStorageLocation.name : 'Unknown'}</p>
                    <p><strong>Interval:</strong> ${schedule.interval}</p>
                    <p><strong>Retention:</strong> ${schedule.retention_days || 30} days</p>
                    <p><strong>Status:</strong> <span class="status ${schedule.is_active ? 'active' : 'inactive'}">${schedule.is_active ? 'Active' : 'Inactive'}</span></p>
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
        document.getElementById('backup-schedule-remote-storage-location').value = schedule.destination_id || '';
        document.getElementById('backup-schedule-interval').value = schedule.interval || 'daily';
        document.getElementById('backup-schedule-retention').value = schedule.retention_days || 30;
        document.getElementById('backup-schedule-enabled').checked = schedule.is_active !== false;
    } else {
        title.textContent = 'Add Backup Schedule';
        document.getElementById('backup-schedule-id').value = '';
        document.getElementById('backup-schedule-name').value = '';
        document.getElementById('backup-schedule-database').value = '';
        document.getElementById('backup-schedule-remote-storage-location').value = '';
        document.getElementById('backup-schedule-interval').value = 'daily';
        document.getElementById('backup-schedule-retention').value = 30;
        document.getElementById('backup-schedule-enabled').checked = true;
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
    
    // Update remote storage location select
    const remoteStorageLocationSelect = document.getElementById('backup-schedule-remote-storage-location');
    remoteStorageLocationSelect.innerHTML = '<option value="">Select a remote storage location...</option>' +
        remoteStorageLocations.map(location => `<option value="${location.id}">${location.name}</option>`).join('');
}

async function saveBackupSchedule() {
    const id = document.getElementById('backup-schedule-id').value;
    const name = trimValue(document.getElementById('backup-schedule-name').value);
    const databaseId = document.getElementById('backup-schedule-database').value;
    const remoteStorageLocationId = document.getElementById('backup-schedule-remote-storage-location').value;
    const interval = document.getElementById('backup-schedule-interval').value;
    const retention = parseInt(document.getElementById('backup-schedule-retention').value) || 30;
    const enabled = document.getElementById('backup-schedule-enabled').checked;

    if (!name) {
        showStatus('Please enter a name', 'error');
        return;
    }
    
    if (!databaseId) {
        showStatus('Please select a database', 'error');
        return;
    }
    
    if (!remoteStorageLocationId) {
        showStatus('Please select a remote storage location', 'error');
        return;
    }

    const payload = {
        name,
        target_id: databaseId,
        destination_id: remoteStorageLocationId,
        interval,
        retention_days: retention,
        is_active: enabled
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
        await apiCall(`/automation/schedules/${id}`, 'DELETE');
        showStatus('Backup schedule deleted');
        await loadBackupSchedules();
    } catch (error) {
        showStatus(`Failed to delete backup schedule: ${error.message}`, 'error');
    }
}

// Initialize event listeners for backup schedules tab
function initBackupSchedulesTab() {
    // Backup schedule form
    document.getElementById('add-backup-schedule-btn').addEventListener('click', () => showBackupScheduleForm());
    document.getElementById('save-backup-schedule-btn').addEventListener('click', saveBackupSchedule);
    document.getElementById('cancel-backup-schedule-btn').addEventListener('click', hideBackupScheduleForm);
}
