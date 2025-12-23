"""
Notebook Manager for NotebookLM-style Document Management

Provides CRUD operations for notebooks and document tracking with PostgreSQL persistence.
"""

import logging
import hashlib
from typing import Dict, List, Optional
from datetime import datetime
from uuid import UUID, uuid4

from ..db import DatabaseManager
from ..db.models import Notebook, NotebookSource, User

logger = logging.getLogger(__name__)


class NotebookManager:
    """
    Manages notebooks and their associated documents with database persistence.

    Features:
    - Notebook CRUD operations
    - Document tracking and duplicate detection
    - Statistics and metadata management
    - Multi-user support (ready for future expansion)
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize notebook manager with database connection.

        Args:
            db_manager: DatabaseManager instance for database operations
        """
        self.db = db_manager
        logger.info("NotebookManager initialized")

    # =========================================================================
    # Notebook CRUD Operations
    # =========================================================================

    def create_notebook(
        self,
        user_id: str,
        name: str,
        description: str = ""
    ) -> Dict:
        """
        Create a new notebook for a user.

        Args:
            user_id: UUID of the user creating the notebook
            name: Notebook name (must be unique per user)
            description: Optional notebook description

        Returns:
            Dict containing notebook details (notebook_id, name, description, created_at, etc.)

        Raises:
            ValueError: If notebook name already exists for this user
            Exception: For database errors
        """
        try:
            with self.db.get_session() as session:
                # Check if notebook name already exists for this user
                existing = session.query(Notebook).filter(
                    Notebook.user_id == UUID(user_id),
                    Notebook.name == name
                ).first()

                if existing:
                    raise ValueError(f"Notebook '{name}' already exists for user {user_id}")

                # Create new notebook
                notebook = Notebook(
                    notebook_id=uuid4(),
                    user_id=UUID(user_id),
                    name=name,
                    description=description,
                    document_count=0
                )

                session.add(notebook)
                session.flush()  # Get the notebook_id

                logger.info(f"Created notebook: {notebook.notebook_id} ({name})")

                return {
                    "id": str(notebook.notebook_id),
                    "user_id": str(notebook.user_id),
                    "name": notebook.name,
                    "description": notebook.description,
                    "created_at": notebook.created_at.isoformat(),
                    "updated_at": notebook.updated_at.isoformat(),
                    "document_count": notebook.document_count
                }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to create notebook: {e}")
            raise

    def get_notebook(self, notebook_id: str) -> Optional[Dict]:
        """
        Retrieve notebook details by ID.

        Args:
            notebook_id: UUID of the notebook

        Returns:
            Dict containing notebook details or None if not found
        """
        try:
            with self.db.get_session() as session:
                notebook = session.query(Notebook).filter(
                    Notebook.notebook_id == UUID(notebook_id)
                ).first()

                if not notebook:
                    logger.warning(f"Notebook not found: {notebook_id}")
                    return None

                return {
                    "id": str(notebook.notebook_id),
                    "user_id": str(notebook.user_id),
                    "name": notebook.name,
                    "description": notebook.description,
                    "created_at": notebook.created_at.isoformat(),
                    "updated_at": notebook.updated_at.isoformat(),
                    "document_count": notebook.document_count
                }

        except Exception as e:
            logger.error(f"Failed to get notebook {notebook_id}: {e}")
            raise

    def list_notebooks(self, user_id: str) -> List[Dict]:
        """
        List all notebooks for a user.

        Args:
            user_id: UUID of the user

        Returns:
            List of notebooks ordered by creation date (newest first)
        """
        try:
            with self.db.get_session() as session:
                notebooks = session.query(Notebook).filter(
                    Notebook.user_id == UUID(user_id)
                ).order_by(Notebook.created_at.desc()).all()

                result = []
                for notebook in notebooks:
                    result.append({
                        "id": str(notebook.notebook_id),
                        "user_id": str(notebook.user_id),
                        "name": notebook.name,
                        "description": notebook.description,
                        "created_at": notebook.created_at.isoformat(),
                        "updated_at": notebook.updated_at.isoformat(),
                        "document_count": notebook.document_count
                    })

                logger.info(f"Retrieved {len(result)} notebooks for user {user_id}")
                return result

        except Exception as e:
            logger.error(f"Failed to list notebooks for user {user_id}: {e}")
            raise

    def update_notebook(
        self,
        notebook_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> bool:
        """
        Update notebook details.

        Args:
            notebook_id: UUID of the notebook
            name: New notebook name (optional)
            description: New description (optional)

        Returns:
            True if updated successfully, False if notebook not found

        Raises:
            ValueError: If new name conflicts with existing notebook
        """
        try:
            with self.db.get_session() as session:
                notebook = session.query(Notebook).filter(
                    Notebook.notebook_id == UUID(notebook_id)
                ).first()

                if not notebook:
                    logger.warning(f"Notebook not found for update: {notebook_id}")
                    return False

                # Check name conflict if renaming
                if name and name != notebook.name:
                    existing = session.query(Notebook).filter(
                        Notebook.user_id == notebook.user_id,
                        Notebook.name == name,
                        Notebook.notebook_id != UUID(notebook_id)
                    ).first()

                    if existing:
                        raise ValueError(f"Notebook name '{name}' already exists")

                    notebook.name = name

                if description is not None:
                    notebook.description = description

                notebook.updated_at = datetime.utcnow()

                logger.info(f"Updated notebook: {notebook_id}")
                return True

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to update notebook {notebook_id}: {e}")
            raise

    def delete_notebook(self, notebook_id: str) -> bool:
        """
        Delete a notebook and all its associated documents.

        Note: This will also trigger deletion of associated document sources
        and conversations due to CASCADE constraints.

        Args:
            notebook_id: UUID of the notebook

        Returns:
            True if deleted successfully, False if notebook not found
        """
        try:
            with self.db.get_session() as session:
                notebook = session.query(Notebook).filter(
                    Notebook.notebook_id == UUID(notebook_id)
                ).first()

                if not notebook:
                    logger.warning(f"Notebook not found for deletion: {notebook_id}")
                    return False

                session.delete(notebook)
                logger.info(f"Deleted notebook: {notebook_id} ({notebook.name})")
                return True

        except Exception as e:
            logger.error(f"Failed to delete notebook {notebook_id}: {e}")
            raise

    # =========================================================================
    # Document Management
    # =========================================================================

    def add_document(
        self,
        notebook_id: str,
        file_name: str,
        file_content: bytes,
        file_type: Optional[str] = None,
        chunk_count: Optional[int] = None
    ) -> str:
        """
        Register a document in a notebook with duplicate detection.

        Args:
            notebook_id: UUID of the notebook
            file_name: Name of the document file
            file_content: File content for hash calculation
            file_type: File type/extension (e.g., 'pdf', 'txt')
            chunk_count: Number of chunks the document was split into

        Returns:
            source_id (UUID) of the registered document

        Raises:
            ValueError: If notebook not found or duplicate document detected
            Exception: For database errors
        """
        try:
            # Calculate file hash for duplicate detection
            file_hash = hashlib.sha256(file_content).hexdigest()
            file_size = len(file_content)

            with self.db.get_session() as session:
                # Verify notebook exists
                notebook = session.query(Notebook).filter(
                    Notebook.notebook_id == UUID(notebook_id)
                ).first()

                if not notebook:
                    raise ValueError(f"Notebook not found: {notebook_id}")

                # Check for duplicate file
                existing = session.query(NotebookSource).filter(
                    NotebookSource.notebook_id == UUID(notebook_id),
                    NotebookSource.file_hash == file_hash
                ).first()

                if existing:
                    logger.warning(f"Duplicate document detected: {file_name} (hash: {file_hash})")
                    raise ValueError(f"Document already exists in notebook: {existing.file_name}")

                # Create document source record
                source = NotebookSource(
                    source_id=uuid4(),
                    notebook_id=UUID(notebook_id),
                    file_name=file_name,
                    file_hash=file_hash,
                    file_size=file_size,
                    file_type=file_type,
                    chunk_count=chunk_count
                )

                session.add(source)

                # Update notebook document count
                notebook.document_count += 1
                notebook.updated_at = datetime.utcnow()

                session.flush()

                logger.info(f"Added document to notebook {notebook_id}: {file_name} (source_id: {source.source_id})")
                return str(source.source_id)

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to add document to notebook {notebook_id}: {e}")
            raise

    def get_documents(self, notebook_id: str) -> List[Dict]:
        """
        List all documents in a notebook.

        Args:
            notebook_id: UUID of the notebook

        Returns:
            List of document details ordered by upload timestamp (newest first)
        """
        try:
            with self.db.get_session() as session:
                sources = session.query(NotebookSource).filter(
                    NotebookSource.notebook_id == UUID(notebook_id)
                ).order_by(NotebookSource.upload_timestamp.desc()).all()

                result = []
                for source in sources:
                    result.append({
                        "source_id": str(source.source_id),
                        "notebook_id": str(source.notebook_id),
                        "file_name": source.file_name,
                        "file_hash": source.file_hash,
                        "file_size": source.file_size,
                        "file_type": source.file_type,
                        "chunk_count": source.chunk_count,
                        "upload_timestamp": source.upload_timestamp.isoformat(),
                        "active": getattr(source, 'active', True)  # Default to True for backwards compatibility
                    })

                logger.info(f"Retrieved {len(result)} documents from notebook {notebook_id}")
                return result

        except Exception as e:
            logger.error(f"Failed to get documents for notebook {notebook_id}: {e}")
            raise

    def remove_document(self, notebook_id: str, source_id: str) -> bool:
        """
        Remove a document from a notebook.

        Args:
            notebook_id: UUID of the notebook
            source_id: UUID of the document source

        Returns:
            True if removed successfully, False if document not found
        """
        try:
            with self.db.get_session() as session:
                source = session.query(NotebookSource).filter(
                    NotebookSource.source_id == UUID(source_id),
                    NotebookSource.notebook_id == UUID(notebook_id)
                ).first()

                if not source:
                    logger.warning(f"Document not found: {source_id} in notebook {notebook_id}")
                    return False

                # Update notebook document count
                notebook = session.query(Notebook).filter(
                    Notebook.notebook_id == UUID(notebook_id)
                ).first()

                if notebook:
                    notebook.document_count = max(0, notebook.document_count - 1)
                    notebook.updated_at = datetime.utcnow()

                session.delete(source)
                logger.info(f"Removed document {source_id} from notebook {notebook_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to remove document {source_id}: {e}")
            raise

    def update_document_active(
        self,
        notebook_id: str,
        source_id: str,
        active: bool
    ) -> Optional[Dict]:
        """
        Update the active status of a document.

        Args:
            notebook_id: UUID of the notebook
            source_id: UUID of the document source
            active: Whether the document should be active for RAG retrieval

        Returns:
            Dict containing updated document details, or None if not found
        """
        try:
            with self.db.get_session() as session:
                source = session.query(NotebookSource).filter(
                    NotebookSource.source_id == UUID(source_id),
                    NotebookSource.notebook_id == UUID(notebook_id)
                ).first()

                if not source:
                    logger.warning(f"Document not found: {source_id} in notebook {notebook_id}")
                    return None

                source.active = active

                # Update notebook's updated_at timestamp
                notebook = session.query(Notebook).filter(
                    Notebook.notebook_id == UUID(notebook_id)
                ).first()
                if notebook:
                    notebook.updated_at = datetime.utcnow()

                session.flush()

                logger.info(f"Updated document {source_id} active status to {active}")
                return {
                    "source_id": str(source.source_id),
                    "notebook_id": str(source.notebook_id),
                    "file_name": source.file_name,
                    "file_hash": source.file_hash,
                    "file_size": source.file_size,
                    "file_type": source.file_type,
                    "chunk_count": source.chunk_count,
                    "upload_timestamp": source.upload_timestamp.isoformat(),
                    "active": source.active
                }

        except Exception as e:
            logger.error(f"Failed to update document active status {source_id}: {e}")
            raise

    # =========================================================================
    # Statistics and Utilities
    # =========================================================================

    def get_notebook_stats(self, notebook_id: str) -> Optional[Dict]:
        """
        Get statistics for a notebook.

        Args:
            notebook_id: UUID of the notebook

        Returns:
            Dict containing document count, total size, etc. or None if not found
        """
        try:
            with self.db.get_session() as session:
                notebook = session.query(Notebook).filter(
                    Notebook.notebook_id == UUID(notebook_id)
                ).first()

                if not notebook:
                    return None

                # Calculate total size and chunk count
                sources = session.query(NotebookSource).filter(
                    NotebookSource.notebook_id == UUID(notebook_id)
                ).all()

                total_size = sum(s.file_size or 0 for s in sources)
                total_chunks = sum(s.chunk_count or 0 for s in sources)

                return {
                    "id": str(notebook.notebook_id),
                    "name": notebook.name,
                    "document_count": notebook.document_count,
                    "total_size_bytes": total_size,
                    "total_chunks": total_chunks,
                    "created_at": notebook.created_at.isoformat(),
                    "last_updated": notebook.updated_at.isoformat()
                }

        except Exception as e:
            logger.error(f"Failed to get stats for notebook {notebook_id}: {e}")
            raise

    def ensure_default_user(self, user_id: str = "default", username: str = "Default User") -> str:
        """
        Ensure a default user exists in the database.

        Args:
            user_id: UUID for the default user (default: "default")
            username: Username for the default user

        Returns:
            user_id (UUID string) of the default user
        """
        try:
            # Convert string "default" to a consistent UUID
            if user_id == "default":
                # Use a deterministic UUID for "default" user
                user_uuid = UUID('00000000-0000-0000-0000-000000000001')
            else:
                user_uuid = UUID(user_id)

            with self.db.get_session() as session:
                user = session.query(User).filter(
                    User.user_id == user_uuid
                ).first()

                if not user:
                    user = User(
                        user_id=user_uuid,
                        username=username,
                        email=None
                    )
                    session.add(user)
                    logger.info(f"Created default user: {user_uuid}")

                return str(user_uuid)

        except Exception as e:
            logger.error(f"Failed to ensure default user: {e}")
            raise
