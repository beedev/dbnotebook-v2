"""Base service class providing common functionality.

This module provides the base service class that all service implementations
should inherit from. It provides common functionality like pipeline access,
logging configuration, and error handling patterns.
"""

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ...pipeline import LocalRAGPipeline
    from ..db import DatabaseManager
    from ..notebook import NotebookManager


class BaseService:
    """Base class for all service implementations.

    Provides common functionality including:
    - Pipeline access for RAG operations
    - Database manager access for persistence
    - Notebook manager access for document organization
    - Standardized logging configuration
    - Common error handling patterns

    All service implementations should inherit from this class.
    """

    def __init__(
        self,
        pipeline: "LocalRAGPipeline",
        db_manager: Optional["DatabaseManager"] = None,
        notebook_manager: Optional["NotebookManager"] = None
    ):
        """Initialize base service.

        Args:
            pipeline: LocalRAGPipeline instance for RAG operations
            db_manager: Optional DatabaseManager for persistence
            notebook_manager: Optional NotebookManager for notebook operations
        """
        self._pipeline = pipeline
        self._db_manager = db_manager
        self._notebook_manager = notebook_manager

        # Configure logger with class name
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.setLevel(logging.INFO)

    @property
    def pipeline(self) -> "LocalRAGPipeline":
        """Access to the RAG pipeline."""
        return self._pipeline

    @property
    def db_manager(self) -> Optional["DatabaseManager"]:
        """Access to the database manager."""
        return self._db_manager

    @property
    def notebook_manager(self) -> Optional["NotebookManager"]:
        """Access to the notebook manager."""
        return self._notebook_manager

    @property
    def logger(self) -> logging.Logger:
        """Access to the service logger."""
        return self._logger

    def _validate_database_available(self) -> None:
        """Validate that database features are available.

        Raises:
            RuntimeError: If database manager is not configured
        """
        if self._db_manager is None:
            raise RuntimeError(
                "Database features are not available. "
                "Service requires DATABASE_URL to be configured."
            )

    def _validate_notebook_manager_available(self) -> None:
        """Validate that notebook manager is available.

        Raises:
            RuntimeError: If notebook manager is not configured
        """
        if self._notebook_manager is None:
            raise RuntimeError(
                "Notebook features are not available. "
                "Service requires database to be configured."
            )

    def _log_operation(
        self,
        operation: str,
        **kwargs
    ) -> None:
        """Log a service operation with context.

        Args:
            operation: Operation name
            **kwargs: Additional context to log
        """
        context = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        self._logger.info(f"{operation}: {context}")

    def _log_error(
        self,
        operation: str,
        error: Exception,
        **kwargs
    ) -> None:
        """Log an error with context.

        Args:
            operation: Operation that failed
            error: Exception that occurred
            **kwargs: Additional context to log
        """
        context = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        self._logger.error(
            f"{operation} failed: {error.__class__.__name__}: {error}",
            extra={"context": context},
            exc_info=True
        )

    def _validate_user_access(
        self,
        user_id: str,
        resource_id: str,
        resource_type: str
    ) -> bool:
        """Validate user has access to a resource.

        This is a placeholder for future authorization logic.
        Currently returns True (permissive).

        Args:
            user_id: User UUID
            resource_id: Resource UUID (notebook_id, source_id, etc.)
            resource_type: Type of resource ("notebook", "document", etc.)

        Returns:
            True if user has access, False otherwise
        """
        # TODO: Implement actual authorization logic
        # For now, allow all access
        return True

    def _sanitize_metadata(
        self,
        metadata: dict
    ) -> dict:
        """Sanitize metadata dictionary.

        Removes None values and ensures all values are JSON-serializable.

        Args:
            metadata: Raw metadata dictionary

        Returns:
            Sanitized metadata dictionary
        """
        sanitized = {}
        for key, value in metadata.items():
            if value is not None:
                # Ensure JSON-serializable types
                if isinstance(value, (str, int, float, bool, list, dict)):
                    sanitized[key] = value
                else:
                    # Convert to string for non-standard types
                    sanitized[key] = str(value)
        return sanitized
