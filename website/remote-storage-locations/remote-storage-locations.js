/**
 * Remote Storage Locations Tab JavaScript
 * 
 * Handles remote storage location management for the Backup Manager.
 */

// Remote Storage Locations Management Functions
async function loadRemoteStorageLocations() {
    try {
        remoteStorageLocations = await apiCall('/automation/destinations');
        renderRemoteStorageLocations();
    } catch (error) {
        showStatus(`Failed to load remote storage locations: ${error.message}`, 'error');
    }
}

function renderRemoteStorageLocations() {
    const container = document.getElementById('remote-storage-locations-list');

    const items = remoteStorageLocations.filter(l => l && l.id !== 'local' && l.destination_type !== 'local');
    
    if (items.length === 0) {
        container.innerHTML = '<p class="no-items">No remote storage locations configured. Add one to get started.</p>';
        return;
    }

    container.innerHTML = items.map(location => `
        <div class="item">
            <div class="item-header">
                <h3>${location.name}</h3>
                <div class="item-actions">
                    ${location.id === 'local' ? '' : `<button class="btn btn-sm btn-secondary" onclick="editRemoteStorageLocation('${location.id}')">Edit</button>`}
                    ${location.id === 'local' ? '' : `<button class="btn btn-sm btn-danger" onclick="deleteRemoteStorageLocation('${location.id}')">Delete</button>`}
                </div>
            </div>
            <div class="item-details">
                <p><strong>Type:</strong> ${location.destination_type}</p>
                ${getRemoteStorageLocationDetails(location)}
                <p><strong>Status:</strong> <span class="status ${location.is_active ? 'active' : 'inactive'}">${location.is_active ? 'Active' : 'Inactive'}</span></p>
            </div>
        </div>
    `).join('');
}

function getRemoteStorageLocationDetails(location) {
    switch (location.destination_type) {
        case 'local':
            return `<p><strong>Path:</strong> ${location.config.path || 'N/A'}</p>`;
        case 'sftp':
            return `
                <p><strong>Host:</strong> ${location.config.host || 'N/A'}</p>
                <p><strong>Port:</strong> ${location.config.port || 22}</p>
                <p><strong>Path:</strong> ${location.config.path || 'N/A'}</p>
            `;
        case 'google_drive':
            return `<p><strong>Folder ID:</strong> ${location.config.folder_id || 'N/A'}</p>`;
        default:
            return '';
    }
}

function showRemoteStorageLocationForm(location = null) {
    const form = document.getElementById('remote-storage-location-form');
    const title = document.getElementById('remote-storage-location-form-title');
    
    if (location) {
        title.textContent = 'Edit Remote Storage Location';
        document.getElementById('remote-storage-location-id').value = location.id;
        document.getElementById('remote-storage-location-name').value = location.name;
        document.getElementById('remote-storage-location-type').value = location.destination_type;
        
        // Set config based on type
        switch (location.destination_type) {
            case 'local':
                document.getElementById('remote-storage-local-path').value = location.config.path || '';
                break;
            case 'sftp':
                document.getElementById('remote-storage-sftp-host').value = location.config.host || '';
                document.getElementById('remote-storage-sftp-port').value = location.config.port || 22;
                document.getElementById('remote-storage-sftp-user').value = location.config.username || '';
                document.getElementById('remote-storage-sftp-password').value = '';
                const keyEl = document.getElementById('remote-storage-sftp-private-key');
                if (keyEl) {
                    keyEl.value = '';
                }
                const passphraseEl = document.getElementById('remote-storage-sftp-private-key-passphrase');
                if (passphraseEl) {
                    passphraseEl.value = '';
                }
                document.getElementById('remote-storage-sftp-path').value = location.config.path || '';
                break;
            case 'google_drive':
                document.getElementById('remote-storage-gdrive-folder').value = location.config.folder_id || '';
                document.getElementById('remote-storage-gdrive-credentials').value = '';
                break;
        }
        
        updateRemoteStorageLocationConfigVisibility();
    } else {
        title.textContent = 'Add Remote Storage Location';
        document.getElementById('remote-storage-location-id').value = '';
        document.getElementById('remote-storage-location-name').value = '';
        document.getElementById('remote-storage-location-type').value = 'sftp';
        document.getElementById('remote-storage-local-path').value = '/app/backups';
        document.getElementById('remote-storage-sftp-host').value = '';
        document.getElementById('remote-storage-sftp-port').value = 22;
        document.getElementById('remote-storage-sftp-user').value = '';
        document.getElementById('remote-storage-sftp-password').value = '';
        const keyEl = document.getElementById('remote-storage-sftp-private-key');
        if (keyEl) {
            keyEl.value = '';
        }
        const passphraseEl = document.getElementById('remote-storage-sftp-private-key-passphrase');
        if (passphraseEl) {
            passphraseEl.value = '';
        }
        document.getElementById('remote-storage-sftp-path').value = '';
        document.getElementById('remote-storage-gdrive-folder').value = '';
        document.getElementById('remote-storage-gdrive-credentials').value = '';
        
        updateRemoteStorageLocationConfigVisibility();
    }
    
    form.classList.remove('hidden');
}

function hideRemoteStorageLocationForm() {
    document.getElementById('remote-storage-location-form').classList.add('hidden');
    if (typeof clearStatusMessages === 'function') {
        clearStatusMessages();
    }
}

function editRemoteStorageLocation(id) {
    const location = remoteStorageLocations.find(l => l.id === id);
    if (location) showRemoteStorageLocationForm(location);
}

function updateRemoteStorageLocationConfigVisibility() {
    const type = document.getElementById('remote-storage-location-type').value;
    
    // Hide all config sections
    document.getElementById('remote-storage-local-config').classList.add('hidden');
    document.getElementById('remote-storage-sftp-config').classList.add('hidden');
    document.getElementById('remote-storage-gdrive-config').classList.add('hidden');
    
    // Show relevant config section
    const sectionId = type === 'google_drive' ? 'remote-storage-gdrive-config' : `remote-storage-${type}-config`;
    const section = document.getElementById(sectionId);
    if (section) {
        section.classList.remove('hidden');
    }
}

async function testRemoteStorageLocationConnection() {
    const name = document.getElementById('remote-storage-location-name').value.trim();
    const type = document.getElementById('remote-storage-location-type').value;

    if (!name) {
        showStatus('Please enter a name to test connection', 'error');
        return;
    }

    let config = {};
    let secrets = {};

    switch (type) {
        case 'local':
            config.path = document.getElementById('remote-storage-local-path').value.trim();
            if (!config.path) {
                showStatus('Please enter a path to test connection', 'error');
                return;
            }
            break;
        case 'sftp':
            config.host = document.getElementById('remote-storage-sftp-host').value.trim();
            config.port = parseInt(document.getElementById('remote-storage-sftp-port').value) || 22;
            config.path = document.getElementById('remote-storage-sftp-path').value.trim();
            config.username = document.getElementById('remote-storage-sftp-user').value.trim();

            const sftpPrivateKey = trimValue(document.getElementById('remote-storage-sftp-private-key')?.value);
            const sftpPassphrase = trimValue(document.getElementById('remote-storage-sftp-private-key-passphrase')?.value);
            const sftpPassword = trimValue(document.getElementById('remote-storage-sftp-password').value);

            if (sftpPrivateKey) {
                secrets.private_key = sftpPrivateKey;
                if (sftpPassphrase) {
                    secrets.private_key_passphrase = sftpPassphrase;
                }
            } else {
                if (!sftpPassword) {
                    showStatus('Please enter either a password or a private key to test connection', 'error');
                    return;
                }
                secrets.password = sftpPassword;
            }
            
            if (!config.host || !config.username) {
                showStatus('Please fill in host and username to test connection', 'error');
                return;
            }
            break;
        case 'google_drive':
            config.folder_id = document.getElementById('remote-storage-gdrive-folder').value.trim();
            const creds = document.getElementById('remote-storage-gdrive-credentials').value.trim();
            if (!creds) {
                showStatus('Please enter service account credentials to test connection', 'error');
                return;
            }
            try {
                JSON.parse(creds);
                secrets.service_account_json = creds;
            } catch {
                showStatus('Invalid JSON for service account credentials', 'error');
                return;
            }
            break;
    }

    const payload = {
        name,
        destination_type: type,
        config,
    };

    if (Object.keys(secrets).length > 0) {
        payload.secrets = secrets;
    }

    try {
        const result = await apiCall('/automation/destinations/test-connection', 'POST', payload);
        if (result.success) {
            showStatus('Connection test successful!', 'success');
        } else {
            showStatus(`Connection test failed: ${result.message}`, 'error');
        }
    } catch (error) {
        showStatus(`Connection test failed: ${error.message}`, 'error');
    }
}

async function saveRemoteStorageLocation() {
    const id = document.getElementById('remote-storage-location-id').value;
    const name = document.getElementById('remote-storage-location-name').value.trim();
    const type = document.getElementById('remote-storage-location-type').value;

    const existing = id ? remoteStorageLocations.find(l => l.id === id) : null;
    const existingType = existing ? existing.destination_type : null;

    if (!name) {
        showStatus('Please enter a name', 'error');
        return;
    }

    let config = {};
    let secrets = {};

    switch (type) {
        case 'local':
            config.path = document.getElementById('remote-storage-local-path').value.trim();
            break;
        case 'sftp':
            config.host = document.getElementById('remote-storage-sftp-host').value.trim();
            config.port = parseInt(document.getElementById('remote-storage-sftp-port').value) || 22;
            config.username = document.getElementById('remote-storage-sftp-user').value.trim();
            config.path = document.getElementById('remote-storage-sftp-path').value.trim();

            const sftpPrivateKey = trimValue(document.getElementById('remote-storage-sftp-private-key')?.value);
            const sftpPassphrase = trimValue(document.getElementById('remote-storage-sftp-private-key-passphrase')?.value);
            const sftpPassword = trimValue(document.getElementById('remote-storage-sftp-password').value);

            if (sftpPrivateKey) {
                secrets.private_key = sftpPrivateKey;
                if (sftpPassphrase) {
                    secrets.private_key_passphrase = sftpPassphrase;
                }
            } else if (sftpPassword) {
                secrets.password = sftpPassword;
            }
            break;
        case 'google_drive':
            config.folder_id = document.getElementById('remote-storage-gdrive-folder').value.trim();
            const creds = document.getElementById('remote-storage-gdrive-credentials').value.trim();
            if (creds) {
                try {
                    JSON.parse(creds);
                    secrets.service_account_json = creds;
                } catch {
                    showStatus('Invalid JSON for service account credentials', 'error');
                    return;
                }
            }
            break;
    }

    const payload = {
        name,
        destination_type: type,
        config
    };

    if (Object.keys(secrets).length > 0 || !id) {
        payload.secrets = secrets;
    }

    if (id && existingType && existingType !== type && Object.keys(secrets).length === 0) {
        showStatus('Changing destination type requires providing the new credentials again', 'error');
        return;
    }

    try {
        if (!id || Object.keys(secrets).length > 0 || type === 'local') {
            const testResult = await apiCall('/automation/destinations/test-connection', 'POST', payload);
            if (!testResult.success) {
                showStatus(`Cannot save remote storage location - connection test failed: ${testResult.message}`, 'error');
                return;
            }
        }

        if (id) {
            await apiCall(`/automation/destinations/${id}`, 'PUT', payload);
            showStatus('Remote storage location updated successfully');
        } else {
            await apiCall('/automation/destinations', 'POST', payload);
            showStatus('Remote storage location created successfully');
        }
        hideRemoteStorageLocationForm();
        await loadRemoteStorageLocations();
        if (typeof updateScheduleSelects === 'function') {
            updateScheduleSelects();
        }
    } catch (error) {
        showStatus(`Failed to save remote storage location: ${error.message}`, 'error');
    }
}

async function deleteRemoteStorageLocation(id) {
    if (!confirm('Are you sure you want to delete this remote storage location?')) return;
    
    try {
        if (typeof apiDeleteCall !== 'function') {
            throw new Error('Delete helper not available');
        }
        await apiDeleteCall(`/automation/destinations/${id}`);
        showStatus('Remote storage location deleted');
        await loadRemoteStorageLocations();
        if (typeof updateScheduleSelects === 'function') {
            updateScheduleSelects();
        }
    } catch (error) {
        showStatus(`Failed to delete remote storage location: ${error.message}`, 'error');
    }
}

// Initialize event listeners for remote storage locations tab
function initRemoteStorageLocationsTab() {
    // Remote storage location form
    document.getElementById('add-remote-storage-location-btn').addEventListener('click', () => showRemoteStorageLocationForm());
    document.getElementById('test-remote-storage-location-connection-btn').addEventListener('click', testRemoteStorageLocationConnection);
    document.getElementById('save-remote-storage-location-btn').addEventListener('click', saveRemoteStorageLocation);
    document.getElementById('cancel-remote-storage-location-btn').addEventListener('click', hideRemoteStorageLocationForm);
    document.getElementById('remote-storage-location-type').addEventListener('change', updateRemoteStorageLocationConfigVisibility);
}
