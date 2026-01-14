/**
 * Databases Tab JavaScript
 * 
 * Handles database management for the Backup Manager.
 */

// Database Management Functions
/**
 * Load backup targets (databases) from the API and refresh the UI.
 * @returns {Promise<void>}
 */
async function loadDatabases() {
    try {
        databases = await apiCall('/automation/targets');
        renderDatabases();
    } catch (error) {
        showStatus(`Failed to load databases: ${error.message}`, 'error');
    }
}

/**
 * Render the databases list into the DOM.
 * @returns {void}
 */
function renderDatabases() {
    const container = document.getElementById('databases-list');
    
    if (databases.length === 0) {
        container.innerHTML = '<p class="no-items">No databases configured. Add one to get started.</p>';
        return;
    }

    container.innerHTML = databases.map(database => `
        <div class="item">
            <div class="item-header">
                <h3>${database.name}</h3>
                <div class="item-actions">
                    <button class="btn btn-sm btn-success" data-action="db-backup" data-id="${database.id}">Backup</button>
                    <button class="btn btn-sm btn-warning" data-action="db-restore" data-id="${database.id}">Restore</button>
                    <button class="btn btn-sm btn-secondary" data-action="db-edit" data-id="${database.id}">Edit</button>
                    <button class="btn btn-sm btn-danger" data-action="db-delete" data-id="${database.id}">Delete</button>
                </div>
            </div>
            <div class="item-details">
                <p><strong>Type:</strong> ${database.db_type}</p>
                <p><strong>Host:</strong> ${database.config.host || 'N/A'}</p>
                <p><strong>Database:</strong> ${database.config.database || 'N/A'}</p>
                <p><strong>Status:</strong> <span class="status ${database.is_active ? 'active' : 'inactive'}">${database.is_active ? 'Active' : 'Inactive'}</span></p>
            </div>
        </div>
    `).join('');
}

/**
 * Show the add/edit database form.
 * @param {Object|null} database Database object when editing, otherwise null.
 * @returns {void}
 */
function showDatabaseForm(database = null) {
    const form = document.getElementById('database-form');
    const title = document.getElementById('database-form-title');
    
    if (database) {
        title.textContent = 'Edit Database';
        document.getElementById('database-id').value = database.id;
        document.getElementById('database-name').value = database.name;
        document.getElementById('database-db-type').value = database.db_type;
        document.getElementById('database-host').value = database.config.host || '';
        document.getElementById('database-port').value = database.config.port || '';
        document.getElementById('database-database').value = database.config.database || '';
        document.getElementById('database-user').value = database.config.user || '';
        document.getElementById('database-password').value = '';
    } else {
        title.textContent = 'Add Database';
        document.getElementById('database-id').value = '';
        document.getElementById('database-name').value = '';
        document.getElementById('database-db-type').value = 'postgresql';
        document.getElementById('database-host').value = '';
        document.getElementById('database-port').value = '';
        document.getElementById('database-database').value = '';
        document.getElementById('database-user').value = '';
        document.getElementById('database-password').value = '';
    }
    
    form.classList.remove('hidden');
    updateDatabaseFormUX();
}

/**
 * Update the database form UX (labels/placeholders/help text) based on the selected DB type.
 * @returns {void}
 */
function updateDatabaseFormUX() {
    const dbTypeEl = document.getElementById('database-db-type');
    const helpEl = document.getElementById('database-connection-help');
    const hostEl = document.getElementById('database-host');
    const portEl = document.getElementById('database-port');
    const databaseLabelEl = document.querySelector('label[for="database-database"]');
    const databaseEl = document.getElementById('database-database');
    const userEl = document.getElementById('database-user');
    const passwordEl = document.getElementById('database-password');

    const dbType = dbTypeEl ? dbTypeEl.value : 'postgresql';

    if (databaseLabelEl) {
        databaseLabelEl.textContent = dbType === 'sqlite' ? 'SQLite File Path' : 'Database Name';
    }

    if (databaseEl) {
        databaseEl.placeholder = dbType === 'sqlite' ? 'e.g., /data/test.db' : 'e.g., myapp';
    }

    if (hostEl) {
        hostEl.placeholder = dbType === 'sqlite' ? '(not required for SQLite)' : 'e.g., localhost or db-service';
    }

    if (portEl) {
        portEl.placeholder = dbType === 'postgresql' ? 'e.g., 5432' : (dbType === 'neo4j' ? 'e.g., 7687' : (dbType === 'mysql' ? 'e.g., 3306' : '(not required)'));
    }

    if (userEl) {
        userEl.placeholder = dbType === 'neo4j' ? '(optional if Neo4j auth is disabled)' : (dbType === 'sqlite' ? '(not required for SQLite)' : 'Database username');
    }

    if (passwordEl) {
        passwordEl.placeholder = dbType === 'neo4j' ? '(optional if Neo4j auth is disabled)' : (dbType === 'sqlite' ? '(not required for SQLite)' : 'Database password (encrypted at rest)');
    }

    if (helpEl) {
        const isDev = window.APP_IS_DEV;

        const renderHelp = (localLine, swarmLine) => {
            if (isDev === true) {
                helpEl.innerHTML = localLine;
                return;
            }
            if (isDev === false) {
                helpEl.innerHTML = swarmLine;
                return;
            }

            helpEl.innerHTML = `${localLine}<br/>${swarmLine}`;
        };

        if (dbType === 'postgresql') {
            const localLine = '<strong>Local (if launched with Test DBs):</strong> host=localhost, port=5434, db=testdb, user=testuser, password=testpass';
            const swarmLine = '<strong>Swarm/Docker:</strong> use the service DNS name and internal port (typically 5432). If the DB runs on your host machine while API runs in Docker, use host.docker.internal.';
            renderHelp(localLine, swarmLine);
        } else if (dbType === 'mysql') {
            const localLine = '<strong>Local (if launched with Test DBs):</strong> host=localhost, port=3306, db=testdb, user=testuser (or root), password=testpass (or rootpass)';
            const swarmLine = '<strong>Swarm/Docker:</strong> use the service DNS name and internal port (3306). If the DB runs on your host machine while API runs in Docker, use host.docker.internal.';
            renderHelp(localLine, swarmLine);
        } else if (dbType === 'neo4j') {
            const localLine = '<strong>Local (if launched with Test DBs):</strong> host=localhost, port=7688, user/pass empty (auth disabled)';
            const swarmLine = '<strong>Swarm/Docker:</strong> use the service DNS name and internal port (7687).';
            renderHelp(localLine, swarmLine);
        } else if (dbType === 'sqlite') {
            const localLine = '<strong>Local (if launched with Test DBs):</strong> /data/test.db (mounted into the API container)';
            const swarmLine = '<strong>Swarm/Docker:</strong> the path must exist inside the container / service that runs the backup.';
            renderHelp(localLine, swarmLine);
        } else {
            helpEl.innerHTML = '';
        }
    }
}

/**
 * Hide the database form.
 * @returns {void}
 */
function hideDatabaseForm() {
    document.getElementById('database-form').classList.add('hidden');
    if (typeof clearStatusMessages === 'function') {
        clearStatusMessages();
    }
}

/**
 * Open the form in edit mode for an existing database by id.
 * @param {string} id Database id.
 * @returns {void}
 */
function editDatabase(id) {
    const database = databases.find(d => d.id === id);
    if (database) showDatabaseForm(database);
}

/**
 * Call the backend connection test endpoint with the current form values.
 * @returns {Promise<void>}
 */
async function testDatabaseConnection() {
    const name = trimValue(document.getElementById('database-name').value);
    const db_type = document.getElementById('database-db-type').value;
    const host = trimValue(document.getElementById('database-host').value);
    const port = parseInt(document.getElementById('database-port').value) || null;
    const database = trimValue(document.getElementById('database-database').value);
    const user = trimValue(document.getElementById('database-user').value);
    const password = trimValue(document.getElementById('database-password').value);

    if (!name) {
        showStatus('Please enter a name to test connection', 'error');
        return;
    }

    if (db_type === 'sqlite') {
        if (!database) {
            showStatus('Please provide a SQLite file path (e.g., /data/test.db)', 'error');
            return;
        }
    } else if (db_type === 'neo4j') {
        if (!host) {
            showStatus('Please fill in host to test connection', 'error');
            return;
        }
    } else {
        if (!host || !database || !user) {
            showStatus('Please fill in all required fields to test connection', 'error');
            return;
        }
    }

    const config = { host, port, database, user };
    if (db_type === 'sqlite') {
        config.path = database;
    }
    const payload = {
        name,
        db_type,
        config,
        secrets: password ? { password } : {}
    };

    try {
        const result = await apiCall('/automation/targets/test-connection', 'POST', payload);
        if (result.success) {
            showStatus('Connection test successful!', 'success');
        } else {
            showStatus(`Connection test failed: ${result.message}`, 'error');
        }
    } catch (error) {
        showStatus(`Connection test failed: ${error.message}`, 'error');
    }
}

/**
 * Create or update a database target using the automation API.
 * @returns {Promise<void>}
 */
async function saveDatabase() {
    const id = document.getElementById('database-id').value;
    const name = trimValue(document.getElementById('database-name').value);
    const db_type = document.getElementById('database-db-type').value;
    const host = trimValue(document.getElementById('database-host').value);
    const port = parseInt(document.getElementById('database-port').value) || null;
    const database = trimValue(document.getElementById('database-database').value);
    const user = trimValue(document.getElementById('database-user').value);
    const password = trimValue(document.getElementById('database-password').value);

    if (!name) {
        showStatus('Please enter a name', 'error');
        return;
    }

    if (db_type === 'sqlite') {
        if (!database) {
            showStatus('Please provide a SQLite file path (e.g., /data/test.db)', 'error');
            return;
        }
    } else if (db_type === 'neo4j') {
        if (!host) {
            showStatus('Please fill in host', 'error');
            return;
        }
    } else {
        if (!host || !database || !user) {
            showStatus('Please fill in all required fields', 'error');
            return;
        }
    }

    const config = { host, port, database, user };
    if (db_type === 'sqlite') {
        config.path = database;
    }

    const payload = {
        name,
        db_type,
        config,
        secrets: password ? { password } : {}
    };

    try {
        // Test connection before saving
        const testResult = await apiCall('/automation/targets/test-connection', 'POST', payload);
        if (!testResult.success) {
            showStatus(`Cannot save database - connection test failed: ${testResult.message}`, 'error');
            return;
        }

        if (id) {
            await apiCall(`/automation/targets/${id}`, 'PUT', payload);
            showStatus('Database updated successfully');
        } else {
            await apiCall('/automation/targets', 'POST', payload);
            showStatus('Database created successfully');
        }
        hideDatabaseForm();
        await loadDatabases();
        updateScheduleSelects();
    } catch (error) {
        showStatus(`Failed to save database: ${error.message}`, 'error', true);
    }
}

/**
 * Delete a database target by id.
 * @param {string} id Database id.
 * @returns {Promise<void>}
 */
async function deleteDatabase(id) {
    if (!confirm('Are you sure you want to delete this database?')) return;
    
    try {
        if (typeof apiDeleteCall !== 'function') {
            throw new Error('Delete helper not available');
        }
        await apiDeleteCall(`/automation/targets/${id}`);
        showStatus('Database deleted');
        await loadDatabases();
        updateScheduleSelects();
    } catch (error) {
        showStatus(`Failed to delete database: ${error.message}`, 'error', true);
    }
}

// Backup/Restore Modal Functions
/**
 * Set status text inside the backup/restore modal.
 * @param {string} message Status message.
 * @param {string} type Status type (success|info|warning|error).
 * @param {boolean|null} persist When true, do not auto-hide; when null, defaults to persisting errors/warnings.
 * @returns {void}
 */
function setDatabaseActionStatus(message, type = 'success', persist = null) {
    const el = document.getElementById('database-action-status');
    if (!el) {
        showStatus(message, type, persist);
        return;
    }

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
            el.classList.add('hidden');
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
 * Hide the backup/restore modal status area.
 * @returns {void}
 */
function clearDatabaseActionStatus() {
    const el = document.getElementById('database-action-status');
    if (el) {
        el.classList.add('hidden');
    }
}

/**
 * Show the backup/restore modal for a given database and action.
 * @param {string} databaseId Database id.
 * @param {string} actionType Either 'backup' or 'restore'.
 * @returns {void}
 */
function showDatabaseActionModal(databaseId, actionType) {
    const database = databases.find(d => d.id === databaseId);
    if (!database) {
        showStatus('Database not found', 'error');
        return;
    }

    const modal = document.getElementById('database-action-modal');
    const title = document.getElementById('database-action-modal-title');
    const restoreSourceDiv = document.getElementById('database-action-restore-source');
    const encryptionGroup = document.getElementById('database-action-encryption-password-group');
    const encryptionInput = document.getElementById('database-action-encryption-password');
    
    document.getElementById('database-action-target-id').value = databaseId;
    document.getElementById('database-action-type').value = actionType;
    
    if (actionType === 'backup') {
        title.textContent = `Backup: ${database.name}`;
        restoreSourceDiv.classList.add('hidden');
    } else {
        title.textContent = `Restore: ${database.name}`;
        restoreSourceDiv.classList.remove('hidden');
    }

    if (encryptionGroup) {
        encryptionGroup.classList.add('hidden');
    }
    if (encryptionInput) {
        encryptionInput.value = '';
    }
    
    updateDatabaseActionDestinations(actionType);
    clearDatabaseActionStatus();
    modal.classList.remove('hidden');
}

/**
 * Hide the backup/restore modal.
 * @returns {void}
 */
function hideDatabaseActionModal() {
    document.getElementById('database-action-modal').classList.add('hidden');
    document.getElementById('database-action-local-warning').classList.add('hidden');
    const encryptionGroup = document.getElementById('database-action-encryption-password-group');
    const encryptionInput = document.getElementById('database-action-encryption-password');
    if (encryptionGroup) {
        encryptionGroup.classList.add('hidden');
    }
    if (encryptionInput) {
        encryptionInput.value = '';
    }
    clearDatabaseActionStatus();
}

/**
 * Populate destination select for backup/restore actions.
 * @param {string} actionType Either 'backup' or 'restore'.
 * @returns {void}
 */
function updateDatabaseActionDestinations(actionType) {
    const select = document.getElementById('database-action-destination');
    select.innerHTML = '<option value="">Select storage location...</option>';
    
    // Always add built-in local storage as default option (uses /app/backups)
    select.innerHTML += '<option value="__local__" data-type="local">Local Storage (Default)</option>';
    
    // Add configured remote storage locations
    remoteStorageLocations
        .filter(location => location && location.id !== 'local' && location.destination_type !== 'local')
        .forEach(location => {
        const typeLabel = location.destination_type === 'local' ? '(Local Directory)' : 
                         location.destination_type === 'sftp' ? '(SFTP)' : 
                         location.destination_type === 'google_drive' ? '(Google Drive)' : '';
        select.innerHTML += `<option value="${location.id}" data-type="${location.destination_type}">${location.name} ${typeLabel}</option>`;
    });
    
    // Reset warning
    document.getElementById('database-action-local-warning').classList.add('hidden');
    
    // Reset backup file selector
    if (actionType === 'restore') {
        document.getElementById('database-action-backup-file').innerHTML = '<option value="">Select backup file...</option>';
    }
}

/**
 * Handle destination change: show local warnings and (for restore) load backup list.
 * @returns {Promise<void>}
 */
async function handleDatabaseActionDestinationChange() {
    const select = document.getElementById('database-action-destination');
    const selectedOption = select.options[select.selectedIndex];
    const destType = selectedOption ? selectedOption.getAttribute('data-type') : '';
    const warningDiv = document.getElementById('database-action-local-warning');
    const actionType = document.getElementById('database-action-type').value;
    
    // Show/hide local warning
    if (destType === 'local') {
        warningDiv.classList.remove('hidden');
    } else {
        warningDiv.classList.add('hidden');
    }
    
    // For restore, load available backup files from this destination
    if (actionType === 'restore' && select.value) {
        await loadBackupFilesForDestination(select.value);
    }

    updateDatabaseActionEncryptionVisibility();
}

/**
 * Load backups for the selected destination and populate the restore dropdown.
 * @param {string} destinationId Destination id or '__local__'.
 * @returns {Promise<void>}
 */
async function loadBackupFilesForDestination(destinationId) {
    const backupFileSelect = document.getElementById('database-action-backup-file');
    const targetId = document.getElementById('database-action-target-id').value;
    const target = Array.isArray(databases) ? databases.find(d => d && d.id === targetId) : null;
    const targetDbType = target ? String(target.db_type || '').toLowerCase() : '';
    
    try {
        backupFileSelect.innerHTML = '<option value="">Loading...</option>';
        
        // Load backup files from this destination
        let files;
        if (destinationId === '__local__') {
            const result = await apiCall('/backup/list');
            files = result.files || [];

            if (targetDbType) {
                const allowedSuffixes =
                    targetDbType === 'neo4j'
                        ? ['.cypher', '.cypher.gz', '.cypher.enc', '.cypher.gz.enc']
                        : targetDbType === 'sqlite'
                            ? ['.db', '.db.gz', '.db.enc', '.db.gz.enc']
                            : ['.sql', '.sql.gz', '.sql.enc', '.sql.gz.enc'];
                files = files.filter(f => {
                    const name = String((f && f.filename) ? f.filename : '').toLowerCase();
                    return allowedSuffixes.some(s => name.endsWith(s));
                });
            }
        } else {
            files = await apiCall(`/automation/destinations/${destinationId}/backups?target_id=${targetId}`);
        }
        
        backupFileSelect.innerHTML = '<option value="">Select backup file...</option>';
        
        if (files && files.length > 0) {
            files.forEach(file => {
                const value = destinationId === '__local__' ? (file.filename || '') : (file.id || '');
                const label = file.filename || file.name || file.id || '';
                const lowerLabel = String(label || '').toLowerCase();
                const isEncrypted = lowerLabel.endsWith('.enc');
                const date = file.created_at ? new Date(file.created_at).toLocaleString() : 'Unknown';
                const size = file.size_mb ? `${file.size_mb} MB` : (file.size ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : '');
                backupFileSelect.innerHTML += `<option value="${value}" data-encrypted="${isEncrypted ? 'true' : 'false'}">${label} (${date}) ${size}</option>`;
            });
        } else {
            backupFileSelect.innerHTML = '<option value="">No backups found</option>';
        }

        updateDatabaseActionEncryptionVisibility();
    } catch (error) {
        backupFileSelect.innerHTML = '<option value="">Error loading backups</option>';
        console.error('Failed to load backup files:', error);
    }
}

/**
 * Show or hide the encryption password input depending on the selected backup.
 * @returns {void}
 */
function updateDatabaseActionEncryptionVisibility() {
    const groupEl = document.getElementById('database-action-encryption-password-group');
    const inputEl = document.getElementById('database-action-encryption-password');
    const actionType = document.getElementById('database-action-type')?.value || '';
    const backupSelect = document.getElementById('database-action-backup-file');

    if (!groupEl || !inputEl) return;
    if (actionType !== 'restore' || !backupSelect) {
        groupEl.classList.add('hidden');
        inputEl.value = '';
        return;
    }

    const selectedOption = backupSelect.options[backupSelect.selectedIndex];
    const encrypted = (selectedOption && selectedOption.getAttribute('data-encrypted') === 'true') || false;
    groupEl.classList.toggle('hidden', !encrypted);
    if (!encrypted) {
        inputEl.value = '';
    }
}

/**
 * Execute the selected modal action (backup or restore) for the selected database.
 * @returns {Promise<void>}
 */
async function executeDatabaseAction() {
    const targetId = document.getElementById('database-action-target-id').value;
    const actionType = document.getElementById('database-action-type').value;
    const destinationId = document.getElementById('database-action-destination').value;
    
    if (!destinationId) {
        setDatabaseActionStatus('Please select a storage location', 'error');
        return;
    }
    
    const database = databases.find(d => d.id === targetId);
    const isDefaultLocal = destinationId === '__local__';
    const destination = isDefaultLocal ? { name: 'Local Storage' } : remoteStorageLocations.find(d => d.id === destinationId);
    
    try {
        if (actionType === 'backup') {
            // Execute immediate backup
            setDatabaseActionStatus(`Starting backup of ${database.name} to ${destination.name}...`, 'info', false);
            
            const payload = {
                target_id: targetId,
                use_local_storage: isDefaultLocal
            };
            if (!isDefaultLocal) {
                payload.destination_ids = [destinationId];
            }
            
            const result = await apiCall('/automation/backup-now', 'POST', payload);

            showStatus(`Backup completed successfully! File: ${result.backup_filename || 'N/A'}`, 'success');
        } else {
            // Execute restore
            const backupFileId = document.getElementById('database-action-backup-file').value;
            
            if (!backupFileId) {
                setDatabaseActionStatus('Please select a backup file to restore', 'error');
                return;
            }
            
            if (!confirm(`Are you sure you want to restore ${database.name} from backup? This will overwrite the current database!`)) {
                return;
            }

            const typedConfirmation = (prompt('Type RESTORE to confirm this restore operation:') || '').trim();
            if (typedConfirmation !== 'RESTORE') {
                setDatabaseActionStatus('Restore cancelled: confirmation text did not match RESTORE', 'error', true);
                return;
            }
            
            setDatabaseActionStatus(`Starting restore of ${database.name}...`, 'info', false);
            
            const restorePayload = {
                target_id: targetId,
                backup_id: backupFileId,
                confirmation: typedConfirmation,
                use_local_storage: isDefaultLocal
            };
            if (!isDefaultLocal) {
                restorePayload.destination_id = destinationId;
            }

            const selectedOption = document.getElementById('database-action-backup-file')?.options[
                document.getElementById('database-action-backup-file')?.selectedIndex
            ];
            const isEncrypted = (selectedOption && selectedOption.getAttribute('data-encrypted') === 'true') || false;
            if (isEncrypted) {
                const pwd = trimValue(document.getElementById('database-action-encryption-password')?.value);
                if (!pwd) {
                    setDatabaseActionStatus('This backup is encrypted. Please enter the encryption password.', 'error', true);
                    return;
                }
                restorePayload.encryption_password = pwd;
            }
            
            if (typeof apiRestoreCall !== 'function') {
                throw new Error('Restore helper not available');
            }
            const result = await apiRestoreCall('/automation/restore-now', restorePayload);

            showStatus(`Restore completed successfully!`, 'success');
        }
        
        hideDatabaseActionModal();
    } catch (error) {
        setDatabaseActionStatus(`${actionType === 'backup' ? 'Backup' : 'Restore'} failed: ${error.message}`, 'error', true);
    }
}

// Initialize event listeners for databases tab
/**
 * Initialize event handlers for the databases tab (form + modal).
 * @returns {void}
 */
function initDatabasesTab() {
    // Database form
    document.getElementById('add-database-btn').addEventListener('click', () => showDatabaseForm());
    document.getElementById('test-database-connection-btn').addEventListener('click', testDatabaseConnection);
    document.getElementById('save-database-btn').addEventListener('click', saveDatabase);
    document.getElementById('cancel-database-btn').addEventListener('click', hideDatabaseForm);

    const closeBtn = document.getElementById('database-form-close-btn');
    if (closeBtn) {
        closeBtn.addEventListener('click', hideDatabaseForm);
    }

    const dbTypeEl = document.getElementById('database-db-type');
    if (dbTypeEl) {
        dbTypeEl.addEventListener('change', updateDatabaseFormUX);
    }

    window.addEventListener('appVersionLoaded', () => {
        updateDatabaseFormUX();
    });

    // Backup/Restore modal
    const actionDestSelect = document.getElementById('database-action-destination');
    if (actionDestSelect) {
        actionDestSelect.addEventListener('change', handleDatabaseActionDestinationChange);
    }

    const actionBackupSelect = document.getElementById('database-action-backup-file');
    if (actionBackupSelect) {
        actionBackupSelect.addEventListener('change', updateDatabaseActionEncryptionVisibility);
    }
    
    const actionExecuteBtn = document.getElementById('database-action-execute-btn');
    if (actionExecuteBtn) {
        actionExecuteBtn.addEventListener('click', executeDatabaseAction);
    }
    
    // Close modal when clicking outside
    const actionModal = document.getElementById('database-action-modal');
    if (actionModal) {
        actionModal.addEventListener('click', (e) => {
            if (e.target.id === 'database-action-modal') {
                hideDatabaseActionModal();
            }
        });
    }

    const list = document.getElementById('databases-list');
    if (list) {
        list.addEventListener('click', (e) => {
            const btn = e.target.closest('button[data-action]');
            if (!btn) return;
            const action = btn.getAttribute('data-action');
            const id = btn.getAttribute('data-id');
            if (!id) return;

            if (action === 'db-backup') {
                showDatabaseActionModal(id, 'backup');
            } else if (action === 'db-restore') {
                showDatabaseActionModal(id, 'restore');
            } else if (action === 'db-edit') {
                editDatabase(id);
            } else if (action === 'db-delete') {
                deleteDatabase(id);
            }
        });
    }

    document.querySelectorAll('#database-action-modal .modal-close').forEach(btn => {
        btn.addEventListener('click', hideDatabaseActionModal);
    });
}

window.updateDatabaseActionEncryptionVisibility = updateDatabaseActionEncryptionVisibility;
