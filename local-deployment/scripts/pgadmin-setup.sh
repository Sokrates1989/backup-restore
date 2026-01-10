#!/bin/sh

# Wait for pgAdmin to be ready
echo "Waiting for pgAdmin to start..."
sleep 10

# Create the test PostgreSQL server connection
echo "Creating test PostgreSQL server connection..."

# Use pgAdmin's CLI to add the server
# This creates a server connection for the test PostgreSQL database
python3 - << 'EOF'
import json
import os
import time
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Wait a bit more for PostgreSQL to be fully ready
time.sleep(5)

# Configuration
PGADMIN_EMAIL = os.environ.get('PGADMIN_EMAIL', 'admin@local.dev')
PGADMIN_PASSWORD = os.environ.get('PGADMIN_PASSWORD', 'admin')
TEST_POSTGRES_HOST = 'test-postgres'
TEST_POSTGRES_PORT = 5432
TEST_POSTGRES_DB = os.environ.get('TEST_POSTGRES_DB', 'testdb')
TEST_POSTGRES_USER = os.environ.get('TEST_POSTGRES_USER', 'testuser')
TEST_POSTGRES_PASSWORD = os.environ.get('TEST_POSTGRES_PASSWORD', 'testpass')

# Create the database if it doesn't exist
try:
    # Connect using the configured test PostgreSQL credentials
    conn = psycopg2.connect(
        host=TEST_POSTGRES_HOST,
        port=TEST_POSTGRES_PORT,
        user=TEST_POSTGRES_USER,
        password=TEST_POSTGRES_PASSWORD,
        database=TEST_POSTGRES_DB  # Connect to the test database directly
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    print(f"Connected to PostgreSQL as {TEST_POSTGRES_USER} user")
    
    # Test the connection
    cursor.execute("SELECT 1")
    print(f"Database {TEST_POSTGRES_DB} is accessible")
    
    conn.close()
    print(f"Database '{TEST_POSTGRES_DB}' and user '{TEST_POSTGRES_USER}' verified successfully")
    
except Exception as e:
    print(f"Database connection error: {e}")
    print("Database setup will continue, but you may need to configure the connection manually in pgAdmin")

# Create pgAdmin server configuration
server_config = {
    "Name": "Test PostgreSQL",
    "Group": "Test Databases",
    "Host": TEST_POSTGRES_HOST,
    "Port": TEST_POSTGRES_PORT,
    "MaintenanceDB": TEST_POSTGRES_DB,  # Use the test database as maintenance DB
    "Username": TEST_POSTGRES_USER,
    "Password": TEST_POSTGRES_PASSWORD,
    "SSLMode": "prefer",
    "ConnectionParameters": {
        "connect_timeout": "10"
    }
}

# Write the server configuration to pgAdmin's expected location
servers_dir = f"/var/lib/pgadmin/servers/{PGADMIN_EMAIL}"
os.makedirs(servers_dir, exist_ok=True)

server_file = os.path.join(servers_dir, f"{server_config['Name']}.json")
with open(server_file, 'w') as f:
    json.dump(server_config, f, indent=2)

print(f"pgAdmin server configuration created at {server_file}")
EOF

echo "pgAdmin setup completed!"
