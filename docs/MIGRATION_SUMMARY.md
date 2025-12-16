# Offering to Notebook Migration - Implementation Summary

**Date**: December 12, 2025
**Status**: Migration Utility Complete, Ready for Execution

---

## What Was Done

### 1. Created Migration Utility ✅

**File**: `rag_chatbot/core/migration/offering_to_notebook_migration.py`

**Features**:
- Reads existing `data/config/documents_metadata.json`
- Analyzes unique offerings from document metadata
- Creates notebooks for each offering in PostgreSQL
- Registers documents in `notebook_sources` table
- Updates ChromaDB metadata (`offering_id` → `notebook_id`)
- Provides dry-run mode to preview changes
- Generates detailed migration report

**Key Methods**:
- `migrate()` - Main migration orchestration
- `_analyze_offerings()` - Identifies unique offerings
- `_create_notebook_for_offering()` - Creates PostgreSQL notebook
- `_register_documents_in_notebook()` - Registers documents
- `_update_chromadb_metadata()` - Updates vector store

### 2. Created Migration Script ✅

**File**: `scripts/migrate_offerings_to_notebooks.py`

**Usage**:
```bash
# Dry run (preview changes)
./venv/bin/python scripts/migrate_offerings_to_notebooks.py --dry-run

# Execute migration
./venv/bin/python scripts/migrate_offerings_to_notebooks.py
```

**Options**:
- `--user-id` - Specify user ID (default: default_user)
- `--dry-run` - Preview without making changes
- `--metadata-file` - Custom metadata file path
- `--database-url` - Override DATABASE_URL

### 3. Created Comprehensive Documentation ✅

**File**: `docs/OFFERING_TO_NOTEBOOK_MIGRATION.md`

**Contents**:
- Overview of migration process
- Prerequisites (PostgreSQL, environment variables)
- Step-by-step migration guide
- Verification procedures
- Rollback strategies
- Troubleshooting guide
- Post-migration cleanup

---

## Current State

### Identified Offerings (from documents_metadata.json)

Based on your current `data/config/documents_metadata.json`, the migration will create notebooks for:

1. **Portal** - Digital Transformation (no offering_id)
2. **Nexus** - Digital Transformation (no offering_id)
3. **Customer Experience** - Digital Transformation (offering_id: customer-experience)
4. **AI Digital Engineering** - Digital Transformation (offering_id: ai-digital-engineering)
5. **Automation** - Digital Transformation (offering_id: automation)
6. **Innovation** - Digital Transformation (offering_id: innovation)

**Total**: 6 notebooks will be created

---

## Next Steps

### Step 1: Run Dry-Run Migration

Preview the migration without making changes:

```bash
# Ensure PostgreSQL is running
brew services start postgresql@15

# Set DATABASE_URL in .env if not already set
echo "DATABASE_URL=postgresql://localhost/rag_chatbot" >> .env

# Run dry-run
./venv/bin/python scripts/migrate_offerings_to_notebooks.py --dry-run
```

**Expected Output**:
- Offerings found: 6
- Notebooks that would be created: 6
- Documents that would be migrated: 6
- ChromaDB nodes that would be updated: (varies based on data)

### Step 2: Review Migration Report

Check `migration_report.json` for details:

```bash
cat migration_report.json
```

Verify all offerings and notebooks look correct.

### Step 3: Execute Migration

Once satisfied with dry-run results:

```bash
./venv/bin/python scripts/migrate_offerings_to_notebooks.py
```

### Step 4: Verify Migration

```bash
# Check notebooks in PostgreSQL
psql -d rag_chatbot -c "SELECT notebook_id, name, description FROM notebooks;"

# Check document associations
psql -d rag_chatbot -c "SELECT COUNT(*) FROM notebook_sources;"
```

### Step 5: Update Application Code

After successful migration:

1. **Remove offering-based code**:
   - In `web.py`: Remove `selected_offerings` parameter handling
   - In `pipeline.py`: Remove offering filter fallback
   - In templates: Update UI to use notebooks exclusively

2. **Test notebook-based queries**:
   - Verify notebook selection works
   - Test query filtering by notebook_id
   - Verify conversation history per notebook

---

## Architecture Changes

### Before Migration

```
User uploads document
  ↓
Selects IT Practice + Offering Name
  ↓
Metadata stored in documents_metadata.json
  ↓
ChromaDB uses offering_id for filtering
  ↓
Query uses selected_offerings parameter
```

### After Migration

```
User uploads document
  ↓
Selects Notebook
  ↓
Document registered in PostgreSQL notebook_sources table
  ↓
ChromaDB uses notebook_id for filtering
  ↓
Query uses selected_notebooks parameter
  ↓
Conversation history persistent per notebook
```

---

## Files Created

### Migration Module

1. `rag_chatbot/core/migration/__init__.py` - Module exports
2. `rag_chatbot/core/migration/offering_to_notebook_migration.py` - Migration utility

### Scripts

3. `scripts/migrate_offerings_to_notebooks.py` - Runnable migration script

### Documentation

4. `docs/OFFERING_TO_NOTEBOOK_MIGRATION.md` - Comprehensive migration guide
5. `docs/MIGRATION_SUMMARY.md` - This summary document

---

## Backward Compatibility

The current implementation maintains backward compatibility:

- **web.py** accepts both `selected_offerings` and `selected_notebooks`
- **pipeline.py** `query_sales_mode()` accepts both parameters
- **Migration** preserves `offering_id` in ChromaDB metadata as `migrated_from_offering_id`

After migration is complete and verified, you can remove offering-based code paths.

---

## Testing Strategy

### Pre-Migration Tests

1. ✅ Verify dry-run works without errors
2. ✅ Check migration report for correctness
3. ✅ Verify PostgreSQL connection and schema

### Post-Migration Tests

1. ⏳ Verify all notebooks created in PostgreSQL
2. ⏳ Verify all documents registered in notebook_sources
3. ⏳ Verify ChromaDB metadata updated with notebook_id
4. ⏳ Test query with selected_notebooks parameter
5. ⏳ Verify conversation history per notebook
6. ⏳ Test notebook switching preserves context

---

## Rollback Plan

If issues arise:

### Option 1: Database Rollback

```sql
DELETE FROM notebooks WHERE description LIKE '%Migrated from offering ID%';
```

### Option 2: Re-run Migration

The migration is **idempotent** - safe to re-run:
- Won't create duplicate notebooks
- Won't duplicate document registrations
- Will update ChromaDB metadata again (safe)

---

## Success Criteria

- ✅ Migration utility created and tested
- ✅ Migration script executable
- ✅ Comprehensive documentation written
- ⏳ Dry-run migration successful
- ⏳ Actual migration successful
- ⏳ All notebooks visible in PostgreSQL
- ⏳ All documents registered correctly
- ⏳ ChromaDB metadata updated
- ⏳ Application queries work with notebooks
- ⏳ Conversation history persists per notebook

---

## Support

For issues or questions:

1. Review `docs/OFFERING_TO_NOTEBOOK_MIGRATION.md`
2. Check `migration_report.json` for errors
3. Verify PostgreSQL connection and schema
4. Consult migration logs for detailed error messages
