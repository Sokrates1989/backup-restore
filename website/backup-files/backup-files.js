/**
 * Backup Files Tab JavaScript
 * 
 * Handles backup file management for the Backup Manager.
 * Supports browsing local and remote storage locations.
 */

let currentStorageLocation = 'all';

// Backup Files Management Functions
async function loadBackupFiles() {
    try {
        const location = document.getElementById('backup-files-storage-location')?.value || 'all';
        currentStorageLocation = location;
        
        let allBackups = [];

        let localFiles = [];
        let automationRuns = [];
        const automationLocalFilenames = new Set();
        
        if (location === 'all' || location === 'local') {
            try {
                const backupRuns = await apiCall('/automation/runs');
                automationRuns = Array.isArray(backupRuns) ? backupRuns : [];
                if (location === 'local') {
                    automationRuns = automationRuns.filter(r => (r.destination_id || '') === 'local');
                }

                automationRuns.forEach(run => {
                    const filename = run.backup_filename || '';
                    if ((run.destination_id || '') === 'local' && filename) {
                        automationLocalFilenames.add(filename);
                    }
                });
            } catch (e) {
                console.log('No automation runs or error loading:', e);
            }
        }

        if (location === 'all' || location === 'local') {
            // Load local backup files
            try {
                const localBackups = await apiCall('/backup/list');
                localFiles = (localBackups && localBackups.files) ? localBackups.files : [];
                localFiles = localFiles.filter(f => !automationLocalFilenames.has(f.filename));
            } catch (e) {
                console.log('No local backups or error loading:', e);
            }
        }

        if (automationRuns.length > 0) {
            allBackups = allBackups.concat(automationRuns.map(run => {
                const filename = run.backup_filename || `backup_${run.id}`;
                const localFilename = automationLocalFilenames.has(filename) ? filename : '';
                return {
                    id: run.id,
                    filename,
                    local_filename: localFilename,
                    created_at: run.created_at,
                    size_mb: run.file_size_mb || 0,
                    type: 'automation',
                    source: `${run.target_name || 'Unknown'} → ${run.destination_name || 'Unknown'}`,
                    status: run.status,
                    schedule_name: run.schedule_name,
                    destination_id: run.destination_id
                };
            }));
        }

        if (localFiles.length > 0) {
            allBackups = allBackups.concat(localFiles.map(file => ({
                id: file.filename,
                ...file,
                type: 'local',
                source: 'Local Storage',
                destination_id: 'local'
            })));
        }
        
        // Load from specific remote destination
        if (location !== 'all' && location !== 'local') {
            try {
                const remoteBackups = await apiCall(`/automation/destinations/${location}/backups`);
                if (remoteBackups && remoteBackups.length > 0) {
                    const dest = remoteStorageLocations.find(d => d.id === location);
                    allBackups = allBackups.concat(remoteBackups.map(file => ({
                        id: file.id || file.name,
                        filename: file.name,
                        created_at: file.created_at,
                        size_mb: file.size ? (file.size / 1024 / 1024).toFixed(2) : 0,
                        type: 'remote',
                        source: dest ? dest.name : 'Remote Storage',
                        destination_id: location
                    })));
                }
            } catch (e) {
                console.log('Error loading remote backups:', e);
            }
        }
        
        backupFiles = allBackups;
        renderBackupFiles();
    } catch (error) {
        showStatus(`Failed to load backup files: ${error.message}`, 'error', true);
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

function renderBackupFiles() {
    const container = document.getElementById('backup-files-list');
    
    if (backupFiles.length === 0) {
        container.innerHTML = '<p class="no-items">No backup files found. Run a backup to get started.</p>';
        return;
    }

    // Sort by creation date (newest first)
    const sortedBackups = [...backupFiles].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    container.innerHTML = sortedBackups.map(backup => {
        const typeLabel = backup.type === 'local' ? 'Local File' : 
                         backup.type === 'remote' ? 'Remote Storage' : 'Scheduled Backup';
        const downloadFilename = backup.local_filename || backup.filename;
        const canDownload = backup.type === 'local' || Boolean(backup.local_filename);
        const canRestore = backup.type === 'local' || Boolean(backup.local_filename);
        
        return `
            <div class="item">
                <div class="item-header">
                    <h3>${backup.filename}</h3>
                    <div class="item-actions">
                        <button class="btn btn-sm btn-secondary" onclick="viewBackupDetails('${backup.id}', '${backup.type}', '${backup.destination_id || ''}')">Details</button>
                        ${canDownload ? `
                            <button class="btn btn-sm btn-primary" onclick="downloadBackup('${downloadFilename}')">Download</button>
                        ` : ''}
                        ${canRestore ? `
                            <button class="btn btn-sm btn-warning" onclick="restoreFromBackup('${downloadFilename}')">Restore</button>
                        ` : ''}
                        <button class="btn btn-sm btn-danger" onclick="deleteBackup('${backup.id}', '${backup.type}', '${backup.destination_id || ''}')">Delete</button>
                    </div>
                </div>
                <div class="item-details">
                    <p><strong>Type:</strong> ${typeLabel}</p>
                    <p><strong>Source:</strong> ${backup.source}</p>
                    ${backup.schedule_name ? `<p><strong>Schedule:</strong> ${backup.schedule_name}</p>` : ''}
                    ${backup.status ? `<p><strong>Status:</strong> <span class="status ${backup.status}">${backup.status}</span></p>` : ''}
                    <p><strong>Size:</strong> ${(backup.size_mb === 0 || backup.size_mb) ? `${backup.size_mb} MB` : 'Unknown'}</p>
                    <p><strong>Created:</strong> ${backup.created_at ? new Date(backup.created_at).toLocaleString() : 'Unknown'}</p>
                </div>
            </div>
        `;
    }).join('');
}

async function viewBackupDetails(backupId, type) {
    try {
        let details;
        
        if (type === 'automation') {
            details = await apiCall(`/automation/runs/${backupId}`);
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
                    <span>${details.type === 'automation' ? 'Scheduled Backup' : 'Local File'}</span>
                </div>
                <div class="detail-item">
                    <label>Status:</label>
                    <span class="status ${details.status || 'unknown'}">${details.status || 'Unknown'}</span>
                </div>
                <div class="detail-item">
                    <label>Created:</label>
                    <span>${new Date(details.created_at).toLocaleString()}</span>
                </div>
                <div class="detail-item">
                    <label>Size:</label>
                    <span>${details.size_mb ? `${details.size_mb} MB` : 'Unknown'}</span>
                </div>
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
    
    modal.classList.remove('hidden');
}

function hideBackupDetailsModal() {
    document.getElementById('backup-details-modal').classList.add('hidden');
}

async function downloadBackup(filename) {
    try {
        const response = await fetch(`/backup/download/${filename}`, {
            headers: {
                'X-Admin-Key': adminToken
            }
        });
        
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
        
        showStatus('Backup downloaded successfully', 'success');
    } catch (error) {
        showStatus(`Failed to download backup: ${error.message}`, 'error');
    }
}

async function restoreFromBackup(filename) {
    if (!confirm(`Are you sure you want to restore from backup "${filename}"? This will overwrite the current database!`)) {
        return;
    }
    
    try {
        let restoreKey = localStorage.getItem('backup_restore_token') || '';
        if (!restoreKey) {
            restoreKey = prompt('Enter Restore API Key (X-Restore-Key):') || '';
            restoreKey = restoreKey.trim();
            if (!restoreKey) return;
            localStorage.setItem('backup_restore_token', restoreKey);
        }

        const response = await fetch(`/backup/restore/${filename}`, {
            method: 'POST',
            headers: {
                'X-Restore-Key': restoreKey
            }
        });

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || `HTTP ${response.status}`);
        }

        await response.json().catch(() => ({}));
        showStatus('Database restore initiated successfully', 'success');
        await loadBackupFiles();
    } catch (error) {
        showStatus(`Failed to restore backup: ${error.message}`, 'error');
    }
}

async function deleteBackup(backupId, type) {
    if (!confirm('Are you sure you want to delete this backup?')) return;
    
    try {
        if (type === 'automation') {
            if (typeof apiDeleteCall !== 'function') {
                throw new Error('Delete helper not available');
            }
            await apiDeleteCall(`/automation/runs/${backupId}`);
        } else {
            const file = backupFiles.find(f => (f.filename || '') === backupId);
            const filename = file ? file.filename : backupId;

            if (typeof apiDeleteCall !== 'function') {
                throw new Error('Delete helper not available');
            }
            await apiDeleteCall(`/backup/delete/${filename}`);
        }
        
        showStatus('Backup deleted successfully', 'success');
        await loadBackupFiles();
    } catch (error) {
        showStatus(`Failed to delete backup: ${error.message}`, 'error');
    }
}

async function runBackupNow() {
    try {
        const schedules = await apiCall('/automation/schedules');
        const activeSchedules = schedules.filter(s => s.enabled);
        
        if (activeSchedules.length === 0) {
            showStatus('No active backup schedules found', 'error');
            return;
        }
        
        // Create a simple selection dialog
        const scheduleName = prompt(`Available schedules:\n${activeSchedules.map((s, i) => `${i + 1}. ${s.name}`).join('\n')}\n\nEnter schedule number or name:`);
        
        if (!scheduleName) return;
        
        let selectedSchedule;
        
        // Try to parse as number
        const scheduleIndex = parseInt(scheduleName) - 1;
        if (scheduleIndex >= 0 && scheduleIndex < activeSchedules.length) {
            selectedSchedule = activeSchedules[scheduleIndex];
        } else {
            // Try to find by name
            selectedSchedule = activeSchedules.find(s => s.name.toLowerCase().includes(scheduleName.toLowerCase()));
        }
        
        if (!selectedSchedule) {
            showStatus('Schedule not found', 'error');
            return;
        }
        
        await apiCall(`/automation/schedules/${selectedSchedule.id}/run-now`, 'POST');
        
        showStatus('Backup started successfully', 'success');
        await loadBackupFiles();
    } catch (error) {
        showStatus(`Failed to run backup: ${error.message}`, 'error');
    }
}

// Initialize event listeners for backup files tab
function initBackupFilesTab() {
    // Backup actions
    document.getElementById('refresh-backup-files-btn').addEventListener('click', loadBackupFiles);
    document.getElementById('run-backup-btn').addEventListener('click', runBackupNow);
    
    // Storage location selector
    const storageSelect = document.getElementById('backup-files-storage-location');
    if (storageSelect) {
        storageSelect.addEventListener('change', loadBackupFiles);
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
    
    // Update storage selector when destinations are loaded
    updateBackupFilesStorageSelector();
}
