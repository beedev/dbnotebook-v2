"""AI Transformations API routes.

Provides endpoints for:
- Getting transformation status and results for a source
- Retrying failed transformations
- Listing sources with transformation status
"""

import logging
from uuid import UUID
from flask import request, jsonify

from ...core.db import DatabaseManager
from ...core.db.models import NotebookSource
from ...core.transformations import TransformationWorker, TransformationJob

logger = logging.getLogger(__name__)


def create_transformation_routes(
    app,
    db_manager: DatabaseManager,
    transformation_worker: TransformationWorker = None,
):
    """Create AI Transformations API routes.

    Args:
        app: Flask application instance
        db_manager: DatabaseManager instance
        transformation_worker: Optional TransformationWorker for retries
    """

    @app.route('/api/sources/<source_id>/transformations', methods=['GET'])
    def get_transformations(source_id: str):
        """Get transformation status and results for a source.

        Returns:
            JSON with transformation status, results, and metadata
        """
        try:
            with db_manager.get_session() as session:
                source = session.query(NotebookSource).filter(
                    NotebookSource.source_id == UUID(source_id)
                ).first()

                if not source:
                    return jsonify({
                        "success": False,
                        "error": "Source not found"
                    }), 404

                return jsonify({
                    "success": True,
                    "source_id": str(source.source_id),
                    "file_name": source.file_name,
                    "transformation_status": source.transformation_status or "pending",
                    "transformation_error": source.transformation_error,
                    "transformed_at": source.transformed_at.isoformat() if source.transformed_at else None,
                    "transformations": {
                        "dense_summary": source.dense_summary,
                        "key_insights": source.key_insights,
                        "reflection_questions": source.reflection_questions,
                    }
                })

        except ValueError as e:
            return jsonify({
                "success": False,
                "error": f"Invalid source ID format: {e}"
            }), 400
        except Exception as e:
            logger.error(f"Error getting transformations for source {source_id}: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/sources/<source_id>/transformations/retry', methods=['POST'])
    def retry_transformations(source_id: str):
        """Retry failed transformations for a source.

        Request body (optional):
            {
                "document_text": "full document text"  // If not provided, will try to get from chunks
            }

        Returns:
            JSON with status indicating if retry was queued
        """
        if not transformation_worker:
            return jsonify({
                "success": False,
                "error": "Transformation worker not available"
            }), 503

        try:
            data = request.get_json() or {}
            document_text = data.get("document_text", "")

            with db_manager.get_session() as session:
                source = session.query(NotebookSource).filter(
                    NotebookSource.source_id == UUID(source_id)
                ).first()

                if not source:
                    return jsonify({
                        "success": False,
                        "error": "Source not found"
                    }), 404

                # Reset status to pending
                source.transformation_status = "pending"
                source.transformation_error = None

                # Create job for the worker
                job = TransformationJob(
                    source_id=str(source.source_id),
                    document_text=document_text,
                    notebook_id=str(source.notebook_id),
                    file_name=source.file_name
                )

                # Queue the job
                transformation_worker.queue_job(job)

                return jsonify({
                    "success": True,
                    "message": "Transformation retry queued",
                    "source_id": str(source.source_id)
                })

        except ValueError as e:
            return jsonify({
                "success": False,
                "error": f"Invalid source ID format: {e}"
            }), 400
        except Exception as e:
            logger.error(f"Error retrying transformations for source {source_id}: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/notebooks/<notebook_id>/transformations', methods=['GET'])
    def list_notebook_transformations(notebook_id: str):
        """List all sources in a notebook with their transformation status.

        Query params:
            status: Filter by transformation_status (pending, processing, completed, failed)

        Returns:
            JSON with list of sources and their transformation status
        """
        try:
            status_filter = request.args.get('status')

            with db_manager.get_session() as session:
                query = session.query(NotebookSource).filter(
                    NotebookSource.notebook_id == UUID(notebook_id),
                    NotebookSource.active == True
                )

                if status_filter:
                    query = query.filter(
                        NotebookSource.transformation_status == status_filter
                    )

                sources = query.order_by(NotebookSource.upload_timestamp.desc()).all()

                return jsonify({
                    "success": True,
                    "notebook_id": notebook_id,
                    "total": len(sources),
                    "sources": [
                        {
                            "source_id": str(s.source_id),
                            "file_name": s.file_name,
                            "transformation_status": s.transformation_status or "pending",
                            "transformation_error": s.transformation_error,
                            "transformed_at": s.transformed_at.isoformat() if s.transformed_at else None,
                            "has_summary": bool(s.dense_summary),
                            "has_insights": bool(s.key_insights),
                            "has_questions": bool(s.reflection_questions),
                        }
                        for s in sources
                    ]
                })

        except ValueError as e:
            return jsonify({
                "success": False,
                "error": f"Invalid notebook ID format: {e}"
            }), 400
        except Exception as e:
            logger.error(f"Error listing transformations for notebook {notebook_id}: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/transformations/stats', methods=['GET'])
    def get_transformation_stats():
        """Get overall transformation statistics.

        Returns:
            JSON with counts by status and overall metrics
        """
        try:
            from sqlalchemy import func

            with db_manager.get_session() as session:
                # Count by status
                status_counts = session.query(
                    NotebookSource.transformation_status,
                    func.count(NotebookSource.source_id)
                ).filter(
                    NotebookSource.active == True
                ).group_by(
                    NotebookSource.transformation_status
                ).all()

                stats = {
                    "pending": 0,
                    "processing": 0,
                    "completed": 0,
                    "failed": 0,
                }

                for status, count in status_counts:
                    if status in stats:
                        stats[status] = count
                    elif status is None:
                        stats["pending"] += count

                stats["total"] = sum(stats.values())

                return jsonify({
                    "success": True,
                    "stats": stats
                })

        except Exception as e:
            logger.error(f"Error getting transformation stats: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    logger.info("Transformation API routes registered")
