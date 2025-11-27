# Interactive Scripts

This directory contains interactive bash scripts that run in Docker containers to provide a consistent cross-platform experience.

## 📁 Contents

- **`Dockerfile`** - Shared Alpine Linux + Docker CLI environment for all interactive scripts
- **`setup.sh`** - Initial project setup wizard
- **`docker-compose.setup.yml`** - Docker Compose configuration for setup script

## 🎯 Purpose

Interactive scripts in this directory provide guided configuration through terminal prompts. By running them in Docker containers, we ensure:

- ✅ **Cross-platform compatibility** - Works identically on Windows, Linux, and macOS
- ✅ **No local dependencies** - Only Docker required
- ✅ **Consistent environment** - Same bash version and tools everywhere
- ✅ **No redundancy** - Single Dockerfile shared by all scripts

## 🚀 Usage

### Setup Wizard

The setup wizard helps configure your project on first run:

```bash
# Automatically triggered by quick-start scripts on first run
.\quick-start.ps1  # Windows
./quick-start.sh   # Linux/Mac

# Or run manually
docker compose -f interactive-scripts/docker-compose.setup.yml run --rm setup
```

The wizard will guide you through:
1. Docker image name and version
2. Python version selection
3. Database type (PostgreSQL or Neo4j)
4. Database mode (local or external)
5. API configuration (port, debug mode)

### Build Script

The production image build script also uses this shared environment:

```bash
docker compose -f build-image/docker-compose.build.yml run --rm build-image
```

## 🔧 Adding New Interactive Scripts

To add a new interactive script:

1. Create your script in this directory (e.g., `my-script.sh`)
2. Make it executable: `chmod +x interactive-scripts/my-script.sh`
3. Create a docker-compose file:

```yaml
services:
  my-script:
    build:
      context: .
      dockerfile: interactive-scripts/Dockerfile
    container_name: my-script-runner
    stdin_open: true
    tty: true
    volumes:
      - .:/workspace
    working_dir: /workspace
    command: sh -c "chmod +x interactive-scripts/my-script.sh && interactive-scripts/my-script.sh"
```

4. Run with: `docker compose -f interactive-scripts/docker-compose.my-script.yml run --rm my-script`

## 📝 Script Guidelines

When creating interactive scripts:

- Use `#!/bin/bash` shebang
- Check for interactive terminal: `if [ -t 0 ]; then`
- Provide clear prompts and defaults
- Update `.env` file when configuration changes
- Use `sed -i` for in-place file edits
- Validate user input before applying changes
- Provide summary of changes before confirmation

## 🔍 Technical Details

### Shared Dockerfile

The shared `Dockerfile` provides:
- Alpine Linux 3.20
- Docker CLI 27
- Bash shell
- Minimal footprint

### Interactive Mode

Docker Compose configurations use:
- `stdin_open: true` - Keeps STDIN open (equivalent to `docker run -i`)
- `tty: true` - Allocates pseudo-TTY (equivalent to `docker run -t`)

This enables proper terminal interaction for prompts and user input.

### Volume Mounts

Scripts mount the project root as `/workspace`, allowing them to:
- Read configuration files
- Update `.env` and other files
- Access Docker socket (for build scripts)

## 🆘 Troubleshooting

### Prompts not appearing

If you don't see prompts, ensure you're using `docker compose run` (not `up`):

```bash
# ✅ Correct - interactive
docker compose -f interactive-scripts/docker-compose.setup.yml run --rm setup

# ❌ Wrong - not interactive
docker compose -f interactive-scripts/docker-compose.setup.yml up
```

### Permission errors

If you get permission errors when updating files:

1. Check that volumes are mounted correctly
2. Ensure the script has execute permissions
3. On Linux, check file ownership after script runs

### Script exits immediately

Check that:
1. The script has `#!/bin/bash` shebang
2. Interactive checks are in place: `if [ -t 0 ]; then`
3. The script doesn't have syntax errors: `bash -n script.sh`
