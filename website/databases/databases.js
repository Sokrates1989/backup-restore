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
    updateDatabaseFormUX();
}

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

function hideDatabaseForm() {
    document.getElementById('database-form').classList.add('hidden');
    if (typeof clearStatusMessages === 'function') {
        clearStatusMessages();
    }
}

function editDatabase(id) {
    const database = databases.find(d => d.id === id);
    if (database) showDatabaseForm(database);
}

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

async function deleteDatabase(id) {
    if (!confirm('Are you sure you want to delete this database?')) return;
    
    try {
        await apiCall(`/automation/targets/${id}`, 'DELETE');
        showStatus('Database deleted');
        await loadDatabases();
        updateScheduleSelects();
    } catch (error) {
        showStatus(`Failed to delete database: ${error.message}`, 'error', true);
    }
}

// Initialize event listeners for databases tab
function initDatabasesTab() {
    // Database form
    document.getElementById('add-database-btn').addEventListener('click', () => showDatabaseForm());
    document.getElementById('test-database-connection-btn').addEventListener('click', testDatabaseConnection);
    document.getElementById('save-database-btn').addEventListener('click', saveDatabase);
    document.getElementById('cancel-database-btn').addEventListener('click', hideDatabaseForm);

    const dbTypeEl = document.getElementById('database-db-type');
    if (dbTypeEl) {
        dbTypeEl.addEventListener('change', updateDatabaseFormUX);
    }

    window.addEventListener('appVersionLoaded', () => {
        updateDatabaseFormUX();
    });
}
