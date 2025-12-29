"""Multi-notebook query API routes.

Provides endpoints for querying across multiple notebooks simultaneously,
enabling cross-notebook search and information discovery.
"""

import logging
from flask import Blueprint, request, jsonify

from ...core.services.multi_notebook_service import MultiNotebookService


logger = logging.getLogger(__name__)


def create_multi_notebook_routes(app, pipeline, notebook_manager=None):
    """Create multi-notebook query routes.

    Args:
        app: Flask application instance
        pipeline: LocalRAGPipeline instance
        notebook_manager: Optional NotebookManager instance
    """

    # Initialize service
    service = MultiNotebookService(
        pipeline=pipeline,
        notebook_manager=notebook_manager
    )

    @app.route("/api/multi-notebook/query", methods=["POST"])
    def query_multiple_notebooks():
        """Query across multiple notebooks.

        Request JSON:
            {
                "query": "User search query",
                "notebook_ids": ["uuid1", "uuid2", ...],
                "user_id": "user-uuid",  # Optional
                "top_k": 10  # Optional, default: 10
            }

        Response JSON:
            {
                "success": true,
                "answer": "Unified answer synthesizing all sources...",
                "sources": [
                    {
                        "notebook_id": "uuid",
                        "notebook_name": "My Notebook",
                        "source_id": "doc-uuid",
                        "filename": "document.pdf",
                        "content": "Relevant excerpt...",
                        "score": 0.85,
                        "page": 5,
                        "section": "Introduction"
                    }
                ],
                "notebook_coverage": {
                    "uuid1": {
                        "notebook_name": "Notebook 1",
                        "hits": 3,
                        "relevance": 0.82
                    },
                    "uuid2": {
                        "notebook_name": "Notebook 2",
                        "hits": 2,
                        "relevance": 0.75
                    }
                }
            }

        Error Response:
            {
                "success": false,
                "error": "Error message"
            }
        """
        try:
            data = request.get_json()

            # Validate required fields
            query = data.get("query", "").strip()
            if not query:
                return jsonify({
                    "success": False,
                    "error": "Query is required"
                }), 400

            notebook_ids = data.get("notebook_ids", [])
            if not notebook_ids:
                return jsonify({
                    "success": False,
                    "error": "At least one notebook_id is required"
                }), 400

            if not isinstance(notebook_ids, list):
                return jsonify({
                    "success": False,
                    "error": "notebook_ids must be a list"
                }), 400

            # Optional parameters - use default user if not provided
            user_id = data.get("user_id") or "00000000-0000-0000-0000-000000000001"
            top_k = data.get("top_k", 10)

            # Validate top_k
            try:
                top_k = int(top_k)
                if top_k < 1 or top_k > 50:
                    top_k = 10  # Reset to default if out of range
            except (ValueError, TypeError):
                top_k = 10

            logger.info(
                f"Multi-notebook query: {len(notebook_ids)} notebooks, "
                f"top_k={top_k}, user={user_id}"
            )

            # Execute query
            result = service.query_multiple(
                query=query,
                notebook_ids=notebook_ids,
                user_id=user_id,
                top_k=top_k
            )

            # Check for errors in result
            if "error" in result and not result.get("answer"):
                return jsonify({
                    "success": False,
                    "error": result["error"]
                }), 400

            # Return successful result
            return jsonify({
                "success": True,
                "answer": result["answer"],
                "sources": result["sources"],
                "notebook_coverage": result["notebook_coverage"]
            })

        except Exception as e:
            logger.error(f"Error in multi-notebook query: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": f"Internal server error: {str(e)}"
            }), 500

    @app.route("/api/multi-notebook/notebooks", methods=["GET"])
    def list_queryable_notebooks():
        """List notebooks available for multi-notebook query.

        Returns notebooks that have at least one document.

        Query Parameters:
            user_id: Optional user UUID for filtering

        Response JSON:
            {
                "success": true,
                "notebooks": [
                    {
                        "id": "uuid",
                        "name": "My Notebook",
                        "document_count": 5
                    }
                ]
            }

        Error Response:
            {
                "success": false,
                "error": "Error message"
            }
        """
        try:
            # Use default user if not provided
            user_id = request.args.get("user_id") or "00000000-0000-0000-0000-000000000001"

            logger.info(f"Listing queryable notebooks for user={user_id}")

            notebooks = service.get_queryable_notebooks(user_id=user_id)

            return jsonify({
                "success": True,
                "notebooks": notebooks
            })

        except Exception as e:
            logger.error(f"Error listing queryable notebooks: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": f"Internal server error: {str(e)}"
            }), 500

    logger.info("Multi-notebook query routes initialized")
