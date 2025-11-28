#!/bin/bash
#
# dev-setup.sh
#
# This script initializes Python dependency lock files (poetry.lock, pdm.lock)
# inside the Dockerized dev environment. It is idempotent and safe to re-run.
# Usage: Run inside the dev container (e.g., via docker-compose run --rm dev ./dev-setup.sh)
#
# - Generates poetry.lock and pdm.lock if missing
# - Applies configuration from environment variables
# - Prints instructions for interactive use
# - Does not start backend services automatically

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

print_color $YELLOW "[python-dependency-management] Initializing project dependency files..."

# Ensure PDM does not create a .venv in the project directory
print_color $BLUE "ðŸ”§ Configuring PDM to install packages globally in the container..."
pdm config python.use_venv false

# Apply configuration from environment variables
if [ "${USE_UV_BACKEND:-true}" = "true" ]; then
    print_color $BLUE "ðŸš€ Configuring PDM to use uv backend for faster operations..."
    pdm config use_uv true
else
    print_color $BLUE "ðŸ“¦ Using PDM's default backend..."
    pdm config use_uv false
fi

if [ "${PDM_INSTALL_CACHE:-true}" = "true" ]; then
    print_color $BLUE "ðŸ’¾ Enabling PDM install cache..."
    pdm config install.cache true
else
    pdm config install.cache false
fi

if [ "${PDM_PARALLEL_INSTALL:-true}" = "true" ]; then
    print_color $BLUE "âš¡ Enabling parallel installs..."
    pdm config install.parallel true
else
    pdm config install.parallel false
fi

# Initialize Poetry lock file if missing
if [ ! -f poetry.lock ]; then
    print_color $YELLOW "Generating poetry.lock..."
    poetry lock || print_color $YELLOW "Poetry lock failed (maybe no pyproject.toml or not a poetry project)"
else
    print_color $GREEN "poetry.lock already exists."
fi

# Initialize PDM lock file if missing
if [ ! -f pdm.lock ]; then
    print_color $YELLOW "Generating pdm.lock..."
    pdm lock || print_color $YELLOW "PDM lock failed (maybe no pyproject.toml or not a pdm project)"
else
    print_color $GREEN "pdm.lock already exists."
fi

print_color $GREEN "[python-dependency-management] Setup complete!"

print_color $YELLOW "Available tools and commands:"
print_color $YELLOW "  ðŸ“¦ PDM: pdm add <package>, pdm install, pdm remove <package>"
print_color $YELLOW "  ðŸŽ­ Poetry: poetry add <package>, poetry install, poetry remove <package>"
print_color $YELLOW "  âš¡ uv: uv add <package>, uv pip install <package>, uv run <command>"

print_color $YELLOW "Configuration applied:"
print_color $YELLOW "  ðŸš€ PDM uv backend: ${USE_UV_BACKEND:-true}"
print_color $YELLOW "  ðŸ’¾ PDM install cache: ${PDM_INSTALL_CACHE:-true}"
print_color $YELLOW "  âš¡ PDM parallel installs: ${PDM_PARALLEL_INSTALL:-true}"

print_color $BLUE "ðŸ’¡ Common PDM Commands & Use Cases:"
print_color $YELLOW ""
print_color $YELLOW "ðŸ“¦ Basic Package Management:"
print_color $YELLOW "  pdm add requests                    # Add a package"
print_color $YELLOW "  pdm add \"requests>=2.28.0\"         # Add with version constraint"
print_color $YELLOW "  pdm add pytest --dev               # Add development dependency"
print_color $YELLOW "  pdm remove requests                 # Remove a package"
print_color $YELLOW "  pdm install                         # Install all dependencies"
print_color $YELLOW "  pdm list                            # List installed packages"
print_color $YELLOW ""
print_color $YELLOW "ðŸ”„ Dependency Management:"
print_color $YELLOW "  pdm update                          # Update all dependencies"
print_color $YELLOW "  pdm update requests                 # Update specific package"
print_color $YELLOW "  pdm lock                            # Update lock file"
print_color $YELLOW "  pdm lock --check                    # Check if lock file is up-to-date"
print_color $YELLOW "  pdm sync                            # Sync environment with lock file"
print_color $YELLOW ""
print_color $YELLOW "ðŸ”§ Troubleshooting & Conflicts:"
print_color $YELLOW "  pdm lock --update-reuse             # Update lock with conflict resolution"
print_color $YELLOW "  pdm install --no-lock               # Install without updating lock file"
print_color $YELLOW "  pdm cache clear                     # Clear package cache"
print_color $YELLOW "  pdm info                            # Show project information"
print_color $YELLOW "  pdm info requests                   # Show package details"
print_color $YELLOW ""
print_color $YELLOW "ðŸ Python Version Management:"
print_color $YELLOW "  pdm python list                     # List available Python versions"
print_color $YELLOW "  pdm python install 3.12             # Install specific Python version"
print_color $YELLOW "  pdm use 3.12                        # Switch to Python 3.12"
print_color $YELLOW ""
print_color $YELLOW "ðŸš€ Running Scripts:"
print_color $YELLOW "  pdm run python script.py            # Run script with project dependencies"
print_color $YELLOW "  pdm run pytest                      # Run tests"
print_color $YELLOW "  pdm run --list                      # List available scripts"
print_color $YELLOW ""
print_color $YELLOW "ðŸ” Debugging Dependency Issues:"
print_color $YELLOW "  pdm show --graph                    # Show dependency tree"
print_color $YELLOW "  pdm show --reverse requests         # Show what depends on requests"
print_color $YELLOW "  pdm export -f requirements          # Export to requirements.txt format"
print_color $YELLOW "  pdm import requirements.txt         # Import from requirements.txt"
print_color $YELLOW ""
print_color $YELLOW "âš¡ Quick Fixes for Common Issues:"
print_color $YELLOW "  # Dependency conflict resolution:"
print_color $YELLOW "  pdm lock --update-reuse --resolution=highest"
print_color $YELLOW ""
print_color $YELLOW "  # Force reinstall all packages:"
print_color $YELLOW "  pdm sync --reinstall"
print_color $YELLOW ""
print_color $YELLOW "  # Install from fresh lock file:"
print_color $YELLOW "  rm pdm.lock && pdm lock && pdm install"
print_color $YELLOW ""

print_color $YELLOW "To start an interactive shell, run:"
print_color $YELLOW "  docker-compose run --rm dev bash"

print_color $YELLOW "To start the backend (if using docker-compose in project root):"
print_color $YELLOW "  docker-compose up --build" 
