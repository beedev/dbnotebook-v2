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
        Multi-user safe programmatic API for RAG queries.

        This endpoint is stateless and thread-safe for concurrent requests.
        Uses the default LLM model configured at startup.

        Request JSON:
            {
                "notebook_id": "uuid",           # Required
                "query": "string",               # Required
                "mode": "chat|QA",               # Optional, default: "chat" (ignored, always stateless)
                "include_sources": true,         # Optional, default: true
                "max_sources": 6                 # Optional, default: 6, max: 20
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
        timings = {}  # Track timing for each stage

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

            # Optional parameters (model removed for multi-user safety)
            mode = data.get("mode", "chat")  # Kept for API compatibility but ignored
            include_sources = data.get("include_sources", True)
            max_sources = min(data.get("max_sources", 6), 20)  # Cap at 20

            logger.info(f"API query: notebook_id={notebook_id}, mode={mode}, include_sources={include_sources}")

            # Step 1: Verify notebook exists
            t1 = time.time()
            notebook = notebook_manager.get_notebook(notebook_id)
            timings["1_notebook_lookup_ms"] = int((time.time() - t1) * 1000)

            if not notebook:
                return jsonify({
                    "success": False,
                    "error": f"Notebook not found: {notebook_id}"
                }), 404

            # MULTI-USER SAFE: No global state mutations
            # - Uses thread-safe _get_cached_nodes
            # - Creates per-request retriever
            # - Uses global Settings.llm (stateless completion, no chat history)

            # Step 2: Get cached nodes for this notebook (thread-safe)
            t2 = time.time()
            nodes = pipeline._get_cached_nodes(notebook_id)
            timings["2_node_cache_ms"] = int((time.time() - t2) * 1000)
            logger.debug(f"Got {len(nodes)} cached nodes for notebook {notebook_id}")

            # Build sources from retrieval
            sources = []
            retrieval_results = []
            retrieval_strategy = "hybrid"

            if nodes:
                try:
                    from llama_index.core import Settings
                    from llama_index.core.schema import QueryBundle

                    # Verify engine is initialized (set during app startup)
                    if not pipeline._engine or not pipeline._engine._retriever:
                        return jsonify({
                            "success": False,
                            "error": "Pipeline not initialized. Please try again."
                        }), 503

                    # Step 3: Create RAPTOR-aware retriever (same as UI /chat)
                    # This enables hierarchical retrieval + reranking for cross-document understanding
                    t3 = time.time()
                    retriever = pipeline._engine._retriever.get_combined_raptor_retriever(
                        llm=Settings.llm,
                        language="eng",
                        nodes=nodes,
                        vector_store=pipeline._vector_store,
                        notebook_id=notebook_id,
                        source_ids=None,  # Will check all sources in notebook
                    )
                    timings["3_create_retriever_ms"] = int((time.time() - t3) * 1000)

                    # Step 4: Retrieve relevant chunks
                    t4 = time.time()
                    query_bundle = QueryBundle(query_str=query)
                    retrieval_results = retriever.retrieve(query_bundle)
                    timings["4_chunk_retrieval_ms"] = int((time.time() - t4) * 1000)

                    # Step 5: Format sources for response
                    t5 = time.time()
                    if include_sources:
                        for node_with_score in retrieval_results[:max_sources]:
                            node = node_with_score.node
                            metadata = node.metadata or {}
                            sources.append({
                                "document": metadata.get("file_name", "Unknown"),
                                "excerpt": node.text[:200] + "..." if len(node.text) > 200 else node.text,
                                "score": float(round(node_with_score.score or 0.0, 3))
                            })
                    timings["5_format_sources_ms"] = int((time.time() - t5) * 1000)

                    retrieval_strategy = retriever.__class__.__name__.replace("Retriever", "").lower()

                except Exception as e:
                    logger.warning(f"Source retrieval failed: {e}")
                    # Continue without sources

            # Step 6.5: RAPTOR cluster summaries (bounded, O(log n))
            # Adds high-level context without breaking existing flow
            t6 = time.time()
            raptor_summaries = []
            if pipeline._vector_store and hasattr(pipeline._vector_store, 'get_top_raptor_summaries'):
                try:
                    from llama_index.core import Settings as LlamaSettings
                    # Get query embedding for similarity search
                    t6a = time.time()
                    query_embedding = LlamaSettings.embed_model.get_query_embedding(query)
                    timings["6a_raptor_embedding_ms"] = int((time.time() - t6a) * 1000)

                    # Bounded lookup: max 5 summaries, tree_level >= 1
                    t6b = time.time()
                    raptor_results = pipeline._vector_store.get_top_raptor_summaries(
                        notebook_id=notebook_id,
                        query_embedding=query_embedding,
                        top_k=5
                    )
                    timings["6b_raptor_lookup_ms"] = int((time.time() - t6b) * 1000)

                    raptor_summaries = [
                        (node, score) for node, score in raptor_results
                        if score >= 0.3  # Relevance threshold
                    ]
                    if raptor_summaries:
                        logger.info(f"Retrieved {len(raptor_summaries)} RAPTOR summaries for query")
                except Exception as e:
                    logger.debug(f"RAPTOR summaries unavailable: {e}")
                    # Continue without summaries - graceful degradation
            timings["6_raptor_total_ms"] = int((time.time() - t6) * 1000)

            # Step 7: Build hierarchical context
            t7 = time.time()
            # STATELESS LLM CALL: No shared chat history, no engine state
            # Build hierarchical context: RAPTOR summaries (framing) + chunks (evidence)
            context_parts = []

            # Add RAPTOR summaries first (high-level framing)
            if raptor_summaries:
                summary_texts = []
                for node, score in raptor_summaries[:3]:  # Max 3 summaries for context
                    summary_texts.append(node.text)
                if summary_texts:
                    context_parts.append("## HIGH-LEVEL CONTEXT (Document Summaries)\n" + "\n\n".join(summary_texts))

            # Add retrieved chunks (detailed evidence)
            chunk_texts = []
            for node_with_score in retrieval_results[:max_sources]:
                node = node_with_score.node
                metadata = node.metadata or {}
                doc_name = metadata.get("file_name", "Unknown")
                chunk_texts.append(f"[Source: {doc_name}]\n{node.text}")

            if chunk_texts:
                context_parts.append("## DETAILED EVIDENCE (Relevant Passages)\n" + "\n\n---\n\n".join(chunk_texts))

            context = "\n\n".join(context_parts) if context_parts else "No relevant context found."
            timings["7_context_building_ms"] = int((time.time() - t7) * 1000)

            # Step 8: Generate response using global LLM (stateless, thread-safe)
            # Use the same rich system prompt as UI /chat for intelligent responses
            t8 = time.time()
            from llama_index.core import Settings
            from dbnotebook.core.prompt import get_system_prompt, get_context_prompt

            system_prompt = get_system_prompt("eng", is_rag_prompt=True)
            context_prompt_template = get_context_prompt("eng")
            context_prompt = context_prompt_template.format(context_str=context)

            prompt = f"""{system_prompt}

{context_prompt}

User question: {query}"""

            response = Settings.llm.complete(prompt)
            response_text = response.text
            timings["8_llm_completion_ms"] = int((time.time() - t8) * 1000)

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
                    "node_count": len(nodes),
                    "raptor_summaries_used": len(raptor_summaries) if raptor_summaries else 0,
                    "timings": timings
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
