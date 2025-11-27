# Testing Directory

Organized testing scripts and documentation for the python-api-template project.

## 📁 Directory Structure

```
testing/
├── README.md                  # This file - main entry point
├── quick-test.ps1            # Interactive test (Windows) - MAIN ENTRY
├── quick-test.sh             # Interactive test (Linux/Mac) - MAIN ENTRY
├── test-crud-example.ps1     # Test CRUD endpoints (Windows) - NEW
├── test-crud-example.sh      # Test CRUD endpoints (Linux/Mac) - NEW
├── scripts/                   # Individual test scripts
│   ├── start-postgres.bat    # Start PostgreSQL (Windows)
│   ├── start-postgres.sh     # Start PostgreSQL (Linux/Mac)
│   ├── start-neo4j.bat       # Start Neo4j (Windows)
│   ├── start-neo4j.sh        # Start Neo4j (Linux/Mac)
│   ├── test-api.bat          # Test endpoints (Windows)
│   └── test-api.sh           # Test endpoints (Linux/Mac)
└── docs/                      # Documentation
    ├── TESTING_GUIDE.md      # Detailed testing procedures
    └── SCRIPTS_OVERVIEW.md   # Complete script reference
```

## 🚀 Quick Start

### Interactive Testing (Recommended)

**Windows PowerShell:**
```powershell
cd testing
.\quick-test.ps1
```

**Linux/Mac:**
```bash
cd testing
./quick-test.sh
```

This will give you an interactive menu to:
1. Start services and run tests (full workflow)
2. Just start services (for manual testing)
3. Just run tests (if services already running)
4. Stop services

### Direct Scripts

**Start with PostgreSQL:**
```bash
# Windows
cd testing/scripts
start-postgres.bat

# Linux/Mac
cd testing/scripts
./start-postgres.sh
```

**Start with Neo4j:**
```bash
# Windows
cd testing/scripts
start-neo4j.bat

# Linux/Mac
cd testing/scripts
./start-neo4j.sh
```

**Test API Endpoints:**
```bash
# Windows
cd testing/scripts
test-api.bat

# Linux/Mac
cd testing/scripts
./test-api.sh
```

**Test CRUD Example:**
```bash
# Windows
cd testing
.\test-crud-example.ps1

# Linux/Mac
cd testing
./test-crud-example.sh
```

## 📚 Documentation

- **[Testing Guide](docs/TESTING_GUIDE.md)** - Detailed testing procedures
- **[Scripts Overview](docs/SCRIPTS_OVERVIEW.md)** - Complete script reference

## 🎯 Common Workflows

### First Time Testing

```bash
cd testing
./quick-test.sh
# Choose option 1: Start services and run tests
```

### Development Loop

```bash
# Terminal 1: Start services
cd testing/scripts
./start-postgres.sh

# Terminal 2: Test repeatedly
cd testing/scripts
./test-api.sh
```

### Manual Testing

```bash
cd testing
./quick-test.sh
# Choose option 2: Just start services
# Then open: http://localhost:8000/docs
```

## 🔗 Related Documentation

- **[Main README](../README.md)** - Project overview
- **[Docker Setup](../docs/DOCKER_SETUP.md)** - Docker configuration
- **[Database Modes](../docs/DATABASE_MODES.md)** - Local vs external databases
- **[How to Add Endpoints](../docs/HOW_TO_ADD_ENDPOINT.md)** - Development guide

## 💡 Tips

- Use `quick-test.sh/.ps1` for guided testing
- Use individual scripts for automation
- All scripts automatically detect your database configuration
- Scripts handle `.env` file creation if needed

## 🆘 Need Help?

Check the documentation in the `docs/` directory:
- Read `docs/TESTING_GUIDE.md` for detailed procedures
- See `docs/SCRIPTS_OVERVIEW.md` for complete script documentation
