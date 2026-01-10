"""Simple Programmatic API for RAG queries.

Provides a minimal API for programmatic access:
- POST /api/query - Execute query with notebook_id and get response

Designed for:
- API integrations
- Scripting and automation
- Simple Q&A without complex routing
"""

import logging
import os
import time
from flask import request, jsonify
from functools import wraps

logger = logging.getLogger(__name__)

# Optional API key authentication
API_KEY = os.getenv("API_KEY")


def require_api_key(f):
    """Decorator to optionally require API key if API_KEY env var is set."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if API_KEY:
            provided_key = request.headers.get("X-API-Key")
            if provided_key != API_KEY:
                return jsonify({
                    "success": False,
                    "error": "Invalid or missing API key"
                }), 401
        return f(*args, **kwargs)
    return decorated


def create_query_routes(app, pipeline, db_manager, notebook_manager):
    """Create simple programmatic query API routes.

    Args:
        app: Flask application instance
        pipeline: LocalRAGPipeline instance
        db_manager: DatabaseManager instance
        notebook_manager: NotebookManager instance
    """

    @app.route("/api/query", methods=["POST"])
    @require_api_key
    def api_query():
        """
        Simple programmatic API for RAG queries.

        Request JSON:
            {
                "notebook_id": "uuid",           # Required
                "query": "string",               # Required
                "mode": "chat|QA",               # Optional, default: "chat"
                "include_sources": true,         # Optional, default: true
                "max_sources": 6,                # Optional, default: 6
                "session_id": "uuid"             # Optional, for conversation continuity
            }

        Response JSON:
            {
                "success": true,
                "response": "LLM response text",
                "sources": [
                    {
                        "document": "paper1.pdf",
                        "excerpt": "First 200 chars...",
                        "score": 0.92
                    }
                ],
                "metadata": {
                    "execution_time_ms": 850,
                    "model": "llama3.1:latest",
                    "retrieval_strategy": "hybrid"
                }
            }
        """
        start_time = time.time()

        try:
            data = request.json or {}

            # Validate required fields
            notebook_id = data.get("notebook_id")
            query = data.get("query")

            if not notebook_id:
                return jsonify({
                    "success": False,
                    "error": "notebook_id is required"
                }), 400

            if not query:
                return jsonify({
                    "success": False,
                    "error": "query is required"
                }), 400

            # Optional parameters
            mode = data.get("mode", "chat")
            include_sources = data.get("include_sources", True)
            max_sources = min(data.get("max_sources", 6), 20)  # Cap at 20

            logger.info(f"API query: notebook_id={notebook_id}, mode={mode}, include_sources={include_sources}")

            # Verify notebook exists
            notebook = notebook_manager.get_notebook(notebook_id)
            if not notebook:
                return jsonify({
                    "success": False,
                    "error": f"Notebook not found: {notebook_id}"
                }), 404

            # Configure pipeline for this notebook (uses caching internally)
            pipeline.set_language(pipeline._language)
            pipeline.set_model()
            pipeline.set_engine(offering_filter=[notebook_id], force_reset=False)

            # Get cached nodes for this notebook
            nodes = pipeline._get_cached_nodes(notebook_id)
            logger.debug(f"Got {len(nodes)} cached nodes for notebook {notebook_id}")

            # Build sources from retrieval if requested
            sources = []
            retrieval_strategy = "hybrid"

            if include_sources and nodes:
                try:
                    from llama_index.core import Settings
                    from llama_index.core.schema import QueryBundle

                    # Get retriever (uses cache)
                    retriever = pipeline._engine._retriever.get_retrievers(
                        llm=Settings.llm,
                        language="eng",
                        nodes=nodes,
                        offering_filter=[notebook_id],
                        vector_store=pipeline._vector_store,
                        notebook_id=notebook_id
                    )

                    # Retrieve relevant chunks
                    query_bundle = QueryBundle(query_str=query)
                    retrieval_results = retriever.retrieve(query_bundle)

                    # Format sources
                    for node_with_score in retrieval_results[:max_sources]:
                        node = node_with_score.node
                        metadata = node.metadata or {}
                        sources.append({
                            "document": metadata.get("file_name", "Unknown"),
                            "excerpt": node.text[:200] + "..." if len(node.text) > 200 else node.text,
                            "score": round(node_with_score.score or 0.0, 3)
                        })

                    retrieval_strategy = retriever.__class__.__name__.replace("Retriever", "").lower()

                except Exception as e:
                    logger.warning(f"Source retrieval failed: {e}")
                    # Continue without sources

            # Execute query (uses cached engine)
            chatbot_history = [[query, ""]]  # Format expected by pipeline.query()

            streaming_response = pipeline.query(
                mode=mode,
                message=query,
                chatbot=chatbot_history
            )

            # Collect response
            response_text = ""
            for chunk in streaming_response.response_gen:
                response_text += chunk

            execution_time_ms = int((time.time() - start_time) * 1000)

            logger.info(f"API query completed in {execution_time_ms}ms, {len(sources)} sources")

            return jsonify({
                "success": True,
                "response": response_text,
                "sources": sources,
                "metadata": {
                    "execution_time_ms": execution_time_ms,
                    "model": pipeline._default_model.model if pipeline._default_model else "unknown",
                    "retrieval_strategy": retrieval_strategy,
                    "node_count": len(nodes)
                }
            })

        except Exception as e:
            logger.error(f"Error in query endpoint: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/query/notebooks", methods=["GET"])
    @require_api_key
    def api_query_list_notebooks():
        """
        List available notebooks for querying.

        Response JSON:
            {
                "success": true,
                "notebooks": [
                    {
                        "id": "uuid",
                        "name": "My Notebook",
                        "document_count": 5,
                        "created_at": "2024-01-01T00:00:00Z"
                    }
                ]
            }
        """
        try:
            # Get user_id from query param or use default UUID for single-user deployments
            default_user_id = "00000000-0000-0000-0000-000000000001"
            user_id = request.args.get("user_id", default_user_id)
            notebooks = notebook_manager.list_notebooks(user_id)

            notebook_list = []
            for nb in notebooks:
                notebook_list.append({
                    "id": nb.get("id"),
                    "name": nb.get("name"),
                    "document_count": nb.get("document_count", 0),
                    "created_at": nb.get("created_at")
                })

            return jsonify({
                "success": True,
                "notebooks": notebook_list
            })

        except Exception as e:
            logger.error(f"Error listing notebooks: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    return app
