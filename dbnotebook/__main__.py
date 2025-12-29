import argparse
import logging
import os
import sys
from pathlib import Path

import llama_index.core

from .ui import FlaskChatbotUI
from .pipeline import LocalRAGPipeline
from .ollama import run_ollama_server, is_port_open
from .core.db.db import DatabaseManager
from .core.notebook.notebook_manager import NotebookManager


def setup_logging(log_level: str = "INFO") -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)
    logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.ERROR)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("psycopg2").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)

# Constants
DATA_DIR = "data/data"
UPLOAD_DIR = "uploads"


def main():
    """Main entry point for the RAG chatbot application."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="RAG Chatbot Application")
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Host for Ollama server (localhost or host.docker.internal)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port for the web server"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run in debug mode"
    )
    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger.info(f"Starting RAG Chatbot - Host: {args.host}")

    # Ensure directories exist
    data_path = Path(DATA_DIR)
    data_path.mkdir(parents=True, exist_ok=True)
    upload_path = Path(UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Data directory: {data_path.absolute()}")

    # Start Ollama server if running locally (not in Docker)
    ollama_host = os.getenv("OLLAMA_HOST", "localhost")
    if "host.docker.internal" not in ollama_host:
        port_number = 11434
        if not is_port_open(port_number):
            logger.info("Starting Ollama server...")
            run_ollama_server()
    else:
        logger.info(f"Running in Docker - using external Ollama at {ollama_host}")

    # Initialize settings
    from .setting import get_settings
    settings = get_settings()

    # Disable LlamaIndex verbose logging (it prints full node content including embeddings)
    # llama_index.core.set_global_handler("simple")
    logger.info("LlamaIndex verbose logging disabled")

    # Initialize pipeline with database support
    logger.info("Initializing RAG pipeline...")
    database_url = os.getenv("DATABASE_URL")
    pipeline = LocalRAGPipeline(host=args.host, database_url=database_url)

    # Use the pipeline's database managers (already initialized if database_url is set)
    db_manager = pipeline._db_manager
    notebook_manager = pipeline._notebook_manager

    # Ensure default user exists if notebook manager is available
    if notebook_manager:
        try:
            notebook_manager.ensure_default_user()
            logger.info("Notebook feature initialized successfully")
        except Exception as e:
            logger.error(f"Failed to ensure default user: {e}")
    else:
        logger.warning("DATABASE_URL not set. Notebook feature will be unavailable.")

    # Initialize Flask UI
    logger.info("Building Flask UI...")
    ui = FlaskChatbotUI(
        pipeline=pipeline,
        host=args.host,
        data_dir=DATA_DIR,
        upload_dir=UPLOAD_DIR,
        db_manager=db_manager,
        notebook_manager=notebook_manager
    )

    # Launch application
    logger.info(f"Starting server on http://0.0.0.0:{args.port}")
    print(f"\n  RAG Chatbot is running at: http://localhost:{args.port}\n")
    ui.run(host="0.0.0.0", port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
