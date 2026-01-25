# Installation

This guide covers setting up DBNotebook for local development and production deployment.

---

## Prerequisites

### Required

- **Python 3.11+** - Backend runtime
- **Node.js 18+** - Frontend build
- **PostgreSQL 15+** with **pgvector** extension - Vector database

### Optional

- **Docker** - For containerized deployment
- **Ollama** - For local LLM inference

---

## Quick Install (Local Development)

### 1. Clone the Repository

```bash
git clone https://github.com/beedev/dbnotebook-v2.git
cd dbnotebook-v2
```

### 2. Set Up PostgreSQL

=== "macOS (Homebrew)"

    ```bash
    # Install PostgreSQL
    brew install postgresql@17
    brew services start postgresql@17

    # Install pgvector
    brew install pgvector

    # Create database
    createdb dbnotebook_dev

    # Create user
    psql -d dbnotebook_dev -c "CREATE USER dbnotebook WITH PASSWORD 'dbnotebook';"
    psql -d dbnotebook_dev -c "GRANT ALL PRIVILEGES ON DATABASE dbnotebook_dev TO dbnotebook;"
    psql -d dbnotebook_dev -c "CREATE EXTENSION IF NOT EXISTS vector;"
    ```

=== "Ubuntu/Debian"

    ```bash
    # Install PostgreSQL
    sudo apt install postgresql postgresql-contrib

    # Install pgvector
    sudo apt install postgresql-17-pgvector

    # Create database and user
    sudo -u postgres psql <<EOF
    CREATE USER dbnotebook WITH PASSWORD 'dbnotebook';
    CREATE DATABASE dbnotebook_dev OWNER dbnotebook;
    \c dbnotebook_dev
    CREATE EXTENSION IF NOT EXISTS vector;
    EOF
    ```

=== "Docker"

    ```bash
    docker run -d \
      --name postgres-pgvector \
      -e POSTGRES_USER=dbnotebook \
      -e POSTGRES_PASSWORD=dbnotebook \
      -e POSTGRES_DB=dbnotebook_dev \
      -p 5432:5432 \
      pgvector/pgvector:pg17
    ```

### 3. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
# At minimum, set your API keys for the providers you want to use
```

Key environment variables:

```bash
# LLM Provider (choose one)
LLM_PROVIDER=groq              # groq, openai, anthropic, ollama, gemini
GROQ_API_KEY=your_key_here     # If using Groq

# Embedding (OpenAI recommended for best compatibility)
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=your_key_here

# Database
DATABASE_URL=postgresql://dbnotebook:dbnotebook@localhost:5432/dbnotebook_dev
```

### 5. Build Frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

### 6. Run Database Migrations

```bash
# Activate venv if not already
source venv/bin/activate

# Run migrations
PYTHONPATH=. alembic upgrade head
```

### 7. Start the Application

```bash
./dev.sh local
```

Open http://localhost:7860 in your browser.

Default login: `admin` / `admin123`

---

## Docker Deployment

For production-like deployments, use Docker:

```bash
# Build and start
./dev.sh docker

# Or use docker-compose directly
docker compose up --build -d

# View logs
docker compose logs -f
```

The application will be available at http://localhost:7007

---

## Production Deployment (Linux)

For production servers, use the `prod.sh` script:

```bash
# Start production server
./prod.sh start

# Check status
./prod.sh status

# View logs
./prod.sh logs

# Stop server
./prod.sh stop
```

Features:
- PID-based process management
- Automatic log rotation
- Health check endpoint monitoring
- Graceful shutdown

See [Server Deployment Guide](../deployment/SERVER_DEPLOYMENT.md) for full production setup.

---

## Installing Ollama (Optional)

For local, private LLM inference:

=== "macOS"

    ```bash
    brew install ollama
    ollama serve

    # In another terminal, pull a model
    ollama pull llama3.1:latest
    ```

=== "Linux"

    ```bash
    curl -fsSL https://ollama.com/install.sh | sh
    ollama serve

    # Pull a model
    ollama pull llama3.1:latest
    ```

Then set in `.env`:

```bash
LLM_PROVIDER=ollama
OLLAMA_HOST=localhost
OLLAMA_PORT=11434
```

---

## Verifying Installation

After starting the application:

1. **Check health endpoint**: `curl http://localhost:7860/api/health`
2. **Login**: Open http://localhost:7860 and login with `admin` / `admin123`
3. **Create a notebook**: Click "New Notebook"
4. **Upload a document**: Drag and drop a PDF or text file
5. **Ask a question**: Type a question about your document

---

## Troubleshooting

### Database Connection Errors

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Check pgvector extension
psql -d dbnotebook_dev -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

### Embedding Dimension Mismatch

If you see "dimension mismatch" errors:

```bash
# Check your embedding model dimension
# OpenAI text-embedding-3-small = 1536
# nomic-embed-text = 768

# Set in .env
PGVECTOR_EMBED_DIM=1536  # Match your embedding model
```

### Port Already in Use

```bash
# Find process using port 7860
lsof -i :7860

# Kill it
kill -9 <PID>
```

See [Troubleshooting Guide](../troubleshooting.md) for more solutions.
