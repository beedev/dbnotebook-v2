#!/usr/bin/env python3
"""
Re-embed all documents from PostgreSQL database into ChromaDB.

This script:
1. Loads all notebooks and their documents from PostgreSQL
2. For each document, checks if file exists on disk
3. Re-embeds documents that exist into ChromaDB with proper metadata
4. Updates chunk counts in database

Usage:
    python scripts/reembed_documents.py
"""
import sys
import os
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dbnotebook.pipeline import LocalRAGPipeline
from dbnotebook.setting import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Re-embed all documents from database."""
    logger.info("Starting document re-embedding process")

    # Initialize settings
    settings = get_settings()

    # Initialize pipeline
    logger.info("Initializing RAG pipeline...")
    database_url = os.getenv("DATABASE_URL")
    pipeline = LocalRAGPipeline(
        host="localhost",
        database_url=database_url
    )

    if not pipeline._notebook_manager:
        logger.error("Notebook manager not available!")
        return 1

    # Get all notebooks for default user
    logger.info("Loading notebooks from database...")
    default_user_id = "00000000-0000-0000-0000-000000000001"
    notebooks = pipeline._notebook_manager.list_notebooks(default_user_id)
    logger.info(f"Found {len(notebooks)} notebooks")

    total_embedded = 0
    total_skipped = 0

    for notebook in notebooks:
        notebook_id = notebook['id']
        notebook_name = notebook['name']

        logger.info(f"\n{'='*60}")
        logger.info(f"Processing notebook: {notebook_name} ({notebook_id})")
        logger.info(f"{'='*60}")

        # Get documents for this notebook
        documents = pipeline._notebook_manager.get_documents(notebook_id)
        logger.info(f"Found {len(documents)} documents in notebook")

        for doc in documents:
            file_name = doc['file_name']
            source_id = doc['source_id']

            # Construct file path - try multiple locations
            if os.path.isabs(file_name):
                # Already an absolute path
                file_path = file_name
            else:
                # Try common locations
                possible_paths = [
                    os.path.join("data", "data", file_name),
                    os.path.join("uploads", file_name),
                    file_name  # Current directory
                ]

                file_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        file_path = path
                        break

                if not file_path:
                    file_path = possible_paths[0]  # Default to data/data

            if not os.path.exists(file_path):
                logger.warning(f"⚠️  File not found: {file_name} - SKIPPING")
                total_skipped += 1
                continue

            logger.info(f"📄 Re-embedding: {file_name}")

            try:
                # Delete existing document record from database
                logger.info(f"   Deleting existing record for source_id={source_id}")
                pipeline._notebook_manager.remove_document(notebook_id, source_id)

                # Also clear from vector store
                logger.info(f"   Clearing nodes from ChromaDB for source_id={source_id}")
                pipeline._vector_store.delete_document_nodes(source_id)

                # Clear memory cache to force re-processing
                pipeline._ingestion._node_store.clear()
                pipeline._ingestion._ingested_file.clear()

                # Re-embed document with notebook metadata
                logger.info(f"   Re-ingesting document into notebook {notebook_id}")
                pipeline.store_nodes(
                    input_files=[file_path],
                    notebook_id=notebook_id,
                    user_id="00000000-0000-0000-0000-000000000001"
                )

                logger.info(f"✅ Successfully re-embedded: {file_name}")
                total_embedded += 1

            except Exception as e:
                logger.error(f"❌ Error re-embedding {file_name}: {e}")
                import traceback
                logger.error(traceback.format_exc())

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("Re-embedding Summary:")
    logger.info(f"{'='*60}")
    logger.info(f"Total documents embedded: {total_embedded}")
    logger.info(f"Total documents skipped:  {total_skipped}")

    # Verify ChromaDB has nodes
    logger.info(f"\n{'='*60}")
    logger.info("Verifying ChromaDB...")
    logger.info(f"{'='*60}")

    all_nodes = pipeline._vector_store.load_all_nodes()
    logger.info(f"Total nodes in ChromaDB: {len(all_nodes)}")

    # Count nodes per notebook
    for notebook in notebooks:
        notebook_id = notebook['id']
        notebook_name = notebook['name']

        notebook_nodes = pipeline._vector_store.get_nodes_by_notebook(all_nodes, notebook_id)
        logger.info(f"  {notebook_name}: {len(notebook_nodes)} nodes")

    logger.info("\n✅ Re-embedding complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
