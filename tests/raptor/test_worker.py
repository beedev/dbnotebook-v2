"""Tests for RAPTOR worker module."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from dbnotebook.core.raptor.worker import (
    RAPTORJob,
    RAPTORWorker,
    build_raptor_tree_sync,
)
from dbnotebook.core.raptor.config import RAPTORConfig


class TestRAPTORJob:
    """Tests for RAPTORJob dataclass."""

    def test_job_creation(self):
        """Test creating a RAPTOR job."""
        job = RAPTORJob(
            source_id="source_1",
            notebook_id="notebook_1",
            file_name="test.pdf",
        )

        assert job.source_id == "source_1"
        assert job.notebook_id == "notebook_1"
        assert job.file_name == "test.pdf"


class TestRAPTORWorker:
    """Tests for RAPTORWorker class."""

    def test_init(self):
        """Test worker initialization."""
        mock_db = MagicMock()
        mock_vector_store = MagicMock()

        worker = RAPTORWorker(
            db_manager=mock_db,
            vector_store=mock_vector_store,
        )

        assert worker.db == mock_db
        assert worker.vector_store == mock_vector_store
        assert worker.config is not None
        assert worker._running is False

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        mock_db = MagicMock()
        mock_vector_store = MagicMock()
        config = RAPTORConfig.fast()

        worker = RAPTORWorker(
            db_manager=mock_db,
            vector_store=mock_vector_store,
            config=config,
        )

        assert worker.config.tree_building.max_tree_depth == 3

    def test_start_stop(self):
        """Test starting and stopping the worker."""
        mock_db = MagicMock()
        mock_vector_store = MagicMock()

        worker = RAPTORWorker(
            db_manager=mock_db,
            vector_store=mock_vector_store,
            poll_interval=0.1,
        )

        # Start worker
        worker.start()
        assert worker._running is True
        assert worker._thread is not None
        assert worker._thread.is_alive()

        # Stop worker
        worker.stop()
        assert worker._running is False

    def test_double_start(self):
        """Test that double start is handled."""
        mock_db = MagicMock()
        mock_vector_store = MagicMock()

        worker = RAPTORWorker(
            db_manager=mock_db,
            vector_store=mock_vector_store,
        )

        worker.start()
        worker.start()  # Should not raise

        worker.stop()

    def test_queue_job(self):
        """Test queueing a job."""
        mock_db = MagicMock()
        mock_vector_store = MagicMock()

        worker = RAPTORWorker(
            db_manager=mock_db,
            vector_store=mock_vector_store,
        )

        worker.start()

        job = RAPTORJob(
            source_id="source_1",
            notebook_id="notebook_1",
            file_name="test.pdf",
        )

        # Should not raise
        worker.queue_job(job)

        worker.stop()

    def test_get_pending_sources(self):
        """Test getting pending sources from database."""
        mock_db = MagicMock()
        mock_vector_store = MagicMock()

        # Mock the session and query
        mock_session = MagicMock()
        mock_source = MagicMock()
        mock_source.source_id = "test-source-id"
        mock_source.notebook_id = "test-notebook-id"
        mock_source.file_name = "test.pdf"
        mock_source.raptor_status = "pending"

        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = [
            mock_source
        ]
        mock_db.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        worker = RAPTORWorker(
            db_manager=mock_db,
            vector_store=mock_vector_store,
        )

        pending = worker._get_pending_sources()

        assert len(pending) == 1
        assert pending[0]["source_id"] == "test-source-id"

    def test_update_status(self):
        """Test updating RAPTOR status."""
        mock_db = MagicMock()
        mock_vector_store = MagicMock()

        # Mock the session and source
        mock_session = MagicMock()
        mock_source = MagicMock()
        mock_source.raptor_status = "pending"
        mock_source.raptor_error = None
        mock_source.raptor_built_at = None
        mock_session.query.return_value.filter.return_value.first.return_value = mock_source
        mock_db.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        worker = RAPTORWorker(
            db_manager=mock_db,
            vector_store=mock_vector_store,
        )

        # Use a valid UUID
        worker._update_status("00000000-0000-0000-0000-000000000001", "completed")

        # The mock_source attributes are set directly in _update_status
        # We need to verify the method was called properly
        mock_session.query.assert_called()


class TestBuildRaptorTreeSync:
    """Tests for build_raptor_tree_sync function."""

    def test_no_llm(self):
        """Test with no LLM available."""
        mock_db = MagicMock()
        mock_vector_store = MagicMock()

        with patch('dbnotebook.core.raptor.worker.Settings') as mock_settings:
            mock_settings.llm = None
            mock_settings.embed_model = MagicMock()

            result = build_raptor_tree_sync(
                db_manager=mock_db,
                vector_store=mock_vector_store,
                source_id="source_1",
                notebook_id="notebook_1",
            )

            assert result.success is False
            assert "not available" in result.error

    def test_no_embed_model(self):
        """Test with no embed model available."""
        mock_db = MagicMock()
        mock_vector_store = MagicMock()

        with patch('dbnotebook.core.raptor.worker.Settings') as mock_settings:
            mock_settings.llm = MagicMock()
            mock_settings.embed_model = None

            result = build_raptor_tree_sync(
                db_manager=mock_db,
                vector_store=mock_vector_store,
                source_id="source_1",
                notebook_id="notebook_1",
            )

            assert result.success is False
            assert "not available" in result.error

    def test_no_chunks(self):
        """Test with no chunks found."""
        mock_db = MagicMock()
        mock_vector_store = MagicMock()
        mock_vector_store.get_nodes_by_tree_level.return_value = []

        with patch('dbnotebook.core.raptor.worker.Settings') as mock_settings:
            mock_settings.llm = MagicMock()
            mock_settings.embed_model = MagicMock()

            result = build_raptor_tree_sync(
                db_manager=mock_db,
                vector_store=mock_vector_store,
                source_id="source_1",
                notebook_id="notebook_1",
            )

            assert result.success is False
            assert "No chunks" in result.error
