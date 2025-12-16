# Offering to Notebook Migration Guide

**Date**: December 12, 2025
**Purpose**: Migrate from offering-based document organization to notebook-based structure

---

## Overview

This guide explains how to migrate your existing offering-based documents to the new notebook-based architecture. The migration:

1. Creates notebooks for each unique offering
2. Migrates document metadata to notebook structure
3. Updates ChromaDB vector store metadata with `notebook_id`
4. Preserves all existing documents and their content

---

## What Changes

### Before Migration

**Document Organization**:
- Documents organized by `offering_id` and `offering_name`
- Metadata stored in `data/config/documents_metadata.json`
- ChromaDB nodes use `offering_id` for filtering

**Configuration Files**:
- `data/config/offerings.json` - Offering definitions
- `data/config/practices.json` - IT Practice categories
- `data/config/documents_metadata.json` - Document-to-offering mapping

### After Migration

**Document Organization**:
- Documents organized in **notebooks** (one notebook per offering)
- Metadata stored in PostgreSQL `notebooks` and `notebook_sources` tables
- ChromaDB nodes use `notebook_id` for filtering

**New Structure**:
- Each offering becomes a notebook with the same name
- Notebook description includes the original IT Practice and offering_id
- All documents associated with an offering are registered in its notebook

---

## Prerequisites

### 1. Database Setup

Ensure PostgreSQL is running and `DATABASE_URL` is configured:

```bash
# macOS
brew services start postgresql@15

# Linux
sudo systemctl start postgresql

# Verify database exists
psql -d rag_chatbot -c "SELECT 1"
```

### 2. Environment Variables

Check your `.env` file contains:

```bash
DATABASE_URL=postgresql://localhost/rag_chatbot
# or
DATABASE_URL=postgresql://username:password@localhost/rag_chatbot
```

### 3. Existing Data

Verify you have documents metadata to migrate:

```bash
cat data/config/documents_metadata.json
```

Expected structure:
```json
{
  "filename.md": {
    "it_practice": "Digital Transformation",
    "offering_name": "AI Digital Engineering",
    "offering_id": "ai-digital-engineering"
  }
}
```

---

## Migration Process

### Step 1: Dry Run (Recommended)

Run the migration in dry-run mode to preview changes without making them:

```bash
./venv/bin/python scripts/migrate_offerings_to_notebooks.py --dry-run
```

**What it does**:
- Analyzes existing document metadata
- Identifies unique offerings
- Shows what notebooks would be created
- Displays what documents would be migrated
- **DOES NOT make any changes**

**Expected Output**:
```
=== Starting Offering → Notebook Migration ===
User ID: default_user
Dry Run: True

--- Processing Offering: AI Digital Engineering ---
[DRY RUN] Would create notebook: AI Digital Engineering
  Practice: Digital Transformation
  Description: Notebook for AI Digital Engineering (Digital Transformation) - Migrated from offering ID: ai-digital-engineering
  Documents: 1
[DRY RUN] Would register 1 documents in notebook dry-run-ai-digital-engineering
[DRY RUN] Would update ChromaDB: offering_id=ai-digital-engineering → notebook_id=dry-run-ai-digital-engineering

=== Migration Summary ===
Offerings found: 6
Notebooks created: 6
Documents migrated: 6
ChromaDB nodes updated: 0
Errors: 0

✅ DRY RUN COMPLETE - No changes made
```

### Step 2: Review Migration Report

Check the generated `migration_report.json` for details:

```bash
cat migration_report.json
```

Verify:
- ✅ All offerings are identified
- ✅ Notebook names are correct
- ✅ Document counts match expectations
- ✅ No errors reported

### Step 3: Execute Migration

Once you're satisfied with the dry-run results, execute the migration:

```bash
./venv/bin/python scripts/migrate_offerings_to_notebooks.py
```

**What it does**:
1. Creates PostgreSQL database entries for each notebook
2. Registers documents in `notebook_sources` table
3. Updates ChromaDB metadata to use `notebook_id`
4. Generates migration report with actual results

**Expected Output**:
```
=== Starting Offering → Notebook Migration ===
User ID: default_user
Dry Run: False

--- Processing Offering: AI Digital Engineering ---
Created notebook 'AI Digital Engineering': abc123-def456-...
Registered 1/1 documents in notebook abc123-def456-...
Updated 10 ChromaDB nodes: ai-digital-engineering → abc123-def456-...

=== Migration Summary ===
Offerings found: 6
Notebooks created: 6
Documents migrated: 6
ChromaDB nodes updated: 60
Errors: 0

✅ MIGRATION COMPLETE
```

### Step 4: Verify Migration

Check that notebooks were created in PostgreSQL:

```bash
psql -d rag_chatbot -c "SELECT notebook_id, name, description, document_count FROM notebooks ORDER BY name;"
```

Expected output:
```
     notebook_id      |         name          |              description                | document_count
----------------------+-----------------------+----------------------------------------+----------------
 abc123-def456-...    | AI Digital Engineering| Notebook for AI Digital Engineering... | 1
 ...
```

### Step 5: Update Application Code

The migration utility has already updated:
- ✅ ChromaDB metadata (`offering_id` → `notebook_id`)
- ✅ PostgreSQL database (notebooks and sources registered)

You still need to update:
1. **Remove offering-based code paths**:
   - Remove `selected_offerings` parameter handling
   - Keep only `selected_notebooks` parameter

2. **Update UI templates**:
   - Replace offering selection with notebook selection
   - Update frontend to fetch notebooks instead of offerings

---

## Rollback Strategy

If you need to rollback the migration:

### Option 1: Database Rollback

```sql
-- Delete migrated notebooks
DELETE FROM notebooks WHERE description LIKE '%Migrated from offering ID%';
```

### Option 2: Restore from Backup

If you created a backup before migration:

```bash
# Restore PostgreSQL database
psql -d rag_chatbot < backup_before_migration.sql

# Restore ChromaDB collection
# (ChromaDB doesn't support native restore, would need to re-ingest documents)
```

### Option 3: Re-run Migration

The migration is **idempotent** - you can safely re-run it:
- Existing notebooks with the same name won't be recreated
- Documents already registered will be skipped
- ChromaDB metadata will be updated again (safe)

---

## Troubleshooting

### Error: "DATABASE_URL not set"

**Solution**: Set `DATABASE_URL` in `.env`:
```bash
echo "DATABASE_URL=postgresql://localhost/rag_chatbot" >> .env
```

### Error: "Metadata file not found"

**Solution**: Ensure `data/config/documents_metadata.json` exists:
```bash
ls -la data/config/documents_metadata.json
```

### Error: "No offerings found"

**Cause**: `documents_metadata.json` is empty or has no `offering_name` fields

**Solution**: Verify your metadata file structure matches the expected format

### Error: "Failed to create notebook"

**Causes**:
- PostgreSQL connection issue
- Database schema not initialized
- Duplicate notebook names

**Solutions**:
1. Check PostgreSQL is running: `brew services list`
2. Initialize schema: Run Alembic migrations
3. Check for existing notebooks: `psql -d rag_chatbot -c "SELECT name FROM notebooks;"`

### Warning: "ChromaDB nodes updated: 0"

**Cause**: Documents don't have `offering_id` in their metadata

**Solution**: This is normal for documents without offering_id. Migration will still create notebooks and register documents.

---

## Advanced Options

### Custom User ID

Migrate for a specific user:

```bash
./venv/bin/python scripts/migrate_offerings_to_notebooks.py --user-id my_user_id
```

### Custom Metadata File

Use a different metadata file:

```bash
./venv/bin/python scripts/migrate_offerings_to_notebooks.py \
  --metadata-file /path/to/custom_metadata.json
```

### Custom Database URL

Override the environment variable:

```bash
./venv/bin/python scripts/migrate_offerings_to_notebooks.py \
  --database-url postgresql://user:pass@host/dbname
```

---

## Post-Migration Cleanup

After successful migration and verification:

### 1. Archive Old Configuration Files

```bash
mkdir -p data/config/archive
mv data/config/offerings.json data/config/archive/
mv data/config/documents_metadata.json data/config/archive/
# Keep practices.json if you need IT Practice categories
```

### 2. Remove Offering-Based Code

**Files to update**:
- `rag_chatbot/ui/web.py` - Remove `selected_offerings` handling
- `rag_chatbot/pipeline.py` - Remove offering filter fallback
- Frontend templates - Update UI to use notebooks

**Files to deprecate** (keep for reference):
- `rag_chatbot/core/metadata/metadata_manager.py`
- `data/config/practices.json`

### 3. Update Documentation

Update your project documentation to reflect the notebook-based architecture.

---

## Migration Report Schema

The `migration_report.json` contains:

```json
{
  "started_at": "2025-12-12T...",
  "completed_at": "2025-12-12T...",
  "user_id": "default_user",
  "dry_run": false,
  "offerings_found": 6,
  "notebooks_created": 6,
  "documents_migrated": 6,
  "chromadb_nodes_updated": 60,
  "errors": [],
  "offering_to_notebook_map": {
    "AI Digital Engineering": "abc123-def456-...",
    "Automation": "def789-ghi012-...",
    ...
  }
}
```

**Key Fields**:
- `offerings_found` - Number of unique offerings discovered
- `notebooks_created` - Number of notebooks created in PostgreSQL
- `documents_migrated` - Number of document-notebook associations created
- `chromadb_nodes_updated` - Number of ChromaDB nodes updated with `notebook_id`
- `offering_to_notebook_map` - Mapping of offering names to new notebook IDs
- `errors` - Array of error messages (empty if successful)

---

## Support

If you encounter issues:

1. Check the migration report for errors
2. Verify PostgreSQL connection and schema
3. Review log output for detailed error messages
4. Run dry-run mode to preview without changes

For complex migrations or issues, consult the development team.
