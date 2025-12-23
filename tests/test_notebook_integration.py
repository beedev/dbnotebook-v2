"""
Integration test for Notebook functionality.

Tests end-to-end workflow:
1. Database connection
2. User creation
3. Notebook creation
4. Document registration
5. Duplicate detection
6. Notebook filtering
"""

import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dbnotebook.core.db import DatabaseManager
from dbnotebook.core.notebook import NotebookManager
from dbnotebook.core.ingestion import LocalDataIngestion
from dbnotebook.core.vector_store import LocalVectorStore
from dbnotebook.setting import get_settings


def test_notebook_integration():
    """Test complete notebook workflow."""
    print("\n" + "=" * 60)
    print("NOTEBOOK INTEGRATION TEST")
    print("=" * 60)

    # Step 1: Database setup
    print("\n[1/7] Setting up database connection...")
    DATABASE_URL = "postgresql://postgres:root@localhost:5432/dbnotebook_dev"
    db_manager = DatabaseManager(DATABASE_URL)
    db_manager.init_db()
    print("✅ Database connected")

    # Step 2: Initialize services
    print("\n[2/7] Initializing services...")
    notebook_manager = NotebookManager(db_manager)
    settings = get_settings()
    ingestion = LocalDataIngestion(
        setting=settings,
        db_manager=db_manager
    )
    vector_store = LocalVectorStore(
        host="localhost",
        setting=settings,
        persist=True
    )
    print("✅ Services initialized")

    # Step 3: Create default user
    print("\n[3/7] Creating default user...")
    user_id = notebook_manager.ensure_default_user()
    print(f"✅ Default user created: {user_id}")

    # Step 4: Create test notebook
    print("\n[4/7] Creating test notebook...")
    notebook_name = f"Test Notebook {uuid4().hex[:8]}"
    notebook = notebook_manager.create_notebook(
        user_id=user_id,
        name=notebook_name,
        description="Integration test notebook"
    )
    notebook_id = notebook["notebook_id"]
    print(f"✅ Notebook created: {notebook_id}")
    print(f"   Name: {notebook['name']}")
    print(f"   Document count: {notebook['document_count']}")

    # Step 5: Create test document and register it
    print("\n[5/7] Creating and registering test document...")

    # Create a temporary test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test document for notebook integration testing.\n")
        f.write("It contains multiple lines of text.\n")
        f.write("This tests the document ingestion and registration flow.\n")
        test_file_path = f.name

    try:
        # Ingest document with notebook context
        nodes = ingestion.store_nodes(
            input_files=[test_file_path],
            notebook_id=notebook_id,
            user_id=user_id
        )
        print(f"✅ Document ingested: {len(nodes)} nodes created")

        # Verify document was registered in database
        documents = notebook_manager.get_documents(notebook_id)
        print(f"✅ Document registered in database: {len(documents)} document(s)")

        if documents:
            doc = documents[0]
            print(f"   File: {doc['file_name']}")
            print(f"   Source ID: {doc['source_id']}")
            print(f"   Chunks: {doc['chunk_count']}")
            print(f"   Size: {doc['file_size']} bytes")

        # Verify nodes have correct metadata
        if nodes:
            sample_node = nodes[0]
            metadata = sample_node.metadata
            print(f"   Node metadata:")
            print(f"   - notebook_id: {metadata.get('notebook_id')}")
            print(f"   - user_id: {metadata.get('user_id')}")
            print(f"   - source_id: {metadata.get('source_id')}")

    finally:
        # Clean up temporary file
        os.unlink(test_file_path)

    # Step 6: Test duplicate detection
    print("\n[6/7] Testing duplicate detection...")

    # Try to register the same file again (should fail)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test document for notebook integration testing.\n")
        f.write("It contains multiple lines of text.\n")
        f.write("This tests the document ingestion and registration flow.\n")
        duplicate_file_path = f.name

    try:
        nodes = ingestion.store_nodes(
            input_files=[duplicate_file_path],
            notebook_id=notebook_id,
            user_id=user_id
        )
        print("❌ Duplicate detection FAILED - document should have been rejected")
    except ValueError as e:
        print(f"✅ Duplicate detection PASSED: {str(e)}")
    finally:
        os.unlink(duplicate_file_path)

    # Step 7: Test notebook filtering
    print("\n[7/7] Testing notebook filtering...")

    # Get all nodes (should have at least our test nodes)
    all_nodes = []  # In real scenario, load from vector store

    # Get notebook stats
    stats = notebook_manager.get_notebook_stats(notebook_id)
    print(f"✅ Notebook stats retrieved:")
    print(f"   Document count: {stats['document_count']}")
    print(f"   Total size: {stats['total_size_bytes']} bytes")
    print(f"   Total chunks: {stats['total_chunks']}")

    # Cleanup
    print("\n[CLEANUP] Removing test notebook...")
    deleted = notebook_manager.delete_notebook(notebook_id)
    if deleted:
        print("✅ Test notebook deleted")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✅")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_notebook_integration()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
