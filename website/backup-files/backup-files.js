/**
 * Backup Files Tab JavaScript
 * 
 * Handles backup file management for the Backup Manager.
 */

// Backup Files Management Functions
async function loadBackupFiles() {
    try {
        // Load both local backup files and backup runs from automation
        const [localBackups, backupRuns] = await Promise.all([
            apiCall('/backup/files'),
            apiCall('/automation/runs')
        ]);
        
        backupFiles = localBackups;
        renderBackupFiles(backupRuns);
    } catch (error) {
        showStatus(`Failed to load backup files: ${error.message}`, 'error');
    }
}

function renderBackupFiles(backupRuns = []) {
    const container = document.getElementById('backup-files-list');
    
    if (backupFiles.length === 0 && backupRuns.length === 0) {
        container.innerHTML = '<p class="no-items">No backup files found. Run a backup to get started.</p>';
        return;
    }

    // Combine local files with automation runs for comprehensive view
    const allBackups = [
        ...backupFiles.map(file => ({
            ...file,
            type: 'local',
            source: 'Local Storage'
        })),
        ...backupRuns.map(run => ({
            id: run.id,
            filename: run.backup_filename || `backup_${run.id}`,
            created_at: run.created_at,
            size_mb: run.file_size_mb || 0,
            type: 'automation',
            source: `${run.target_name || 'Unknown'} → ${run.destination_name || 'Unknown'}`,
            status: run.status,
            schedule_name: run.schedule_name
        }))
    ];

    // Sort by creation date (newest first)
    allBackups.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    container.innerHTML = allBackups.map(backup => `
        <div class="item">
            <div class="item-header">
                <h3>${backup.filename}</h3>
                <div class="item-actions">
                    <button class="btn btn-sm btn-secondary" onclick="viewBackupDetails('${backup.id}', '${backup.type}')">Details</button>
                    ${backup.type === 'local' ? `
                        <button class="btn btn-sm btn-primary" onclick="downloadBackup('${backup.filename}')">Download</button>
                        <button class="btn btn-sm btn-warning" onclick="restoreFromBackup('${backup.filename}')">Restore</button>
                    ` : ''}
                    <button class="btn btn-sm btn-danger" onclick="deleteBackup('${backup.id}', '${backup.type}')">Delete</button>
                </div>
            </div>
            <div class="item-details">
                <p><strong>Type:</strong> ${backup.type === 'local' ? 'Local File' : 'Scheduled Backup'}</p>
                <p><strong>Source:</strong> ${backup.source}</p>
                ${backup.schedule_name ? `<p><strong>Schedule:</strong> ${backup.schedule_name}</p>` : ''}
                ${backup.status ? `<p><strong>Status:</strong> <span class="status ${backup.status}">${backup.status}</span></p>` : ''}
                <p><strong>Size:</strong> ${backup.size_mb ? `${backup.size_mb} MB` : 'Unknown'}</p>
                <p><strong>Created:</strong> ${new Date(backup.created_at).toLocaleString()}</p>
            </div>
        </div>
    `).join('');
}

async function viewBackupDetails(backupId, type) {
    try {
        let details;
        
        if (type === 'automation') {
            details = await apiCall(`/automation/runs/${backupId}`);
        } else {
            // For local files, get basic info
            const file = backupFiles.find(f => f.id === backupId);
            details = file;
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
        await apiCall(`/backup/restore/${filename}`, 'POST');
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
            await apiCall(`/automation/runs/${backupId}`, 'DELETE');
        } else {
            await apiCall(`/backup/files/${backupId}`, 'DELETE');
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
        const activeSchedules = schedules.filter(s => s.is_active);
        
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
        
        const result = await apiCall('/automation/runs', 'POST', {
            schedule_id: selectedSchedule.id
        });
        
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
}
