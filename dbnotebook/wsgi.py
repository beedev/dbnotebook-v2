"""
WSGI entry point for Gunicorn.

This module creates the Flask application for use with Gunicorn.
Usage: gunicorn -c gunicorn.conf.py 'dbnotebook.wsgi:app'
"""

# Gevent monkey patching MUST happen before any other imports
# This patches standard library modules for async compatibility
from gevent import monkey
monkey.patch_all()

# Allow nested event loops (fixes LlamaIndex asyncio + gevent conflict)
import nest_asyncio
nest_asyncio.apply()

import os

# Disable background workers in multi-worker mode (asyncio doesn't fork well with gevent)
os.environ["DISABLE_BACKGROUND_WORKERS"] = "true"
import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dbnotebook.ui import FlaskChatbotUI
from dbnotebook.pipeline import LocalRAGPipeline
from dbnotebook.setting import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Reduce noise from third-party libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)
logging.getLogger("werkzeug").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Constants
DATA_DIR = "data/data"
UPLOAD_DIR = "uploads"


def create_app():
    """
    Application factory for Gunicorn.

    Returns:
        Flask: Configured Flask application
    """
    logger.info("Creating Flask application for Gunicorn...")

    # Ensure directories exist
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.warning("DATABASE_URL not set. Notebook features will be unavailable.")

    # Determine Ollama host
    ollama_host = os.getenv("OLLAMA_HOST", "localhost")

    # Initialize pipeline
    logger.info("Initializing RAG pipeline...")
    pipeline = LocalRAGPipeline(host=ollama_host, database_url=database_url)

    # Get database managers from pipeline
    db_manager = pipeline._db_manager
    notebook_manager = pipeline._notebook_manager

    # Ensure default user exists
    if notebook_manager:
        try:
            notebook_manager.ensure_default_user()
            logger.info("Notebook feature initialized successfully")
        except Exception as e:
            logger.error(f"Failed to ensure default user: {e}")

    # Create Flask UI
    logger.info("Building Flask UI...")
    ui = FlaskChatbotUI(
        pipeline=pipeline,
        host=ollama_host,
        data_dir=DATA_DIR,
        upload_dir=UPLOAD_DIR,
        db_manager=db_manager,
        notebook_manager=notebook_manager
    )

    logger.info("Flask application created successfully")
    return ui._app


# Create the application instance for Gunicorn
# Gunicorn will import this module and use the 'app' variable
app = create_app()
