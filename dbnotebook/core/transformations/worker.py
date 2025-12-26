"""Background worker for processing AI transformations.

Processes transformation jobs asynchronously:
1. Polls for pending transformations
2. Generates summaries, insights, and questions
3. Stores embeddings for transformation content
4. Updates source records with results
"""

import asyncio
import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Callable
from uuid import UUID

from sqlalchemy.orm import Session

from ..db import DatabaseManager
from ..db.models import NotebookSource
from .transformation_service import TransformationService, TransformationResult

logger = logging.getLogger(__name__)


@dataclass
class TransformationJob:
    """A job to process transformations for a source."""
    source_id: str
    document_text: str
    notebook_id: str
    file_name: str


class TransformationWorker:
    """Background worker for processing document transformations.

    Runs in a background thread, processing transformation jobs from a queue.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        transformation_service: Optional[TransformationService] = None,
        embed_callback: Optional[Callable[[str, str, str, str], None]] = None,
        poll_interval: float = 5.0,
        max_concurrent: int = 2,
    ):
        """Initialize the transformation worker.

        Args:
            db_manager: Database manager for accessing sources
            transformation_service: Service for generating transformations
            embed_callback: Optional callback to embed transformation text
                           Signature: (text, node_type, source_id, notebook_id) -> None
            poll_interval: Seconds between polling for new jobs
            max_concurrent: Maximum concurrent transformation jobs
        """
        self.db = db_manager
        self.service = transformation_service or TransformationService()
        self.embed_callback = embed_callback
        self.poll_interval = poll_interval
        self.max_concurrent = max_concurrent

        self._queue: asyncio.Queue = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._semaphore: Optional[asyncio.Semaphore] = None

    def start(self):
        """Start the background worker thread."""
        if self._running:
            logger.warning("Worker already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Transformation worker started")

    def stop(self):
        """Stop the background worker."""
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info("Transformation worker stopped")

    def queue_job(self, job: TransformationJob):
        """Queue a transformation job for processing."""
        if self._queue and self._loop:
            self._loop.call_soon_threadsafe(
                self._queue.put_nowait, job
            )
            logger.info(f"Queued transformation job for source: {job.source_id}")

    def _run_loop(self):
        """Run the async event loop in the background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._queue = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(self.max_concurrent)

        try:
            self._loop.run_until_complete(self._main_loop())
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
        finally:
            self._loop.close()

    async def _main_loop(self):
        """Main processing loop."""
        # Start polling task
        poll_task = asyncio.create_task(self._poll_pending())

        while self._running:
            try:
                # Wait for job from queue with timeout
                job = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=self.poll_interval
                )
                # Process job with semaphore for concurrency control
                asyncio.create_task(self._process_with_semaphore(job))
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in main loop: {e}")

        poll_task.cancel()

    async def _poll_pending(self):
        """Poll database for pending transformations."""
        while self._running:
            try:
                pending = self._get_pending_sources()
                for source_data in pending:
                    job = TransformationJob(
                        source_id=source_data["source_id"],
                        document_text=source_data.get("document_text", ""),
                        notebook_id=source_data["notebook_id"],
                        file_name=source_data["file_name"],
                    )
                    await self._queue.put(job)

                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error polling pending: {e}")
                await asyncio.sleep(self.poll_interval)

    async def _process_with_semaphore(self, job: TransformationJob):
        """Process job with semaphore for concurrency control."""
        async with self._semaphore:
            await self._process_job(job)

    async def _process_job(self, job: TransformationJob):
        """Process a single transformation job."""
        source_id = job.source_id
        logger.info(f"Processing transformation for source: {source_id} ({job.file_name})")

        try:
            # Update status to processing
            self._update_status(source_id, "processing")

            # Generate transformations
            if not job.document_text:
                logger.warning(f"No document text for source: {source_id}")
                self._update_status(source_id, "failed", "No document text available")
                return

            result = await self.service.generate_all(job.document_text)

            if not result.success:
                self._update_status(source_id, "failed", result.error)
                return

            # Store transformations in database
            self._store_transformations(source_id, result)

            # Optionally embed transformation content
            if self.embed_callback:
                await self._embed_transformations(job, result)

            # Update status to completed
            self._update_status(source_id, "completed")
            logger.info(f"Completed transformation for source: {source_id}")

        except Exception as e:
            logger.error(f"Failed to process transformation for {source_id}: {e}")
            self._update_status(source_id, "failed", str(e))

    def _get_pending_sources(self, limit: int = 10) -> List[dict]:
        """Get sources with pending transformation status."""
        try:
            with self.db.get_session() as session:
                sources = session.query(NotebookSource).filter(
                    NotebookSource.transformation_status == "pending"
                ).limit(limit).all()

                return [
                    {
                        "source_id": str(s.source_id),
                        "notebook_id": str(s.notebook_id),
                        "file_name": s.file_name,
                        "document_text": "",  # Will be loaded separately if needed
                    }
                    for s in sources
                ]
        except Exception as e:
            logger.error(f"Error getting pending sources: {e}")
            return []

    def _update_status(
        self,
        source_id: str,
        status: str,
        error: Optional[str] = None
    ):
        """Update transformation status for a source."""
        try:
            with self.db.get_session() as session:
                source = session.query(NotebookSource).filter(
                    NotebookSource.source_id == UUID(source_id)
                ).first()

                if source:
                    source.transformation_status = status
                    source.transformation_error = error
                    if status == "completed":
                        source.transformed_at = datetime.utcnow()

                    logger.debug(f"Updated status for {source_id}: {status}")

        except Exception as e:
            logger.error(f"Error updating status for {source_id}: {e}")

    def _store_transformations(self, source_id: str, result: TransformationResult):
        """Store transformation results in the source record."""
        try:
            with self.db.get_session() as session:
                source = session.query(NotebookSource).filter(
                    NotebookSource.source_id == UUID(source_id)
                ).first()

                if source:
                    if result.dense_summary:
                        source.dense_summary = result.dense_summary
                    if result.key_insights:
                        source.key_insights = result.key_insights
                    if result.reflection_questions:
                        source.reflection_questions = result.reflection_questions

                    logger.debug(f"Stored transformations for {source_id}")

        except Exception as e:
            logger.error(f"Error storing transformations for {source_id}: {e}")

    async def _embed_transformations(
        self,
        job: TransformationJob,
        result: TransformationResult
    ):
        """Embed transformation content for retrieval."""
        if not self.embed_callback:
            return

        try:
            # Embed summary
            if result.dense_summary:
                self.embed_callback(
                    result.dense_summary,
                    "summary",
                    job.source_id,
                    job.notebook_id
                )

            # Embed each insight
            if result.key_insights:
                for i, insight in enumerate(result.key_insights):
                    self.embed_callback(
                        insight,
                        "insight",
                        job.source_id,
                        job.notebook_id
                    )

            # Embed each question
            if result.reflection_questions:
                for i, question in enumerate(result.reflection_questions):
                    self.embed_callback(
                        question,
                        "question",
                        job.source_id,
                        job.notebook_id
                    )

        except Exception as e:
            logger.error(f"Error embedding transformations for {job.source_id}: {e}")


def process_source_transformations(
    db_manager: DatabaseManager,
    source_id: str,
    document_text: str,
    llm=None,
) -> TransformationResult:
    """Process transformations synchronously for a single source.

    Convenience function for immediate processing (not background).

    Args:
        db_manager: Database manager
        source_id: Source ID to process
        document_text: Full document text
        llm: Optional LLM override

    Returns:
        TransformationResult with generated content
    """
    service = TransformationService(llm=llm)

    # Create event loop if needed
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    result = loop.run_until_complete(service.generate_all(document_text))

    if result.success:
        # Store in database
        try:
            with db_manager.get_session() as session:
                source = session.query(NotebookSource).filter(
                    NotebookSource.source_id == UUID(source_id)
                ).first()

                if source:
                    if result.dense_summary:
                        source.dense_summary = result.dense_summary
                    if result.key_insights:
                        source.key_insights = result.key_insights
                    if result.reflection_questions:
                        source.reflection_questions = result.reflection_questions
                    source.transformation_status = "completed"
                    source.transformed_at = datetime.utcnow()

        except Exception as e:
            logger.error(f"Error storing transformations: {e}")
            result.error = str(e)
    else:
        # Update status to failed
        try:
            with db_manager.get_session() as session:
                source = session.query(NotebookSource).filter(
                    NotebookSource.source_id == UUID(source_id)
                ).first()
                if source:
                    source.transformation_status = "failed"
                    source.transformation_error = result.error
        except Exception as e:
            logger.error(f"Error updating failed status: {e}")

    return result
