"""V2 Chat API with stateless fast pattern and conversation memory.

This endpoint combines the speed of /api/query with conversation continuity.
Multi-user safe, thread-safe, supports 50-100 concurrent users.

Endpoint: POST /api/v2/chat
"""

import logging
import time
from flask import request, jsonify, Response

from llama_index.core import Settings

from dbnotebook.core.stateless import (
    fast_retrieve,
    get_raptor_summaries,
    build_context_with_history,
    format_sources,
    execute_query,
    execute_query_streaming,
    load_conversation_history,
    save_conversation_turn,
    generate_session_id,
)

logger = logging.getLogger(__name__)

# Note: V2 browser-facing endpoints don't require API key authentication.
# Use /api/query with X-API-Key header for programmatic API access.


def create_chat_v2_routes(app, pipeline, db_manager, notebook_manager, conversation_store):
    """Create V2 chat API routes with fast pattern and memory.

    Args:
        app: Flask application instance
        pipeline: LocalRAGPipeline instance
        db_manager: DatabaseManager instance
        notebook_manager: NotebookManager instance
        conversation_store: ConversationStore instance for memory
    """

    @app.route("/api/v2/chat", methods=["POST"])
    def api_v2_chat():
        """
        V2 Chat API with stateless fast pattern and conversation memory.

        Multi-user safe, thread-safe, uses the fast API pattern with
        database-backed conversation memory for continuity.

        Request JSON:
            {
                "notebook_id": "uuid",           # Required
                "query": "string",               # Required
                "user_id": "uuid",               # Required for multi-user
                "session_id": "uuid",            # Optional - for conversation continuity
                "include_history": true,         # Optional, default: true
                "max_history": 10,               # Optional, default: 10
                "include_sources": true,         # Optional, default: true
                "max_sources": 6                 # Optional, default: 6, max: 20
            }

        Response JSON:
            {
                "success": true,
                "response": "LLM response text",
                "session_id": "uuid",
                "sources": [...],
                "metadata": {
                    "execution_time_ms": 850,
                    "model": "gpt-4.1-nano",
                    "history_turns_used": 5,
                    "timings": {...}
                }
            }
        """
        start_time = time.time()
        timings = {}

        try:
            data = request.json or {}

            # Validate required fields
            notebook_id = data.get("notebook_id")
            query = data.get("query")
            user_id = data.get("user_id")

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

            if not user_id:
                return jsonify({
                    "success": False,
                    "error": "user_id is required for multi-user chat"
                }), 400

            # Optional parameters
            model_name = data.get("model")
            session_id = data.get("session_id") or generate_session_id()
            include_history = data.get("include_history", True)
            max_history = min(data.get("max_history", 10), 50)
            include_sources = data.get("include_sources", True)
            max_sources = min(data.get("max_sources", 6), 20)

            # Get LLM instance for this specific request
            from dbnotebook.core.model.model import LocalRAGModel
            local_llm = LocalRAGModel.set(model_name) if model_name else Settings.llm

            used_model = local_llm.model if hasattr(local_llm, 'model') else "unknown"
            logger.info(f"V2 chat: notebook_id={notebook_id}, user_id={user_id}, session_id={session_id}, model={used_model} (requested={model_name})")

            # Step 1: Verify notebook exists
            t1 = time.time()
            notebook = notebook_manager.get_notebook(notebook_id)
            timings["1_notebook_lookup_ms"] = int((time.time() - t1) * 1000)

            if not notebook:
                return jsonify({
                    "success": False,
                    "error": f"Notebook not found: {notebook_id}"
                }), 404

            # Step 2: Load conversation history (from database)
            t2 = time.time()
            conversation_history = []
            if include_history:
                conversation_history = load_conversation_history(
                    conversation_store=conversation_store,
                    notebook_id=notebook_id,
                    user_id=user_id,
                    max_history=max_history,
                )
            timings["2_load_history_ms"] = int((time.time() - t2) * 1000)

            # Step 3: Get cached nodes (thread-safe)
            t3 = time.time()
            nodes = pipeline._get_cached_nodes(notebook_id)
            timings["3_node_cache_ms"] = int((time.time() - t3) * 1000)
            logger.debug(f"Got {len(nodes)} cached nodes for notebook {notebook_id}")

            # Step 4: Fast retrieval (using stateless pattern)
            retrieval_results = []
            retrieval_strategy = "hybrid"
            if nodes:
                try:
                    if not pipeline._engine or not pipeline._engine._retriever:
                        return jsonify({
                            "success": False,
                            "error": "Pipeline not initialized. Please try again."
                        }), 503

                    t4 = time.time()
                    retrieval_results = fast_retrieve(
                        nodes=nodes,
                        query=query,
                        notebook_id=notebook_id,
                        vector_store=pipeline._vector_store,
                        retriever_factory=pipeline._engine._retriever,
                        llm=local_llm,
                        top_k=max_sources,
                    )
                    timings["4_fast_retrieval_ms"] = int((time.time() - t4) * 1000)
                    retrieval_strategy = "combined_raptor"

                except Exception as e:
                    logger.warning(f"Retrieval failed [{type(e).__name__}]: {e}", exc_info=True)

            # Step 5: Get RAPTOR summaries
            t5 = time.time()
            raptor_summaries = get_raptor_summaries(
                query=query,
                notebook_id=notebook_id,
                vector_store=pipeline._vector_store,
                embed_model=Settings.embed_model,
                top_k=5,
            )
            timings["5_raptor_summaries_ms"] = int((time.time() - t5) * 1000)

            # Step 6: Build context with history
            t6 = time.time()
            context = build_context_with_history(
                retrieval_results=retrieval_results,
                raptor_summaries=raptor_summaries,
                conversation_history=conversation_history,
                max_history=max_history,
                max_summaries=3,
                max_chunks=max_sources,
            )
            timings["6_context_building_ms"] = int((time.time() - t6) * 1000)

            # Step 7: Execute query (stateless LLM call)
            t7 = time.time()
            response_text = execute_query(
                query=query,
                context=context,
                llm=local_llm,
            )
            timings["7_llm_completion_ms"] = int((time.time() - t7) * 1000)

            # Step 8: Save conversation turn to database
            t8 = time.time()
            save_conversation_turn(
                conversation_store=conversation_store,
                notebook_id=notebook_id,
                user_id=user_id,
                user_message=query,
                assistant_response=response_text,
            )
            timings["8_save_history_ms"] = int((time.time() - t8) * 1000)

            # Step 9: Format sources
            sources = []
            if include_sources:
                sources = format_sources(
                    retrieval_results=retrieval_results,
                    max_sources=max_sources,
                )

            execution_time_ms = int((time.time() - start_time) * 1000)

            logger.info(f"V2 chat completed in {execution_time_ms}ms, {len(sources)} sources, {len(conversation_history)} history turns")

            return jsonify({
                "success": True,
                "response": response_text,
                "session_id": session_id,
                "sources": sources,
                "metadata": {
                    "execution_time_ms": execution_time_ms,
                    "model": local_llm.model if hasattr(local_llm, 'model') else (pipeline._default_model.model if pipeline._default_model else "unknown"),
                    "retrieval_strategy": retrieval_strategy,
                    "node_count": len(nodes),
                    "raptor_summaries_used": len(raptor_summaries) if raptor_summaries else 0,
                    "history_turns_used": len(conversation_history) // 2,
                    "timings": timings,
                }
            })

        except Exception as e:
            logger.error(f"Error in V2 chat endpoint: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/v2/chat/stream", methods=["POST"])
    def api_v2_chat_stream():
        """
        V2 Chat API with streaming response.

        Same as /api/v2/chat but returns Server-Sent Events (SSE) stream.
        """
        try:
            data = request.json or {}

            # Validate required fields
            notebook_id = data.get("notebook_id")
            query = data.get("query")
            user_id = data.get("user_id")

            if not notebook_id or not query or not user_id:
                return jsonify({
                    "success": False,
                    "error": "notebook_id, query, and user_id are required"
                }), 400

            # Optional parameters
            model_name = data.get("model")
            session_id = data.get("session_id") or generate_session_id()
            include_history = data.get("include_history", True)
            max_history = min(data.get("max_history", 10), 50)
            max_sources = min(data.get("max_sources", 6), 20)

            # Get LLM instance for this specific request
            from dbnotebook.core.model.model import LocalRAGModel
            local_llm = LocalRAGModel.set(model_name) if model_name else Settings.llm

            used_model = local_llm.model if hasattr(local_llm, 'model') else "unknown"
            logger.info(f"V2 chat stream: notebook_id={notebook_id}, model={used_model} (requested={model_name})")

            # Verify notebook
            notebook = notebook_manager.get_notebook(notebook_id)
            if not notebook:
                return jsonify({
                    "success": False,
                    "error": f"Notebook not found: {notebook_id}"
                }), 404

            def generate():
                import json
                import time as time_module
                response_text = ""
                start_time = time_module.time()
                timings = {}

                try:
                    # Load history
                    t1 = time_module.time()
                    conversation_history = []
                    if include_history:
                        conversation_history = load_conversation_history(
                            conversation_store=conversation_store,
                            notebook_id=notebook_id,
                            user_id=user_id,
                            max_history=max_history,
                        )
                    timings["1_load_history_ms"] = int((time_module.time() - t1) * 1000)

                    # Get nodes and retrieve
                    t2 = time_module.time()
                    nodes = pipeline._get_cached_nodes(notebook_id)
                    timings["2_node_cache_ms"] = int((time_module.time() - t2) * 1000)

                    retrieval_results = []
                    if nodes and pipeline._engine and pipeline._engine._retriever:
                        t3 = time_module.time()
                        retrieval_results = fast_retrieve(
                            nodes=nodes,
                            query=query,
                            notebook_id=notebook_id,
                            vector_store=pipeline._vector_store,
                            retriever_factory=pipeline._engine._retriever,
                            llm=local_llm,
                            top_k=max_sources,
                        )
                        timings["3_retrieval_ms"] = int((time_module.time() - t3) * 1000)

                    # Get RAPTOR summaries
                    t4 = time_module.time()
                    raptor_summaries = get_raptor_summaries(
                        query=query,
                        notebook_id=notebook_id,
                        vector_store=pipeline._vector_store,
                        embed_model=Settings.embed_model,
                    )
                    timings["4_raptor_ms"] = int((time_module.time() - t4) * 1000)

                    # Build context
                    t5 = time_module.time()
                    context = build_context_with_history(
                        retrieval_results=retrieval_results,
                        raptor_summaries=raptor_summaries,
                        conversation_history=conversation_history,
                        max_history=max_history,
                    )
                    timings["5_context_ms"] = int((time_module.time() - t5) * 1000)

                    # Send sources first
                    sources = format_sources(retrieval_results, max_sources)
                    yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

                    # Stream response
                    t6 = time_module.time()
                    for chunk in execute_query_streaming(query, context, local_llm):
                        response_text += chunk
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                    timings["6_llm_stream_ms"] = int((time_module.time() - t6) * 1000)

                    # Save conversation after streaming completes
                    t7 = time_module.time()
                    save_conversation_turn(
                        conversation_store=conversation_store,
                        notebook_id=notebook_id,
                        user_id=user_id,
                        user_message=query,
                        assistant_response=response_text,
                    )
                    timings["7_save_history_ms"] = int((time_module.time() - t7) * 1000)

                    # Calculate total execution time
                    execution_time_ms = int((time_module.time() - start_time) * 1000)

                    # Build metadata
                    metadata = {
                        "execution_time_ms": execution_time_ms,
                        "model": local_llm.model if hasattr(local_llm, 'model') else (pipeline._default_model.model if pipeline._default_model else "unknown"),
                        "node_count": len(nodes) if nodes else 0,
                        "raptor_summaries_used": len(raptor_summaries) if raptor_summaries else 0,
                        "history_turns_used": len(conversation_history) // 2,
                        "timings": timings,
                    }

                    # Send completion signal with metadata
                    yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'metadata': metadata})}\n\n"

                except Exception as e:
                    logger.error(f"Streaming error: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

            return Response(
                generate(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no',
                }
            )

        except Exception as e:
            logger.error(f"Error in V2 chat stream endpoint: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/v2/chat/history", methods=["GET"])
    def api_v2_chat_history():
        """
        Get conversation history for a notebook.

        Query params:
            notebook_id: UUID (required)
            user_id: UUID (required)
            limit: int (optional, default: 50)
        """
        try:
            notebook_id = request.args.get("notebook_id")
            user_id = request.args.get("user_id")
            limit = min(int(request.args.get("limit", 50)), 200)

            if not notebook_id or not user_id:
                return jsonify({
                    "success": False,
                    "error": "notebook_id and user_id are required"
                }), 400

            history = load_conversation_history(
                conversation_store=conversation_store,
                notebook_id=notebook_id,
                user_id=user_id,
                max_history=limit,
            )

            return jsonify({
                "success": True,
                "history": history,
                "count": len(history),
            })

        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/v2/chat/history", methods=["DELETE"])
    def api_v2_clear_chat_history():
        """
        Clear conversation history for a notebook.

        Request JSON:
            {
                "notebook_id": "uuid",
                "user_id": "uuid"
            }
        """
        try:
            data = request.json or {}
            notebook_id = data.get("notebook_id")
            user_id = data.get("user_id")

            if not notebook_id:
                return jsonify({
                    "success": False,
                    "error": "notebook_id is required"
                }), 400

            # Clear notebook history (for this user or all if user_id not provided)
            cleared = conversation_store.clear_notebook_history(notebook_id)

            return jsonify({
                "success": True,
                "cleared": cleared,
            })

        except Exception as e:
            logger.error(f"Error clearing chat history: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    return app
