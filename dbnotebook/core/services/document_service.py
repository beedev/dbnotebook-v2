"""Document service implementation for DBNotebook.

This module implements the document service layer, handling all document-related
operations including uploads, processing, metadata management, and lifecycle operations.
"""

from typing import Dict, Any, List
from pathlib import Path
import hashlib

from .base import BaseService
from ..interfaces.services import IDocumentService


class DocumentService(BaseService, IDocumentService):
    """Service for document management operations.

    Handles document uploads, processing, metadata management,
    and document lifecycle operations. Coordinates between the
    RAG pipeline, notebook manager, and vector store.
    """

    def upload(
        self,
        file: bytes,
        filename: str,
        notebook_id: str,
        user_id: str | None = None,
        metadata: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """Upload and process a document.

        Args:
            file: File content as bytes
            filename: Original filename
            notebook_id: Notebook UUID to add document to
            user_id: Optional user UUID for ownership
            metadata: Optional document metadata (it_practice, offering_id, etc.)

        Returns:
            Dictionary containing:
            - success: Boolean success status
            - source_id: UUID of created source
            - filename: Processed filename
            - node_count: Number of nodes created
            - file_hash: MD5 hash for duplicate detection
            - error: Optional error message

        Raises:
            ValueError: If required parameters are missing or invalid
            RuntimeError: If notebook manager is not available
        """
        # Validate inputs
        if not file:
            raise ValueError("File content is required")
        if not filename:
            raise ValueError("Filename is required")
        if not notebook_id:
            raise ValueError("notebook_id is required")

        # Validate notebook manager is available
        self._validate_notebook_manager_available()

        effective_user_id = user_id or "00000000-0000-0000-0000-000000000001"

        self._log_operation(
            "upload",
            filename=filename,
            notebook_id=notebook_id,
            user_id=effective_user_id,
            file_size=len(file)
        )

        try:
            # Calculate file hash for duplicate detection
            file_hash = hashlib.md5(file).hexdigest()

            # Save file to upload directory
            upload_dir = Path("uploads")
            upload_dir.mkdir(parents=True, exist_ok=True)
            file_path = upload_dir / filename

            with open(file_path, "wb") as f:
                f.write(file)

            self.logger.info(f"Saved file to: {file_path}")

            # Sanitize metadata
            clean_metadata = {}
            if metadata:
                clean_metadata = self._sanitize_metadata(metadata)

            # Process document using pipeline
            # This will:
            # 1. Register document in PostgreSQL with correct chunk_count
            # 2. Add node metadata (notebook_id, source_id, user_id)
            # 3. Store embeddings in pgvector
            self.pipeline.store_nodes(
                input_files=[str(file_path)],
                notebook_id=notebook_id,
                user_id=effective_user_id
            )

            # Get source_id from notebook manager
            documents = self.notebook_manager.get_documents(notebook_id)
            source_id = None
            node_count = 0

            for doc in documents:
                if doc['file_name'] == filename:
                    source_id = doc['source_id']
                    node_count = doc.get('chunk_count', 0)
                    break

            if not source_id:
                # Document was processed but not found in database
                # This shouldn't happen, but handle gracefully
                self.logger.warning(f"Document {filename} processed but source_id not found")
                return {
                    "success": False,
                    "error": "Document processed but registration failed"
                }

            self.logger.info(
                f"Successfully uploaded {filename} to notebook {notebook_id} "
                f"(source_id: {source_id}, nodes: {node_count})"
            )

            return {
                "success": True,
                "source_id": source_id,
                "filename": filename,
                "node_count": node_count,
                "file_hash": file_hash
            }

        except Exception as e:
            self._log_error("upload", e, filename=filename, notebook_id=notebook_id)
            return {
                "success": False,
                "error": str(e)
            }

    def delete(
        self,
        source_id: str,
        notebook_id: str,
        user_id: str | None = None
    ) -> bool:
        """Delete a document from notebook.

        Args:
            source_id: Source UUID to delete
            notebook_id: Notebook UUID containing the source
            user_id: Optional user UUID for authorization

        Returns:
            True if successful

        Raises:
            ValueError: If required parameters are missing
            RuntimeError: If notebook manager is not available
        """
        # Validate inputs
        if not source_id:
            raise ValueError("source_id is required")
        if not notebook_id:
            raise ValueError("notebook_id is required")

        # Validate notebook manager is available
        self._validate_notebook_manager_available()

        effective_user_id = user_id or "00000000-0000-0000-0000-000000000001"

        # Validate user access (placeholder for now)
        if not self._validate_user_access(effective_user_id, source_id, "document"):
            self.logger.warning(f"User {effective_user_id} denied access to document {source_id}")
            return False

        self._log_operation("delete", source_id=source_id, notebook_id=notebook_id)

        try:
            # Delete from PostgreSQL database
            success = self.notebook_manager.remove_document(notebook_id, source_id)

            if not success:
                self.logger.warning(f"Document {source_id} not found or deletion failed")
                return False

            # Delete from pgvector embeddings table
            if self.pipeline._vector_store:
                pgvector_success = self.pipeline._vector_store.delete_document_nodes(source_id)

                if not pgvector_success:
                    self.logger.warning(
                        f"pgvector deletion failed for document {source_id}, "
                        "but PostgreSQL deletion succeeded"
                    )

            # Clear retriever cache to ensure deleted document isn't used in follow-up queries
            if self.pipeline._engine and hasattr(self.pipeline._engine, '_retriever'):
                retriever = self.pipeline._engine._retriever
                if retriever and hasattr(retriever, 'clear_cache'):
                    retriever.clear_cache()
                    self.logger.debug(f"Cleared retriever cache after deleting document {source_id}")

            self.logger.info(f"Deleted document {source_id} from notebook {notebook_id}")
            return True

        except Exception as e:
            self._log_error("delete", e, source_id=source_id, notebook_id=notebook_id)
            return False

    def toggle_active(
        self,
        source_id: str,
        active: bool,
        notebook_id: str | None = None
    ) -> bool:
        """Toggle document active status for RAG inclusion.

        Args:
            source_id: Source UUID to update
            active: New active status
            notebook_id: Optional notebook UUID for validation

        Returns:
            True if successful

        Raises:
            ValueError: If source_id is missing
            RuntimeError: If notebook manager is not available
        """
        # Validate inputs
        if not source_id:
            raise ValueError("source_id is required")

        # Validate notebook manager is available
        self._validate_notebook_manager_available()

        self._log_operation("toggle_active", source_id=source_id, active=active)

        try:
            # Update document active status
            # Note: notebook_id validation is optional for this operation
            updated_doc = self.notebook_manager.update_document_active(
                notebook_id=notebook_id or "",  # Empty string if not provided
                source_id=source_id,
                active=active
            )

            if not updated_doc:
                self.logger.warning(f"Document {source_id} not found")
                return False

            # Clear retriever cache since active documents affect retrieval
            if self.pipeline._engine and hasattr(self.pipeline._engine, '_retriever'):
                retriever = self.pipeline._engine._retriever
                if retriever and hasattr(retriever, 'clear_cache'):
                    retriever.clear_cache()
                    self.logger.debug(f"Cleared retriever cache after toggling document {source_id}")

            self.logger.info(f"Updated document {source_id} active status to {active}")
            return True

        except Exception as e:
            self._log_error("toggle_active", e, source_id=source_id, active=active)
            return False

    def list_documents(
        self,
        notebook_id: str,
        user_id: str | None = None,
        include_inactive: bool = True
    ) -> List[Dict[str, Any]]:
        """List documents in a notebook.

        Args:
            notebook_id: Notebook UUID
            user_id: Optional user UUID for filtering
            include_inactive: Include inactive documents

        Returns:
            List of document metadata dictionaries containing:
            - source_id: UUID
            - filename: Original filename
            - file_hash: MD5 hash
            - active: Active status
            - created_at: Upload timestamp
            - metadata: Custom metadata

        Raises:
            ValueError: If notebook_id is missing
            RuntimeError: If notebook manager is not available
        """
        # Validate inputs
        if not notebook_id:
            raise ValueError("notebook_id is required")

        # Validate notebook manager is available
        self._validate_notebook_manager_available()

        self._log_operation("list_documents", notebook_id=notebook_id)

        try:
            # Get documents from notebook manager
            documents = self.notebook_manager.get_documents(notebook_id)

            # Filter by active status if needed
            if not include_inactive:
                documents = [doc for doc in documents if doc.get('active', True)]

            # Transform to standard format
            result = []
            for doc in documents:
                result.append({
                    "source_id": doc.get("source_id"),
                    "filename": doc.get("file_name"),
                    "file_hash": doc.get("file_hash"),
                    "active": doc.get("active", True),
                    "created_at": doc.get("created_at"),
                    "file_type": doc.get("file_type"),
                    "chunk_count": doc.get("chunk_count", 0),
                    "metadata": doc.get("metadata", {})
                })

            return result

        except Exception as e:
            self._log_error("list_documents", e, notebook_id=notebook_id)
            raise

    def get_document_info(
        self,
        source_id: str,
        notebook_id: str | None = None
    ) -> Dict[str, Any]:
        """Get detailed information about a document.

        Args:
            source_id: Source UUID
            notebook_id: Optional notebook UUID for validation

        Returns:
            Dictionary with document details and statistics

        Raises:
            ValueError: If source_id is missing
            RuntimeError: If notebook manager is not available
        """
        # Validate inputs
        if not source_id:
            raise ValueError("source_id is required")

        # Validate notebook manager is available
        self._validate_notebook_manager_available()

        self._log_operation("get_document_info", source_id=source_id)

        try:
            # Get all documents and find matching source_id
            # Note: This is inefficient for large notebooks, but works for now
            # TODO: Add direct lookup method to NotebookManager
            if notebook_id:
                documents = self.notebook_manager.get_documents(notebook_id)
            else:
                # Search across all notebooks (inefficient)
                # This is a fallback and should be avoided
                self.logger.warning("get_document_info called without notebook_id - inefficient")
                return {
                    "error": "notebook_id is required for efficient lookup"
                }

            for doc in documents:
                if doc.get("source_id") == source_id:
                    return {
                        "source_id": doc.get("source_id"),
                        "filename": doc.get("file_name"),
                        "file_hash": doc.get("file_hash"),
                        "file_type": doc.get("file_type"),
                        "active": doc.get("active", True),
                        "chunk_count": doc.get("chunk_count", 0),
                        "created_at": doc.get("created_at"),
                        "notebook_id": doc.get("notebook_id"),
                        "metadata": doc.get("metadata", {})
                    }

            # Document not found
            return {
                "error": f"Document {source_id} not found"
            }

        except Exception as e:
            self._log_error("get_document_info", e, source_id=source_id)
            raise

    def update_metadata(
        self,
        source_id: str,
        metadata: Dict[str, Any],
        notebook_id: str | None = None
    ) -> bool:
        """Update document metadata.

        Args:
            source_id: Source UUID
            metadata: New metadata dictionary
            notebook_id: Optional notebook UUID for validation

        Returns:
            True if successful

        Raises:
            ValueError: If source_id is missing
            RuntimeError: If database is not available
        """
        # Validate inputs
        if not source_id:
            raise ValueError("source_id is required")
        if not metadata:
            raise ValueError("metadata is required")

        # Validate database is available
        self._validate_database_available()

        self._log_operation("update_metadata", source_id=source_id)

        try:
            # Sanitize metadata
            clean_metadata = self._sanitize_metadata(metadata)

            # Update metadata in database
            # Note: This requires a direct database update
            # The NotebookManager doesn't currently expose a metadata update method
            # TODO: Add update_metadata method to NotebookManager

            self.logger.warning(
                f"update_metadata not fully implemented - "
                f"NotebookManager needs update_metadata method"
            )

            # For now, return False to indicate not implemented
            return False

        except Exception as e:
            self._log_error("update_metadata", e, source_id=source_id)
            return False
