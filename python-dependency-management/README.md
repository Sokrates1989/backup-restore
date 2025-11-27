# 🐳 Docker-based Python Dependency Management for Teams

A modern, Docker-based system for Python dependency management that eliminates the need for local installations of Python, pip, PDM, and Poetry.

## 🎯 Main Benefits

**No local installation required anymore:**
- ✅ No Python, pip, PDM, Poetry, or pipx needed on local development machines
- ✅ Only Docker required - unified development environment for all team members
- ✅ Consistent Python 3.13 environment regardless of operating system
- ✅ Seamless transition: Package Management → Backend start with `docker-compose up`

## 🚀 Quick Start

### 1. One-time Setup
```bash
# From the project root directory:
./manage-python-project-dependencies.sh
```

The script automatically performs the following steps:
- Creates `config.env` from `config.env.example` (if not present)
- Shows current configuration
- Builds Docker image with Python 3.13 + PDM + Poetry + uv
- Generates/updates `pdm.lock` and `poetry.lock`
- Starts interactive shell with all tools

### 2. Manage Dependencies
```bash
# In the container:
pdm add requests fastapi        # Add packages
pdm add pytest --dev          # Development Dependencies
pdm remove old-package        # Remove packages
pdm list                       # Show installed packages
pdm update                     # Update all dependencies
```

### 3. Start Backend
```bash
# Exit container:
exit

# Start backend with updated dependencies:
docker-compose up --build
```

## 🛠️ Technical Features

### **Modern Tools Integrated:**
- **PDM** with **uv backend** for lightning-fast dependency resolution
- **Poetry** available as alternative
- **uv** for ultra-fast package installation
- All tools installed isolated via **pipx**

### **Automated Configuration:**
- `config.env` for team-wide settings
- PDM uses uv backend by default (configurable)
- Parallel installation and caching enabled
- All changes persistent in project files

## 📁 Directory Structure

```
python-dependency-management/
├── Dockerfile              # Python 3.13 + PDM + Poetry + uv
├── docker-compose.yml      # Service definition
├── dev-setup.sh           # Initialization + configuration
├── config.env.example     # Configuration template
├── config.env             # Local configuration (gitignored)
└── README.md              # This documentation
```

## ⚙️ Configuration

### **config.env Options:**
```bash
# Use uv as PDM backend (recommended)
USE_UV_BACKEND=true

# Enable PDM install cache
PDM_INSTALL_CACHE=true

# Enable parallel installation
PDM_PARALLEL_INSTALL=true

# Python version (must match Dockerfile)
PYTHON_VERSION=3.13
```

## 💡 Common PDM Commands

### **📦 Basic Package Management:**
```bash
pdm add requests                    # Add package
pdm add "requests>=2.28.0"         # With version constraint
pdm add pytest --dev               # Development dependency
pdm remove requests                 # Remove package
pdm install                         # Install all dependencies
pdm list                            # Show installed packages
```

### **🔄 Dependency Management:**
```bash
pdm update                          # Update all dependencies
pdm update requests                 # Update specific package
pdm lock                            # Update lock file
pdm lock --check                    # Check lock file for updates
pdm sync                            # Sync environment with lock file
```

### **🔧 Troubleshooting & Conflicts:**
```bash
pdm lock --update-reuse             # Lock update with conflict resolution
pdm install --no-lock               # Install without lock update
pdm cache clear                     # Clear package cache
pdm info                            # Show project information
pdm info requests                   # Show package details
```

### **🐍 Python Version Management:**
```bash
pdm python list                     # List available Python versions
pdm python install 3.12             # Install specific Python version
pdm use 3.12                        # Switch to Python 3.12
```

### **🚀 Running Scripts:**
```bash
pdm run python script.py            # Run script with project dependencies
pdm run pytest                      # Run tests
pdm run --list                      # List available scripts
```

### **🔍 Debugging Dependency Issues:**
```bash
pdm show --graph                    # Show dependency tree
pdm show --reverse requests         # Show what depends on requests
pdm export -f requirements          # Export to requirements.txt format
pdm import requirements.txt         # Import from requirements.txt
```

### **⚡ Quick Fixes for Common Issues:**
```bash
# Dependency conflict resolution:
pdm lock --update-reuse --resolution=highest

# Reinstall all packages:
pdm sync --reinstall

# Create fresh lock file:
rm pdm.lock && pdm lock && pdm install
```

## 👥 Benefits for Teams

### **Consistency:**
- Identical Python environment for all developers
- No "works on my machine" problems
- Unified tool versions (PDM, Poetry, uv)

### **Onboarding:**
- New team members only need Docker
- One command for complete setup
- Integrated documentation and help

### **Maintenance:**
- Central configuration in `config.env.example`
- Easy updates through Docker image rebuild
- No conflicts with local Python installations

## 🔧 Workflow for Developers

### **Typical Development Workflow:**
1. **Manage dependencies:** `./manage-python-project-dependencies.sh`
2. **Add/remove packages** in interactive container
3. **Exit container:** `exit`
4. **Test backend:** `docker-compose up --build`
5. **Deployment:** Dockerfile uses PDM for production environment

### **Files are automatically updated:**
- `pyproject.toml` - Dependency definitions
- `pdm.lock` - Exact versions for reproducibility
- `poetry.lock` - If Poetry is used in parallel

## 🚨 Troubleshooting

### **Container won't start:**
```bash
# Rebuild Docker image:
cd python-dependency-management
docker-compose build --no-cache
```

### **Change configuration:**
```bash
# Edit config.env:
nano python-dependency-management/config.env

# Run script again:
./manage-python-project-dependencies.sh
```

### **PDM command not found:**
```bash
# Check if uv backend is enabled:
pdm config use_uv

# Debug PATH issues:
echo $PATH
which pdm
```

## 🎉 Conclusion

**One command replaces complete local Python infrastructure:**
- No manual setup of Python environments
- Modern, fast tools (PDM + uv) out-of-the-box
- Seamless integration into Docker-based development
- Team-wide consistency and easy onboarding

**Perfect for modern Python teams that rely on Docker!** 🐳

---

## 📝 Additional Information

- **Main project README:** `../README.md`
- **PDM Documentation:** https://pdm.fming.dev/
- **uv Documentation:** https://docs.astral.sh/uv/
- **Docker Compose Reference:** https://docs.docker.com/compose/ 