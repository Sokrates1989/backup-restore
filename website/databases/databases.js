/**
 * Databases Tab JavaScript
 * 
 * Handles database management for the Backup Manager.
 */

// Database Management Functions
async function loadDatabases() {
    try {
        databases = await apiCall('/automation/targets');
        renderDatabases();
    } catch (error) {
        showStatus(`Failed to load databases: ${error.message}`, 'error');
    }
}

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
                    <button class="btn btn-sm btn-secondary" onclick="editDatabase('${database.id}')">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteDatabase('${database.id}')">Delete</button>
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
}

function hideDatabaseForm() {
    document.getElementById('database-form').classList.add('hidden');
}

function editDatabase(id) {
    const database = databases.find(d => d.id === id);
    if (database) showDatabaseForm(database);
}

async function testDatabaseConnection() {
    const name = document.getElementById('database-name').value.trim();
    const db_type = document.getElementById('database-db-type').value;
    const host = document.getElementById('database-host').value.trim();
    const port = parseInt(document.getElementById('database-port').value) || null;
    const database = document.getElementById('database-database').value.trim();
    const user = document.getElementById('database-user').value.trim();
    const password = document.getElementById('database-password').value;

    if (!name || !host || !database || !user) {
        showStatus('Please fill in all required fields to test connection', 'error');
        return;
    }

    const payload = {
        name,
        db_type,
        config: { host, port, database, user },
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

async function saveDatabase() {
    const id = document.getElementById('database-id').value;
    const name = document.getElementById('database-name').value.trim();
    const db_type = document.getElementById('database-db-type').value;
    const host = document.getElementById('database-host').value.trim();
    const port = parseInt(document.getElementById('database-port').value) || null;
    const database = document.getElementById('database-database').value.trim();
    const user = document.getElementById('database-user').value.trim();
    const password = document.getElementById('database-password').value;

    if (!name) {
        showStatus('Please enter a name', 'error');
        return;
    }

    const payload = {
        name,
        db_type,
        config: { host, port, database, user },
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
        showStatus(`Failed to save database: ${error.message}`, 'error');
    }
}

async function deleteDatabase(id) {
    if (!confirm('Are you sure you want to delete this database?')) return;
    
    try {
        await apiCall(`/automation/targets/${id}`, 'DELETE');
        showStatus('Database deleted');
        await loadDatabases();
        updateScheduleSelects();
    } catch (error) {
        showStatus(`Failed to delete database: ${error.message}`, 'error');
    }
}

// Initialize event listeners for databases tab
function initDatabasesTab() {
    // Database form
    document.getElementById('add-database-btn').addEventListener('click', () => showDatabaseForm());
    document.getElementById('test-database-connection-btn').addEventListener('click', testDatabaseConnection);
    document.getElementById('save-database-btn').addEventListener('click', saveDatabase);
    document.getElementById('cancel-database-btn').addEventListener('click', hideDatabaseForm);
}
