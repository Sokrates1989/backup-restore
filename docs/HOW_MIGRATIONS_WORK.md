# How Alembic Migrations Work

## Quick Answer

**Q: How is defined what migrations will be run?**  
**A:** Alembic tracks migrations in a database table called `alembic_version` and runs migrations in order based on their revision chain.

**Q: Will automatically all migrations be attempted in the directory?**  
**A:** No! Only migrations that haven't been run yet (based on the revision chain) will be executed.

---

## How It Works

### 1. **Migration Tracking**

Alembic creates a table in your database:

```sql
CREATE TABLE alembic_version (
    version_num VARCHAR(32) PRIMARY KEY
);
```

This table stores the **current migration version**. Example:

```
version_num
-----------
abc123def456
```

### 2. **Revision Chain**

Each migration file has:

```python
revision = 'abc123'      # This migration's ID
down_revision = 'xyz789' # Previous migration's ID
```

This creates a **chain**:

```
001_initial
    ↓
002_add_categories
    ↓
003_add_priority
    ↓
004_remove_description
```

### 3. **What Gets Run**

When you run `alembic upgrade head`:

1. Alembic checks `alembic_version` table → Current: `002_add_categories`
2. Looks at migration files → Finds chain goes to `004_remove_description`
3. Runs only the **missing migrations**:
   - ✅ `003_add_priority`
   - ✅ `004_remove_description`
4. Updates `alembic_version` → New: `004_remove_description`

**Result:** Only new migrations run, never re-runs old ones!

---

## Configuration Files

### `alembic.ini`

Main configuration file:

```ini
[alembic]
# Where migration files are stored
script_location = alembic

# Database URL (overridden by env.py)
sqlalchemy.url = driver://user:pass@localhost/dbname
```

### `alembic/env.py`

**This is the key file!** It defines:

1. **Which models to track:**

```python
# Import your models' Base
from models.sql.example import Base

# Tell Alembic about your models
target_metadata = Base.metadata
```

2. **Database connection:**

```python
def get_url():
    """Get database URL from environment variables."""
    return os.getenv("DATABASE_URL")
```

3. **How to run migrations:**

```python
def run_migrations_online():
    # Connect to database
    # Run pending migrations
    # Update alembic_version table
```

---

## Migration File Structure

### Location

```
alembic/
└── versions/
    ├── 001_initial_examples_table.py
    ├── 002_add_categories_table.py
    └── 003_add_priority_column.py
```

### File Format

```python
"""Description of what this migration does

Revision ID: abc123
Revises: xyz789  # ← Links to previous migration
Create Date: 2024-01-01 12:00:00
"""
from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision = 'abc123'      # This migration's ID
down_revision = 'xyz789' # Previous migration's ID

def upgrade():
    """Apply changes."""
    op.create_table('new_table', ...)

def downgrade():
    """Revert changes."""
    op.drop_table('new_table')
```

---

## Automatic vs Manual Execution

### In This Template

Migrations run **automatically** on startup with detailed status reporting:

```python
# app/main.py
@app.on_event("startup")
async def startup_event():
    # ... database initialization ...
    
    # Run migrations automatically
    from backend.database.migrations import run_migrations
    run_migrations()
```

**What you'll see:**

```
🔄 Checking migration status...
📍 Current database version: 001_initial_...
🔄 Running 2 pending migration(s)...
   ⏩ 002_add_categ - Add categories table
   ⏩ 003_add_prio - Add priority column to examples
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 001 -> 002, Add categories table
INFO  [alembic.runtime.migration] Running upgrade 002 -> 003, Add priority column
✅ Migrations completed successfully!
📍 New database version: 003_add_prio...
```

**If database is up to date:**

```
🔄 Checking migration status...
📍 Current database version: 003_add_prio...
✅ Database is up to date - no migrations needed
```

**First time (no migrations yet):**

```
🔄 Checking migration status...
📍 Database not initialized (no migrations applied yet)
🔄 Running 3 pending migration(s)...
   ⏩ 001_initial_ - Initial examples table
   ⏩ 002_add_categ - Add categories table
   ⏩ 003_add_prio - Add priority column to examples
...
✅ Migrations completed successfully!
📍 New database version: 003_add_prio...
```

### Manual Execution

You can also run migrations manually:

```bash
# Apply all pending migrations
docker compose exec app pdm run alembic upgrade head

# Rollback one migration
docker compose exec app pdm run alembic downgrade -1

# Check current version
docker compose exec app pdm run alembic current

# View history
docker compose exec app pdm run alembic history
```

---

## Which Migrations Run?

### Example Scenario

**Database state:**
```
alembic_version: 002_add_categories
```

**Migration files:**
```
001_initial_examples_table.py      (revision='001', down_revision=None)
002_add_categories_table.py        (revision='002', down_revision='001')
003_add_priority_column.py         (revision='003', down_revision='002')
004_remove_description.py          (revision='004', down_revision='003')
002_example_add_categories.py      (revision='002_example', down_revision='001')  ← Not in chain!
```

**When you run `alembic upgrade head`:**

1. ✅ Runs `003_add_priority_column.py`
2. ✅ Runs `004_remove_description.py`
3. ❌ Skips `002_example_add_categories.py` (not in the active chain)

**Why?** Alembic follows the revision chain from current version to "head":
```
002 → 003 → 004
```

The `002_example` file has `down_revision='001'`, which would create a **branch**:
```
001 → 002 → 003 → 004  (main chain)
 └─→ 002_example        (orphan branch)
```

Alembic only follows the **main chain** unless you explicitly specify branches.

---

## Important Files

### 1. `alembic/env.py`

**Purpose:** Tells Alembic which models to track

**Key line:**
```python
from models.sql.example import Base
target_metadata = Base.metadata
```

**What this does:**
- Imports your SQLAlchemy models
- Gives Alembic access to table definitions
- Allows auto-generation of migrations

**If you add new models:**
```python
# Import ALL your models so Alembic can see them
from models.sql.example import Base
from models.sql.category import Category  # New model
from models.sql.tag import Tag            # Another new model

# Base.metadata now includes all tables
target_metadata = Base.metadata
```

### 2. `alembic/versions/` Directory

**Purpose:** Stores all migration files

**Naming convention:**
```
{revision_id}_{description}.py
```

Examples:
```
001_initial_examples_table.py
002_add_categories_table.py
003_add_priority_column.py
```

### 3. `alembic_version` Table

**Purpose:** Tracks current migration version in database

**Structure:**
```sql
CREATE TABLE alembic_version (
    version_num VARCHAR(32) PRIMARY KEY
);
```

**Example data:**
```
| version_num  |
|--------------|
| 003_add_pri  |
```

This tells Alembic: "Database is at version 003_add_pri"

---

## Common Scenarios

### Scenario 1: Fresh Database

**State:** No `alembic_version` table exists

**Action:** `alembic upgrade head`

**Result:**
1. Creates `alembic_version` table
2. Runs ALL migrations in order
3. Sets version to latest

### Scenario 2: Up-to-Date Database

**State:** `alembic_version` = latest migration

**Action:** `alembic upgrade head`

**Result:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

Nothing happens - already up to date!

### Scenario 3: Behind by 2 Migrations

**State:** `alembic_version` = `002`

**Files:** `001`, `002`, `003`, `004`

**Action:** `alembic upgrade head`

**Result:**
1. Runs `003`
2. Runs `004`
3. Updates version to `004`

### Scenario 4: Adding a New Migration

**State:** `alembic_version` = `003`

**Action:**
```bash
# 1. Update your model
# 2. Generate migration
alembic revision --autogenerate -m "Add tags table"
```

**Result:**
- Creates `004_add_tags_table.py`
- Sets `down_revision = '003'`
- Next startup will run this migration

---

## Troubleshooting

### Error: "No module named 'models.example'"

**Cause:** `alembic/env.py` imports from wrong path

**Fix:**
```python
# OLD (wrong)
from models.example import Base

# NEW (correct)
from models.sql.example import Base
```

### Error: "Target database is not up to date"

**Cause:** Migration files exist that aren't in the database

**Fix:**
```bash
# Apply pending migrations
alembic upgrade head
```

### Error: "Can't locate revision"

**Cause:** `alembic_version` table has invalid revision ID

**Fix:**
```bash
# Stamp database with correct version
alembic stamp head
```

### Multiple Heads (Branches)

**Cause:** Two migrations have the same `down_revision`

**Example:**
```
001 → 002 → 003
 └─→ 002_alt
```

**Fix:** Merge the branches:
```bash
alembic merge -m "Merge branches" 002 002_alt
```

---

## Best Practices

### 1. **Always Import All Models**

```python
# alembic/env.py
from models.sql.example import Base
from models.sql.category import Category
from models.sql.tag import Tag
# Import ALL models so Alembic sees all tables
```

### 2. **Review Auto-Generated Migrations**

```bash
# Generate migration
alembic revision --autogenerate -m "Add field"

# ALWAYS review the generated file!
cat alembic/versions/xxx_add_field.py
```

### 3. **Test Migrations Locally**

```bash
# Test upgrade
alembic upgrade head

# Test downgrade
alembic downgrade -1

# Test upgrade again
alembic upgrade head
```

### 4. **Keep Migrations Small**

```bash
# Good ✅
alembic revision -m "Add priority column"
alembic revision -m "Add category table"

# Bad ❌
alembic revision -m "Add priority, category, tags, and relationships"
```

### 5. **Never Edit Applied Migrations**

Once a migration has been applied to production, **never edit it**!

Instead, create a new migration to fix issues.

---

## Summary

✅ **Alembic tracks** migrations in `alembic_version` table  
✅ **Follows revision chain** from current to "head"  
✅ **Only runs new migrations** - never re-runs old ones  
✅ **Configured in** `alembic/env.py` and `alembic.ini`  
✅ **Migrations stored in** `alembic/versions/`  
✅ **Auto-runs on startup** in this template  

**Key file to understand:** `alembic/env.py` - this tells Alembic which models to track!

For more details, see:
- [Migration Guide](MIGRATION_GUIDE.md) - How to create migrations
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
