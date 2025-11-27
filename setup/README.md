# Setup Directory

This directory contains files needed for **initial project setup**.

## Files

- **`setup.sh`** - Interactive setup script that configures your project
- **`docker-compose.setup.yml`** - Docker Compose file for running setup in a container
- **`.env.template`** - Template for environment variables

## Usage

### Automatic Setup (via quick-start)

The easiest way to run setup is through the quick-start scripts:

```bash
# Linux/Mac
./quick-start.sh

# Windows
.\quick-start.ps1
```

These scripts will automatically detect if setup is needed and prompt you to run it.

### Manual Setup

If you want to run setup manually:

```bash
# Linux/Mac
docker compose -f setup/docker-compose.setup.yml run --rm setup

# Windows
docker compose -f setup/docker-compose.setup.yml run --rm setup
```

Or run the script directly (Linux/Mac only):

```bash
chmod +x setup/setup.sh
./setup/setup.sh
```

## What Setup Does

The setup script helps you configure:

1. **Docker Image** - Name and version for production builds
2. **Python Version** - Which Python version to use
3. **Database Type** - PostgreSQL or Neo4j
4. **Database Mode** - Local (Docker) or External
5. **Database Credentials** - Username, password, ports
6. **API Configuration** - Port and debug settings

## After Setup

Once setup is complete:

1. A `.env` file will be created in the project root
2. A `.setup-complete` marker file will be created
3. You can start the application using the quick-start scripts

## Re-running Setup

If you need to reconfigure your project:

```bash
rm .setup-complete
./quick-start.sh  # or quick-start.ps1
```

The setup script will detect that setup was already run and ask if you want to reconfigure.
