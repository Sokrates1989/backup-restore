# Database Migration Guide

This guide demonstrates **real-world database schema changes** using Alembic migrations.

## Overview

As your application evolves, you'll need to:
- ✅ Add new tables
- ✅ Add/remove columns
- ✅ Create relationships (1:n, n:m)
- ✅ Modify existing data

This guide shows you how to do all of this **safely and modularly**.

---

## Table of Contents

1. [Creating a New Table](#1-creating-a-new-table)
2. [Adding a Column to Existing Table](#2-adding-a-column)
3. [Removing an Unnecessary Column](#3-removing-a-column)
4. [Creating a 1:N Relationship](#4-creating-a-1n-relationship)
5. [Creating an N:M Relationship](#5-creating-an-nm-relationship)
6. [Best Practices](#best-practices)

---

## Prerequisites

**This guide is for SQL databases only** (PostgreSQL, MySQL, SQLite).

Neo4j is schema-free - just add properties in your Cypher queries, no migrations needed!

---

## 1. Creating a New Table

### Scenario
You need to add a `Category` table to organize your examples.

### Step 1: Create the Model

Create `app/models/sql/category.py`:

```python
"""Category model for organizing examples."""
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
import uuid

from .example import Base  # Import Base from existing model


class Category(Base):
    """
    Category model for organizing examples.
    
    Demonstrates:
    - Simple table creation
    - Basic fields
    - Timestamps
    """
    __tablename__ = "categories"
    
    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Fields
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
```

### Step 2: Generate Migration

```bash
# Inside Docker container
docker compose exec app pdm run alembic revision --autogenerate -m "Add categories table"
```

**Generated migration** (`alembic/versions/xxx_add_categories_table.py`):

```python
"""Add categories table

Revision ID: xxx
Revises: yyy
Create Date: 2024-01-01 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'xxx'
down_revision = 'yyy'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create categories table."""
    op.create_table(
        'categories',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_categories_name'), 'categories', ['name'], unique=False)


def downgrade() -> None:
    """Drop categories table."""
    op.drop_index(op.f('ix_categories_name'), table_name='categories')
    op.drop_table('categories')
```

### Step 3: Apply Migration

```bash
# Restart the app - migrations run automatically on startup
docker compose restart app

# Or run manually
docker compose exec app pdm run alembic upgrade head
```

✅ **Done!** New table created.

---

## 2. Adding a Column

### Scenario
You need to add a `priority` field to the `examples` table.

### Step 1: Update the Model

Edit `app/models/sql/example.py`:

```python
from sqlalchemy import Column, String, Text, DateTime, Integer

class Example(Base):
    __tablename__ = "examples"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # NEW: Add priority field
    priority = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### Step 2: Generate Migration

```bash
docker compose exec app pdm run alembic revision --autogenerate -m "Add priority column to examples"
```

**Generated migration**:

```python
"""Add priority column to examples

Revision ID: xxx
Revises: yyy
"""
from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    """Add priority column."""
    op.add_column('examples', sa.Column('priority', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Remove priority column."""
    op.drop_column('examples', 'priority')
```

### Step 3: Apply Migration

```bash
docker compose restart app
```

✅ **Done!** Column added with default value for existing rows.

---

## 3. Removing a Column

### Scenario
You added a `legacy_id` column during migration from an old system, but now that migration is complete and the column is no longer needed.

### Step 1: Update the Model

Edit `app/models/sql/example.py`:

```python
class Example(Base):
    __tablename__ = "examples"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False)
    # REMOVED: legacy_id = Column(String(100), nullable=True)  # No longer needed
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### Step 2: Generate Migration

```bash
docker compose exec app pdm run alembic revision --autogenerate -m "Remove legacy_id column from examples"
```

**Generated migration**:

```python
"""Remove legacy_id column from examples

Revision ID: xxx
Revises: yyy
"""
from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    """Remove legacy_id column."""
    op.drop_column('examples', 'legacy_id')


def downgrade() -> None:
    """Restore legacy_id column."""
    op.add_column('examples', sa.Column('legacy_id', sa.String(length=100), nullable=True))
```

### Step 3: Apply Migration

```bash
docker compose restart app
```

⚠️ **Warning:** Data in the `legacy_id` column will be lost!

✅ **Done!** Column removed safely without breaking existing functionality.

---

## 4. Creating a 1:N Relationship

### Scenario
Each `Example` belongs to one `Category` (1:N relationship).

### Step 1: Update the Example Model

Edit `app/models/sql/example.py`:

```python
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship

class Example(Base):
    __tablename__ = "examples"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False)
    
    # NEW: Foreign key to categories
    category_id = Column(String, ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    
    # NEW: Relationship
    category = relationship("Category", back_populates="examples")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### Step 2: Update the Category Model

Edit `app/models/sql/category.py`:

```python
from sqlalchemy.orm import relationship

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    
    # NEW: Relationship (one category has many examples)
    examples = relationship("Example", back_populates="category")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### Step 3: Generate Migration

```bash
docker compose exec app pdm run alembic revision --autogenerate -m "Add category relationship to examples"
```

**Generated migration**:

```python
"""Add category relationship to examples

Revision ID: xxx
Revises: yyy
"""
from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    """Add category_id foreign key."""
    op.add_column('examples', sa.Column('category_id', sa.String(), nullable=True))
    op.create_foreign_key(
        'fk_examples_category_id',
        'examples', 'categories',
        ['category_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index(op.f('ix_examples_category_id'), 'examples', ['category_id'], unique=False)


def downgrade() -> None:
    """Remove category_id foreign key."""
    op.drop_index(op.f('ix_examples_category_id'), table_name='examples')
    op.drop_constraint('fk_examples_category_id', 'examples', type_='foreignkey')
    op.drop_column('examples', 'category_id')
```

### Step 4: Apply Migration

```bash
docker compose restart app
```

✅ **Done!** 1:N relationship created.

### Usage Example

```python
# Create category
category = Category(name="Tutorial", description="Tutorial examples")

# Create example with category
example = Example(name="My Example", category=category)

# Query examples by category
tutorial_examples = session.query(Example).filter(Example.category_id == category.id).all()

# Access category from example
print(example.category.name)  # "Tutorial"

# Access examples from category
print(category.examples)  # [<Example>, <Example>, ...]
```

---

## 5. Creating an N:M Relationship

### Scenario
Examples can have multiple `Tag`s, and tags can be applied to multiple examples (N:M relationship).

### Step 1: Create Tag Model and Association Table

Create `app/models/sql/tag.py`:

```python
"""Tag model for N:M relationship with examples."""
from sqlalchemy import Column, String, Table, ForeignKey
from sqlalchemy.orm import relationship
import uuid

from .example import Base


# Association table for N:M relationship
example_tags = Table(
    'example_tags',
    Base.metadata,
    Column('example_id', String, ForeignKey('examples.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', String, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)


class Tag(Base):
    """
    Tag model for categorizing examples.
    
    Demonstrates N:M relationship using association table.
    """
    __tablename__ = "tags"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), nullable=False, unique=True, index=True)
    
    # N:M relationship with examples
    examples = relationship("Example", secondary=example_tags, back_populates="tags")
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name
        }
```

### Step 2: Update Example Model

Edit `app/models/sql/example.py`:

```python
from sqlalchemy.orm import relationship

class Example(Base):
    __tablename__ = "examples"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False)
    category_id = Column(String, ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    category = relationship("Category", back_populates="examples")
    
    # NEW: N:M relationship with tags
    tags = relationship("Tag", secondary="example_tags", back_populates="examples")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### Step 3: Generate Migration

```bash
docker compose exec app pdm run alembic revision --autogenerate -m "Add tags and N:M relationship with examples"
```

**Generated migration**:

```python
"""Add tags and N:M relationship with examples

Revision ID: xxx
Revises: yyy
"""
from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    """Create tags table and association table."""
    # Create tags table
    op.create_table(
        'tags',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_tags_name'), 'tags', ['name'], unique=False)
    
    # Create association table
    op.create_table(
        'example_tags',
        sa.Column('example_id', sa.String(), nullable=False),
        sa.Column('tag_id', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['example_id'], ['examples.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('example_id', 'tag_id')
    )


def downgrade() -> None:
    """Drop association table and tags table."""
    op.drop_table('example_tags')
    op.drop_index(op.f('ix_tags_name'), table_name='tags')
    op.drop_table('tags')
```

### Step 4: Apply Migration

```bash
docker compose restart app
```

✅ **Done!** N:M relationship created.

### Usage Example

```python
# Create tags
python_tag = Tag(name="python")
tutorial_tag = Tag(name="tutorial")

# Create example with tags
example = Example(name="Python Tutorial")
example.tags.append(python_tag)
example.tags.append(tutorial_tag)

# Query examples by tag
python_examples = session.query(Example).join(Example.tags).filter(Tag.name == "python").all()

# Access tags from example
print([tag.name for tag in example.tags])  # ["python", "tutorial"]

# Access examples from tag
print(python_tag.examples)  # [<Example>, <Example>, ...]
```

---

## Best Practices

### 1. **Always Review Generated Migrations**

Alembic auto-generates migrations, but **always review them**:

```bash
# Check the generated migration file
cat alembic/versions/xxx_migration_name.py
```

### 2. **Test Migrations Locally First**

```bash
# Test upgrade
docker compose exec app pdm run alembic upgrade head

# Test downgrade
docker compose exec app pdm run alembic downgrade -1

# Test upgrade again
docker compose exec app pdm run alembic upgrade head
```

### 3. **Use Descriptive Migration Names**

```bash
# Good ✅
alembic revision -m "Add priority column to examples"
alembic revision -m "Create tags table and N:M relationship"

# Bad ❌
alembic revision -m "Update database"
alembic revision -m "Changes"
```

### 4. **Handle Data Migration**

If you need to migrate existing data, create a **manual migration**:

```python
"""Migrate existing examples to default category

Revision ID: xxx
"""
from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    """Assign all examples without category to 'General' category."""
    # Create default category
    op.execute("""
        INSERT INTO categories (id, name, description, created_at)
        VALUES ('default-category-id', 'General', 'Default category', NOW())
        ON CONFLICT (name) DO NOTHING
    """)
    
    # Update examples without category
    op.execute("""
        UPDATE examples
        SET category_id = 'default-category-id'
        WHERE category_id IS NULL
    """)


def downgrade() -> None:
    """Remove category assignments."""
    op.execute("""
        UPDATE examples
        SET category_id = NULL
        WHERE category_id = 'default-category-id'
    """)
```

### 5. **Keep Migrations Small and Focused**

```bash
# Good ✅ - One change per migration
alembic revision -m "Add priority column"
alembic revision -m "Add category relationship"

# Bad ❌ - Too many changes in one migration
alembic revision -m "Add priority, remove description, add category, add tags"
```

### 6. **Backup Before Production Migrations**

```bash
# Always backup production database before running migrations!
pg_dump -U user -d database > backup_$(date +%Y%m%d_%H%M%S).sql
```

---

## Migration Commands Reference

```bash
# Generate new migration (auto-detect changes)
docker compose exec app pdm run alembic revision --autogenerate -m "Description"

# Create empty migration (for manual changes)
docker compose exec app pdm run alembic revision -m "Description"

# Apply all pending migrations
docker compose exec app pdm run alembic upgrade head

# Rollback one migration
docker compose exec app pdm run alembic downgrade -1

# Rollback to specific revision
docker compose exec app pdm run alembic downgrade <revision_id>

# Show current revision
docker compose exec app pdm run alembic current

# Show migration history
docker compose exec app pdm run alembic history

# Show SQL without executing
docker compose exec app pdm run alembic upgrade head --sql
```

---

## Complete Example: Evolution of a Schema

Here's how a real application might evolve:

```
1. Initial setup
   └─ 001_initial_examples_table.py

2. Add categories
   └─ 002_add_categories_table.py

3. Add priority to examples
   └─ 003_add_priority_column.py

4. Link examples to categories (1:N)
   └─ 004_add_category_relationship.py

5. Add tags (N:M)
   └─ 005_add_tags_and_nm_relationship.py

6. Remove unused description field
   └─ 006_remove_description_column.py

7. Migrate data to default category
   └─ 007_migrate_to_default_category.py
```

Each migration is **small, focused, and reversible**.

---

## Neo4j Alternative

**Remember:** Neo4j doesn't need migrations!

```python
# Just update your Cypher queries - that's it!

# Add a new property
query = """
CREATE (n:Example {id: $id, name: $name, priority: $priority})
RETURN n
"""

# Add a relationship
query = """
MATCH (e:Example {id: $example_id})
MATCH (c:Category {id: $category_id})
CREATE (e)-[:BELONGS_TO]->(c)
"""

# Add tags (N:M)
query = """
MATCH (e:Example {id: $example_id})
MATCH (t:Tag {name: $tag_name})
CREATE (e)-[:TAGGED_WITH]->(t)
"""
```

No migrations, no schema changes, just Cypher! 🎉

---

## Summary

✅ **Creating tables** - Add model, generate migration  
✅ **Adding columns** - Update model, generate migration  
✅ **Removing columns** - Remove from model, generate migration  
✅ **1:N relationships** - Add ForeignKey, generate migration  
✅ **N:M relationships** - Create association table, generate migration  
✅ **Data migration** - Create manual migration with SQL  

**Key Principle:** Each migration should be **small, focused, and reversible**.

For more information:
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Relationships](https://docs.sqlalchemy.org/en/20/orm/relationships.html)
