"""Studio Manager for Content Studio CRUD operations."""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from uuid import UUID, uuid4
from pathlib import Path

from ..db import DatabaseManager
from ..db.models import GeneratedContent, Notebook

logger = logging.getLogger(__name__)


class StudioManager:
    """
    Manages generated content in the Content Studio.

    Features:
    - CRUD operations for generated content
    - Gallery listing with filtering
    - File path management for outputs
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        output_dir: str = "outputs/studio"
    ):
        """
        Initialize studio manager.

        Args:
            db_manager: Database manager for persistence
            output_dir: Directory for storing generated content
        """
        self.db = db_manager
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("StudioManager initialized")

    @property
    def output_dir(self) -> Path:
        """Get the output directory."""
        return self._output_dir

    def create_content(
        self,
        user_id: str,
        content_type: str,
        title: str,
        file_path: str,
        prompt_used: Optional[str] = None,
        source_notebook_id: Optional[str] = None,
        thumbnail_path: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Create a new generated content record.

        Args:
            user_id: User who generated the content
            content_type: Type of content (infographic, mindmap, summary)
            title: Content title
            file_path: Path to the generated file
            prompt_used: The prompt used for generation
            source_notebook_id: Source notebook ID (optional)
            thumbnail_path: Path to thumbnail (optional)
            metadata: Additional metadata

        Returns:
            Dict containing content details
        """
        try:
            with self.db.get_session() as session:
                content = GeneratedContent(
                    content_id=uuid4(),
                    user_id=UUID(user_id),
                    source_notebook_id=UUID(source_notebook_id) if source_notebook_id else None,
                    content_type=content_type,
                    title=title,
                    prompt_used=prompt_used,
                    file_path=file_path,
                    thumbnail_path=thumbnail_path,
                    content_metadata=metadata or {},
                )

                session.add(content)
                session.flush()

                logger.info(f"Created content: {content.content_id} ({content_type})")

                return self._content_to_dict(content)

        except Exception as e:
            logger.error(f"Failed to create content: {e}")
            raise

    def get_content(self, content_id: str) -> Optional[Dict]:
        """
        Get a specific content item.

        Args:
            content_id: UUID of the content

        Returns:
            Content details or None if not found
        """
        try:
            with self.db.get_session() as session:
                content = session.query(GeneratedContent).filter(
                    GeneratedContent.content_id == UUID(content_id)
                ).first()

                if not content:
                    return None

                return self._content_to_dict(content)

        except Exception as e:
            logger.error(f"Failed to get content {content_id}: {e}")
            raise

    def list_gallery(
        self,
        user_id: str,
        content_type: Optional[str] = None,
        notebook_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict]:
        """
        List content in the gallery with optional filters.

        Args:
            user_id: User ID to filter by
            content_type: Optional content type filter
            notebook_id: Optional notebook ID filter
            limit: Maximum results to return
            offset: Offset for pagination

        Returns:
            List of content items
        """
        try:
            with self.db.get_session() as session:
                query = session.query(GeneratedContent).filter(
                    GeneratedContent.user_id == UUID(user_id)
                )

                if content_type:
                    query = query.filter(GeneratedContent.content_type == content_type)

                if notebook_id:
                    query = query.filter(
                        GeneratedContent.source_notebook_id == UUID(notebook_id)
                    )

                query = query.order_by(GeneratedContent.created_at.desc())
                query = query.offset(offset).limit(limit)

                results = []
                for content in query.all():
                    results.append(self._content_to_dict(content))

                logger.info(f"Retrieved {len(results)} gallery items")
                return results

        except Exception as e:
            logger.error(f"Failed to list gallery: {e}")
            raise

    def delete_content(self, content_id: str, delete_files: bool = True) -> bool:
        """
        Delete a content item.

        Args:
            content_id: UUID of the content
            delete_files: Whether to delete the actual files

        Returns:
            True if deleted, False if not found
        """
        try:
            with self.db.get_session() as session:
                content = session.query(GeneratedContent).filter(
                    GeneratedContent.content_id == UUID(content_id)
                ).first()

                if not content:
                    logger.warning(f"Content not found: {content_id}")
                    return False

                # Delete files if requested
                if delete_files:
                    if content.file_path:
                        file_path = Path(content.file_path)
                        if file_path.exists():
                            file_path.unlink()
                            logger.info(f"Deleted file: {file_path}")

                    if content.thumbnail_path:
                        thumb_path = Path(content.thumbnail_path)
                        if thumb_path.exists():
                            thumb_path.unlink()
                            logger.info(f"Deleted thumbnail: {thumb_path}")

                session.delete(content)
                logger.info(f"Deleted content: {content_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to delete content {content_id}: {e}")
            raise

    def get_gallery_stats(self, user_id: str) -> Dict:
        """
        Get statistics about the user's gallery.

        Args:
            user_id: User ID

        Returns:
            Dictionary with gallery statistics
        """
        try:
            with self.db.get_session() as session:
                contents = session.query(GeneratedContent).filter(
                    GeneratedContent.user_id == UUID(user_id)
                ).all()

                type_counts = {}
                for content in contents:
                    type_counts[content.content_type] = type_counts.get(
                        content.content_type, 0
                    ) + 1

                return {
                    "total_items": len(contents),
                    "by_type": type_counts,
                }

        except Exception as e:
            logger.error(f"Failed to get gallery stats: {e}")
            raise

    def _content_to_dict(self, content: GeneratedContent) -> Dict:
        """Convert a GeneratedContent model to a dictionary."""
        return {
            "content_id": str(content.content_id),
            "user_id": str(content.user_id),
            "source_notebook_id": str(content.source_notebook_id) if content.source_notebook_id else None,
            "content_type": content.content_type,
            "title": content.title,
            "prompt_used": content.prompt_used,
            "file_path": content.file_path,
            "thumbnail_path": content.thumbnail_path,
            "metadata": content.content_metadata,  # API returns as "metadata"
            "created_at": content.created_at.isoformat() if content.created_at else None,
        }
