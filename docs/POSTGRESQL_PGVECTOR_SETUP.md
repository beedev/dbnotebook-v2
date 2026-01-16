# PostgreSQL + pgvector Installation Guide

This guide covers installing PostgreSQL with the pgvector extension for DBNotebook.

## Table of Contents

1. [Quick Start (Docker)](#quick-start-docker)
2. [macOS Installation](#macos-installation)
3. [Ubuntu/Debian Installation](#ubuntudebian-installation)
4. [Windows Installation](#windows-installation)
5. [pgvector Configuration](#pgvector-configuration)
6. [Verify Installation](#verify-installation)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start (Docker)

The easiest way to get PostgreSQL + pgvector running is with Docker. **This is the recommended approach for DBNotebook.**

### Using docker-compose (Recommended)

DBNotebook includes PostgreSQL in its `docker-compose.yml`:

```bash
docker compose up -d
```

This automatically:
- Starts PostgreSQL 15 with pgvector 0.7.0
- Creates the database `dbnotebook`
- Exposes port 5433 (to avoid conflicts with local PostgreSQL)

### Standalone PostgreSQL with pgvector

If you need a standalone PostgreSQL container:

```bash
# Pull and run pgvector image
docker run -d \
  --name pgvector-db \
  -e POSTGRES_USER=dbnotebook \
  -e POSTGRES_PASSWORD=dbnotebook \
  -e POSTGRES_DB=dbnotebook \
  -p 5433:5432 \
  pgvector/pgvector:pg16

# Verify it's running
docker logs pgvector-db

# Connect with psql
docker exec -it pgvector-db psql -U dbnotebook -d dbnotebook
```

### Enable pgvector Extension

Once connected to PostgreSQL:

```sql
-- Create the vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';
```

---

## macOS Installation

### Option 1: Homebrew (Recommended)

```bash
# Install PostgreSQL
brew install postgresql@15

# Start PostgreSQL service
brew services start postgresql@15

# Add to PATH (add to ~/.zshrc or ~/.bash_profile)
export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"

# Install pgvector
brew install pgvector

# Create database
createdb dbnotebook

# Connect and enable extension
psql -d dbnotebook -c "CREATE EXTENSION vector;"
```

### Option 2: Postgres.app

1. Download [Postgres.app](https://postgresapp.com/)
2. Move to Applications and launch
3. Click "Initialize" to create a default server
4. Install pgvector:

```bash
# Find pg_config path
/Applications/Postgres.app/Contents/Versions/latest/bin/pg_config --pgxs

# Install pgvector from source
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make PG_CONFIG=/Applications/Postgres.app/Contents/Versions/latest/bin/pg_config
make install PG_CONFIG=/Applications/Postgres.app/Contents/Versions/latest/bin/pg_config

# Enable extension
psql -d postgres -c "CREATE DATABASE dbnotebook;"
psql -d dbnotebook -c "CREATE EXTENSION vector;"
```

---

## Ubuntu/Debian Installation

### Step 1: Install PostgreSQL

```bash
# Add PostgreSQL APT repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# Update and install
sudo apt update
sudo apt install -y postgresql-15 postgresql-contrib-15

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Step 2: Install pgvector

```bash
# Install build dependencies
sudo apt install -y postgresql-server-dev-15 build-essential git

# Clone and build pgvector
git clone --branch v0.7.0 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# Verify installation
ls /usr/share/postgresql/15/extension/ | grep vector
```

### Step 3: Configure Database

```bash
# Switch to postgres user
sudo -u postgres psql

# In psql:
CREATE USER dbnotebook WITH PASSWORD 'dbnotebook';
CREATE DATABASE dbnotebook OWNER dbnotebook;
\c dbnotebook
CREATE EXTENSION vector;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO dbnotebook;
\q
```

### Step 4: Allow Password Authentication

Edit `/etc/postgresql/15/main/pg_hba.conf`:

```
# Add this line (before "local all all peer")
local   all             dbnotebook                              md5
host    all             dbnotebook      127.0.0.1/32            md5
```

Restart PostgreSQL:

```bash
sudo systemctl restart postgresql
```

---

## Windows Installation

### Step 1: Install PostgreSQL

1. Download [PostgreSQL installer](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
2. Run installer (select PostgreSQL 15+)
3. Set password for `postgres` user
4. Keep default port 5432
5. Complete installation

### Step 2: Install pgvector

**Option A: Pre-built Binary (Easier)**

1. Download from [pgvector releases](https://github.com/pgvector/pgvector/releases)
2. Extract to PostgreSQL installation:
   - Copy `vector.dll` to `C:\Program Files\PostgreSQL\15\lib`
   - Copy `vector--*.sql` and `vector.control` to `C:\Program Files\PostgreSQL\15\share\extension`

**Option B: Build from Source**

Requires Visual Studio Build Tools:

```cmd
# Open "x64 Native Tools Command Prompt for VS"
git clone https://github.com/pgvector/pgvector.git
cd pgvector
nmake /F Makefile.win
nmake /F Makefile.win install
```

### Step 3: Create Database

Open pgAdmin or psql:

```sql
CREATE DATABASE dbnotebook;
\c dbnotebook
CREATE EXTENSION vector;
```

---

## pgvector Configuration

### Embedding Dimensions

DBNotebook supports different embedding dimensions. Configure in `.env`:

```bash
# OpenAI text-embedding-3-small (default)
PGVECTOR_EMBED_DIM=1536

# Nomic/HuggingFace models
PGVECTOR_EMBED_DIM=768

# OpenAI text-embedding-3-large
PGVECTOR_EMBED_DIM=3072
```

### Index Configuration

For optimal performance with large document collections:

```sql
-- Connect to database
\c dbnotebook

-- Create HNSW index for faster similarity search
CREATE INDEX ON data_embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- For very large collections (>1M vectors), use IVFFlat
CREATE INDEX ON data_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

### Connection Pooling

For production deployments, configure connection pooling in your `.env`:

```bash
# SQLAlchemy pool settings
SQLALCHEMY_POOL_SIZE=20
SQLALCHEMY_MAX_OVERFLOW=30
SQLALCHEMY_POOL_TIMEOUT=30
```

---

## Verify Installation

### Test Connection

```bash
# Test with psql
psql -h localhost -p 5433 -U dbnotebook -d dbnotebook -c "SELECT 1;"

# Test pgvector
psql -h localhost -p 5433 -U dbnotebook -d dbnotebook -c "SELECT '[1,2,3]'::vector;"
```

### Test from Python

```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="dbnotebook",
    user="dbnotebook",
    password="dbnotebook"
)

cur = conn.cursor()

# Test pgvector
cur.execute("SELECT '[1,2,3]'::vector;")
print(cur.fetchone())  # Should print: ([1.0, 2.0, 3.0],)

# Test similarity search
cur.execute("""
    SELECT '[1,2,3]'::vector <-> '[1,2,4]'::vector AS distance;
""")
print(cur.fetchone())  # Should print: (1.0,)

conn.close()
```

### DBNotebook Connection Test

```bash
# Set environment variables
export DATABASE_URL="postgresql://dbnotebook:dbnotebook@localhost:5433/dbnotebook"

# Or use individual settings
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5433
export POSTGRES_DB=dbnotebook
export POSTGRES_USER=dbnotebook
export POSTGRES_PASSWORD=dbnotebook

# Start DBNotebook
docker compose up -d
```

---

## Troubleshooting

### "extension vector does not exist"

The pgvector extension is not installed. See installation steps above for your OS.

```sql
-- Check available extensions
SELECT * FROM pg_available_extensions WHERE name = 'vector';
```

### "could not access file vector.control"

pgvector files are not in the correct location:
- Linux: `/usr/share/postgresql/15/extension/`
- macOS (Homebrew): `/opt/homebrew/share/postgresql@15/extension/`
- Windows: `C:\Program Files\PostgreSQL\15\share\extension\`

### Connection Refused

1. Check if PostgreSQL is running:
   ```bash
   # Linux
   sudo systemctl status postgresql

   # macOS
   brew services list

   # Docker
   docker ps | grep postgres
   ```

2. Check port configuration:
   ```bash
   # Default PostgreSQL port: 5432
   # DBNotebook Docker: 5433
   ```

### "password authentication failed"

1. Check `pg_hba.conf` allows password authentication
2. Verify username/password match
3. Try resetting password:
   ```sql
   ALTER USER dbnotebook WITH PASSWORD 'dbnotebook';
   ```

### Dimension Mismatch Error

```
ValueError: dimension mismatch: expected 1536, got 768
```

Your embedding model dimension doesn't match the table schema:

```sql
-- Check current dimension
SELECT column_name, udt_name
FROM information_schema.columns
WHERE table_name = 'data_embeddings' AND column_name = 'embedding';

-- Recreate table with correct dimension (CAUTION: data loss)
-- Or update PGVECTOR_EMBED_DIM in .env to match
```

### Slow Similarity Search

Create an index:

```sql
-- For cosine similarity (most common)
CREATE INDEX idx_embedding_cosine ON data_embeddings
USING hnsw (embedding vector_cosine_ops);

-- Analyze table for query planner
ANALYZE data_embeddings;
```

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | - | Full connection URL (overrides individual settings) |
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `dbnotebook` | Database name |
| `POSTGRES_USER` | `dbnotebook` | Database user |
| `POSTGRES_PASSWORD` | `dbnotebook` | Database password |
| `PGVECTOR_EMBED_DIM` | `1536` | Embedding dimension |

### Example .env

```bash
# Database connection
DATABASE_URL=postgresql://dbnotebook:dbnotebook@localhost:5433/dbnotebook

# Or individual settings
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=dbnotebook
POSTGRES_USER=dbnotebook
POSTGRES_PASSWORD=dbnotebook

# Embedding dimension (must match your embedding model)
PGVECTOR_EMBED_DIM=1536  # OpenAI text-embedding-3-small
```

---

## Quick Reference

### Common psql Commands

```sql
-- Connect
psql -h localhost -p 5433 -U dbnotebook -d dbnotebook

-- List databases
\l

-- List tables
\dt

-- Describe table
\d data_embeddings

-- Check pgvector version
SELECT extversion FROM pg_extension WHERE extname = 'vector';

-- Exit
\q
```

### Docker Commands

```bash
# Start PostgreSQL
docker compose up -d db

# View logs
docker compose logs db

# Connect with psql
docker compose exec db psql -U dbnotebook -d dbnotebook

# Stop
docker compose down
```
