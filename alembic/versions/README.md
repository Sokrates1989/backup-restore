# Migration Examples

This directory contains **reference migration examples** showing common database schema changes.

## ⚠️ Important

**All migrations (001-008) run automatically as a complete demonstration!**

This template includes a **full migration chain** showing real-world schema evolution:

**Active migration chain:**
```
001 → 002 → 003 → 004 → 005 → 006 → 007 -> 008
```

All migrations run on startup, demonstrating:
- ✅ Creating tables
- ✅ Adding columns
- ✅ Removing columns
- ✅ Creating relationships (1:N and N:M)
- ✅ Migrating data

**This is intentional!** It shows you how a real application's schema evolves over time.

## Available Examples

| File | Purpose | What It Shows |
|------|---------|---------------|
| `001_initial_examples_table.py` | ✅ **ACTIVE** | Initial schema setup |
| `002_example_add_categories_table.py` | 📚 Reference | Creating a new table |
| `003_example_add_column.py` | 📚 Reference | Adding a column |
| `004_example_remove_column.py` | 📚 Reference | Removing a column (legacy_id) |
| `005_example_add_1n_relationship.py` | 📚 Reference | Creating 1:N relationship |
| `006_example_add_nm_relationship.py` | 📚 Reference | Creating N:M relationship |
| `007_example_data_migration.py` | 📚 Reference | Migrating existing data |
| `008_create_users_table.py` | 📚 Reference | Creating users table |

## How to Use These Examples

### 1. **Study the Code**

Open any example migration to see:
- How to structure the migration
- What Alembic commands to use
- How to implement upgrade/downgrade
- Best practices and comments

### 2. **Copy as Template**

When you need to create a similar migration:

```bash
# Create a new migration
docker compose exec app pdm run alembic revision -m "Your description"

# Copy relevant code from the example
# Modify for your needs
# Test it!
```

### 3. **Learn the Patterns**

Each example demonstrates a specific pattern:

**002 - New Table:**
```python
op.create_table('table_name',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(100), nullable=False),
    sa.PrimaryKeyConstraint('id')
)
```

**003 - Add Column:**
```python
op.add_column('table_name',
    sa.Column('new_column', sa.Integer(), nullable=False, server_default='0')
)
```

**004 - Remove Column:**
```python
op.drop_column('table_name', 'column_name')
```

**005 - 1:N Relationship:**
```python
op.add_column('child_table',
    sa.Column('parent_id', sa.String(), nullable=True)
)
op.create_foreign_key('fk_name', 'child_table', 'parent_table',
    ['parent_id'], ['id'], ondelete='SET NULL'
)
```

**006 - N:M Relationship:**
```python
op.create_table('association_table',
    sa.Column('table1_id', sa.String(), nullable=False),
    sa.Column('table2_id', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['table1_id'], ['table1.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['table2_id'], ['table2.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('table1_id', 'table2_id')
)
```

**007 - Data Migration:**
```python
op.execute("""
    INSERT INTO table (id, name) VALUES ('id', 'name')
    ON CONFLICT (name) DO NOTHING
""")
op.execute("""
    UPDATE table SET column = 'value' WHERE condition
""")
```

**008 - Users Table: (Authentication)**
```python
op.create_table('users',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('username', sa.String(length=255), nullable=False),
    sa.Column('first_name', sa.String(length=255), nullable=True),
    sa.Column('last_name', sa.String(length=255), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
)
op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
```

## Creating Your Own Migrations

### Auto-Generate (Recommended)

```bash
# 1. Update your model in app/models/sql/
# 2. Generate migration
docker compose exec app pdm run alembic revision --autogenerate -m "Description"

# 3. Review the generated file
# 4. Test it
docker compose exec app pdm run alembic upgrade head
```

### Manual Migration

```bash
# 1. Create empty migration
docker compose exec app pdm run alembic revision -m "Description"

# 2. Edit the file and add your changes
# 3. Test it
docker compose exec app pdm run alembic upgrade head
```

## Testing Migrations

Always test migrations before production:

```bash
# Apply migration
docker compose exec app pdm run alembic upgrade head

# Check it worked
docker compose exec app pdm run alembic current

# Test rollback
docker compose exec app pdm run alembic downgrade -1

# Re-apply
docker compose exec app pdm run alembic upgrade head
```

## Migration Naming Convention

Use descriptive names:

```bash
# Good ✅
001_initial_examples_table
002_add_categories_table
003_add_priority_column
004_add_category_relationship
005_add_tags_nm_relationship

# Bad ❌
001_migration
002_update
003_changes
```

## Common Patterns

### Adding a Required Column to Existing Table

```python
def upgrade():
    # Step 1: Add as nullable with default
    op.add_column('table', sa.Column('new_col', sa.String(), nullable=True))
    
    # Step 2: Set values for existing rows
    op.execute("UPDATE table SET new_col = 'default' WHERE new_col IS NULL")
    
    # Step 3: Make it required
    op.alter_column('table', 'new_col', nullable=False)
```

### Renaming a Column

```python
def upgrade():
    op.alter_column('table', 'old_name', new_column_name='new_name')
```

### Changing Column Type

```python
def upgrade():
    op.alter_column('table', 'column',
        type_=sa.String(length=255),
        existing_type=sa.String(length=100)
    )
```

## Best Practices

1. ✅ **Always implement downgrade()** - Allow rollback
2. ✅ **Test locally first** - Never test in production
3. ✅ **Keep migrations small** - One change per migration
4. ✅ **Use descriptive names** - Make it clear what changed
5. ✅ **Review auto-generated** - Alembic isn't perfect
6. ✅ **Backup before production** - Always have a backup
7. ✅ **Document data migrations** - Explain what data changes

## Troubleshooting

### "Target database is not up to date"

```bash
# Check current version
docker compose exec app pdm run alembic current

# Check history
docker compose exec app pdm run alembic history

# Upgrade to latest
docker compose exec app pdm run alembic upgrade head
```

### "Can't locate revision"

```bash
# Stamp the database with current version
docker compose exec app pdm run alembic stamp head
```

### "Duplicate key error"

Your migration tried to create something that already exists. Check your database state.

## Further Reading

- [Complete Migration Guide](../../docs/MIGRATION_GUIDE.md)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
