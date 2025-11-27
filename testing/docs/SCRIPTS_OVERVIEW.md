# Testing Scripts Overview

Complete guide to all available testing scripts for Windows, Linux, and Mac.

## 📋 Quick Reference

| Script | Windows | Linux/Mac | Purpose |
|--------|---------|-----------|---------|
| **Quick Test** | `quick-test.ps1` | `quick-test.sh` | Interactive testing menu |
| **Start PostgreSQL** | `start-postgres.bat` | `start-postgres.sh` | Start with PostgreSQL |
| **Start Neo4j** | `start-neo4j.bat` | `start-neo4j.sh` | Start with Neo4j |
| **Test API** | `test-api.bat` | `test-api.sh` | Test API endpoints |

## 🚀 Quick Test Scripts (Recommended)

### Interactive Testing Interface

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

### Features

- ✅ **Docker Status Check** - Verifies Docker is running
- ✅ **Database Selection** - Choose PostgreSQL or Neo4j if no `.env` exists
- ✅ **Configuration Detection** - Automatically reads your `.env` settings
- ✅ **Multiple Actions** - Start, test, or both

### Interactive Menu

```
What would you like to do?
1) Start services and run tests      ← Full workflow
2) Just start services                ← For manual testing
3) Just run tests                     ← If already running
4) Stop services                      ← Clean shutdown
```

### Example Usage

**Option 1: Full Workflow**
```bash
./quick-test.sh
# Choose option 1
# → Starts containers
# → Waits for services
# → Runs all tests
# → Shows results
```

**Option 2: Development Mode**
```bash
./quick-test.sh
# Choose option 2
# → Starts containers with logs
# → Keep terminal open to see live logs
# → Ctrl+C to stop
```

**Option 3: Quick Test**
```bash
./quick-test.sh
# Choose option 3
# → Runs tests against running services
# → Fast feedback loop
```

**Option 4: Cleanup**
```bash
./quick-test.sh
# Choose option 4
# → Stops all containers
# → Cleans up resources
```

## 📦 Individual Start Scripts

### Start with PostgreSQL

**Windows:**
```bash
cd testing/scripts
start-postgres.bat
```

**Linux/Mac:**
```bash
cd testing/scripts
./start-postgres.sh
```

**What it does:**
1. Changes to project root directory
2. Copies `.env.postgres.example` to `.env` (if needed)
3. Runs `docker compose -f docker-compose.postgres.yml up --build`
4. Starts PostgreSQL 16, Redis 7, and the API

**Access Points:**
- API: http://localhost:8000/docs
- PostgreSQL: localhost:5432 (postgres/postgres)
- Data: `.docker/postgres-data/`

### Start with Neo4j

**Windows:**
```bash
cd testing/scripts
start-neo4j.bat
```

**Linux/Mac:**
```bash
cd testing/scripts
./start-neo4j.sh
```

**What it does:**
1. Changes to project root directory
2. Copies `.env.neo4j.example` to `.env` (if needed)
3. Runs `docker compose -f docker-compose.neo4j.yml up --build`
4. Starts Neo4j 5, Redis 7, and the API

**Access Points:**
- API: http://localhost:8000/docs
- Neo4j Browser: http://localhost:7474 (neo4j/password)
- Bolt: bolt://localhost:7687
- Data: `.docker/neo4j-data/`
- Logs: `.docker/neo4j-logs/`

## 🧪 Test Scripts

### Test API Endpoints

**Windows:**
```bash
cd testing/scripts
test-api.bat
```

**Linux/Mac:**
```bash
cd testing/scripts
./test-api.sh
```

**What it tests:**
1. **Database Connection** - `GET /test/db-test`
   - Verifies database connectivity
   - Shows connection details
   - Tests basic query

2. **Database Info** - `GET /test/db-info`
   - Returns database type
   - Shows configuration
   - Displays connection URL

3. **Sample Query** - `GET /test/sample-query`
   - Executes sample database query
   - Returns results
   - Verifies query execution

4. **File Count** - `GET /files/file-count`
   - Counts files in mounted directory
   - Tests file operations
   - Shows file system access

**Example Output:**
```
========================================
Testing API Endpoints
========================================

1. Testing database connection...
GET http://localhost:8000/test/db-test
{
  "status": "success",
  "connection": {
    "status": "success",
    "message": "SQL database connection successful"
  }
}

2. Testing database info...
...
```

## 🔄 Typical Workflows

### Workflow 1: Quick Test (Fastest)

```bash
cd testing
./quick-test.sh
# Choose option 1
# ✅ Everything automated
```

### Workflow 2: Development

```bash
cd testing/scripts
cd testing
./start-postgres.sh
# Keep terminal open for logs
# In another terminal:
./test-api.sh
# Make changes, test again
```

### Workflow 3: Manual Testing

```bash
cd testing
./quick-test.sh
# Choose: 2) Just start services
# Open browser: http://localhost:8000/docs
# Test manually in Swagger UI
```

### Workflow 4: CI/CD

```bash
cd testing
./quick-test.sh <<EOF
1
1
EOF
# Automated: starts services and runs tests
# Exit code 0 = success, non-zero = failure
```

## 🎯 Platform-Specific Notes

### Windows

**PowerShell Scripts (`.ps1`):**
- Native Windows experience
- Colored output
- No bash required
- Run with: `.\script.ps1`

**Batch Scripts (`.bat`):**
- Classic Windows scripts
- Simple and reliable
- Run with: `script.bat`

**Requirements:**
- Docker Desktop for Windows
- PowerShell 5.1+ (built into Windows)

### Linux/Mac

**Shell Scripts (`.sh`):**
- Native Unix experience
- POSIX compatible
- Run with: `./script.sh`
- Make executable: `chmod +x script.sh`

**Requirements:**
- Docker Engine (Linux) or Docker Desktop (Mac)
- Bash shell (standard on both)

## 📊 Script Comparison

### Quick Test vs Individual Scripts

| Feature | Quick Test | Individual Scripts |
|---------|-----------|-------------------|
| **Interactive** | ✅ Menu-driven | ❌ Direct execution |
| **Flexibility** | ✅ Multiple options | ⚠️ Single purpose |
| **Docker Check** | ✅ Built-in | ❌ Manual |
| **Config Help** | ✅ Guides setup | ⚠️ Assumes configured |
| **Best For** | First-time users | Experienced users |

### When to Use Each

**Use Quick Test (`quick-test.sh/.ps1`) when:**
- First time testing
- Want guided experience
- Need to choose database
- Want multiple options

**Use Individual Scripts when:**
- Know exactly what you want
- Scripting/automation
- Quick repeated tests
- CI/CD pipelines

## 🛠️ Troubleshooting

### Scripts Won't Run (Linux/Mac)

**Problem:** `Permission denied`

**Solution:**
```bash
chmod +x testing/*.sh
```

### Docker Not Running

**Problem:** `Docker daemon is not running`

**Solution:**
- Windows: Start Docker Desktop
- Linux: `sudo systemctl start docker`
- Mac: Start Docker Desktop

### Port Already in Use

**Problem:** `Port 8000 is already allocated`

**Solution:**
```bash
# Stop existing containers
docker compose down

# Or change port in .env
PORT=8001
```

### Tests Fail Immediately

**Problem:** Services not ready yet

**Solution:**
```bash
# Wait longer before testing
sleep 15
./test-api.sh
```

## 📚 Additional Resources

- **Main README**: `../README.md`
- **Docker Setup**: `../docs/DOCKER_SETUP.md`
- **Database Modes**: `../docs/DATABASE_MODES.md`
- **Testing Guide**: `TESTING_GUIDE.md`
- **How to Add Endpoints**: `../docs/HOW_TO_ADD_ENDPOINT.md`

## 🎉 Summary

**Simplest Way to Test:**
```bash
cd testing
./quick-test.sh  # or .\quick-test.ps1 on Windows
# Choose option 1
```

**That's it!** The script handles everything else. 🚀
