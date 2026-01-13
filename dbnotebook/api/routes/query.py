"""Programmatic API for RAG queries with optional conversation memory.

Provides a unified API for programmatic access:
- POST /api/query - Execute query with optional session_id for conversation memory
- GET /api/query/notebooks - List available notebooks
- GET /api/user/api-key - Get current user's API key

Conversation Memory:
- Omit session_id → stateless query (new session_id returned for optional continuation)
- Pass session_id → conversational mode (loads history, enriches context)

Designed for:
- API integrations
- Scripting and automation
- Conversational AI agents
- Multi-turn Q&A workflows

API Key Authentication:
- API keys are stored per-user in the database (users.api_key)
- Requests must include X-API-Key header matching a valid user's API key
- Environment variable API_KEY is used as fallback for backward compatibility

RBAC Integration:
- Set RBAC_STRICT_MODE=true to enforce notebook access control
- Users must have viewer access or higher to query notebooks
"""

import logging
import os
import time
from flask import request, jsonify
from functools import wraps

from llama_index.core import Settings
from llama_index.core.schema import QueryBundle

from dbnotebook.core.auth import check_notebook_access, AccessLevel
from dbnotebook.core.constants import DEFAULT_USER_ID
from dbnotebook.core.db.models import User, Conversation

logger = logging.getLogger(__name__)

# Fallback API key from environment (for backward compatibility)
ENV_API_KEY = os.getenv("API_KEY")

# Module-level reference to db_manager (set during route creation)
_db_manager = None


def validate_api_key(provided_key: str) -> tuple[bool, str | None]:
    """Validate API key against database or environment variable.

    Returns:
        Tuple of (is_valid, user_id or None)
    """
    if not provided_key:
        return False, None

    # Check database first (if db_manager is available)
    if _db_manager:
        try:
            with _db_manager.get_session() as session:
                user = session.query(User).filter(User.api_key == provided_key).first()
                if user:
                    return True, str(user.user_id)
        except Exception as e:
            logger.warning(f"Database API key lookup failed: {e}")

    # Fallback to environment variable (backward compatibility)
    if ENV_API_KEY and provided_key == ENV_API_KEY:
        return True, DEFAULT_USER_ID

    return False, None


def require_api_key(f):
    """Decorator to require API key for programmatic API access.

    Validates against:
    1. Database: users.api_key column
    2. Environment: API_KEY variable (fallback for backward compatibility)
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        provided_key = request.headers.get("X-API-Key")

        is_valid, user_id = validate_api_key(provided_key)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": "Invalid or missing API key"
            }), 401

        # Store validated user_id in request context for downstream use
        request.api_user_id = user_id
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
    # Store db_manager reference for API key validation
    global _db_manager
    _db_manager = db_manager

    @app.route("/api/query", methods=["POST"])
    @require_api_key
    def api_query():
        """
        Multi-user safe programmatic API for RAG queries with optional conversation memory.

        Thread-safe for concurrent requests. Uses default LLM model configured at startup.

        **Conversation Memory:**
        - Omit `session_id` → stateless query (new session_id returned for optional continuation)
        - Pass `session_id` → conversational mode (loads history, enriches context)

        Request JSON:
            {
                "notebook_id": "uuid",           # Required
                "query": "string",               # Required
                "session_id": "uuid",            # Optional - pass to continue conversation
                "max_history": 5,                # Optional, default: 5, max: 20 (only if session_id)
                "include_sources": true,         # Optional, default: true
                "max_sources": 6                 # Optional, default: 6, max: 20
            }

        Response JSON:
            {
                "success": true,
                "response": "LLM response text",
                "session_id": "uuid",            # Use this for follow-up queries
                "sources": [...],
                "metadata": {
                    "execution_time_ms": 850,
                    "model": "llama3.1:latest",
                    "retrieval_strategy": "hybrid",
                    "history_messages_used": 0   # >0 if session_id was provided
                }
            }
        """
        import uuid as uuid_lib
        from datetime import datetime

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

            # Session management - optional conversation memory
            session_id_input = data.get("session_id")
            use_memory = session_id_input is not None  # Only use memory if session_id provided

            if session_id_input:
                try:
                    session_id = uuid_lib.UUID(session_id_input)
                except ValueError:
                    return jsonify({
                        "success": False,
                        "error": "Invalid session_id format"
                    }), 400
            else:
                # Generate new session_id (returned for optional continuation)
                session_id = uuid_lib.uuid4()

            # Get user_id for RBAC check
            user_id = (
                request.headers.get("X-User-ID") or
                data.get("user_id") or
                getattr(request, 'api_user_id', None) or
                DEFAULT_USER_ID  # Default for backward compatibility
            )

            # RBAC: Check notebook access (only enforced if RBAC_STRICT_MODE=true)
            has_access, error_msg = check_notebook_access(
                user_id=user_id,
                notebook_id=notebook_id,
                access_level=AccessLevel.VIEWER
            )
            if not has_access:
                return jsonify({
                    "success": False,
                    "error": error_msg
                }), 403

            # Optional parameters
            include_sources = data.get("include_sources", True)
            max_sources = min(data.get("max_sources", 6), 20)  # Cap at 20
            max_history = min(data.get("max_history", 5), 20) if use_memory else 0

            logger.info(f"API query: notebook_id={notebook_id}, session_id={session_id}, use_memory={use_memory}")

            # Step 1: Verify notebook exists
            t1 = time.time()
            notebook = notebook_manager.get_notebook(notebook_id)
            timings["1_notebook_lookup_ms"] = int((time.time() - t1) * 1000)

            if not notebook:
                return jsonify({
                    "success": False,
                    "error": f"Notebook not found: {notebook_id}"
                }), 404

            # Step 1.5: Load conversation history (only if session_id was provided)
            history_messages = []
            if use_memory:
                t1b = time.time()
                with db_manager.get_session() as db_session:
                    history = db_session.query(Conversation).filter(
                        Conversation.session_id == session_id,
                        Conversation.notebook_id == notebook_id
                    ).order_by(Conversation.timestamp.desc()).limit(max_history * 2).all()

                    # Reverse to get chronological order
                    history = list(reversed(history))
                    for msg in history:
                        history_messages.append({
                            "role": msg.role,
                            "content": msg.content
                        })
                timings["1b_load_history_ms"] = int((time.time() - t1b) * 1000)
                logger.debug(f"Loaded {len(history_messages)} history messages for session {session_id}")

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
                                "filename": metadata.get("file_name", "Unknown"),
                                "snippet": node.text[:200] + "..." if len(node.text) > 200 else node.text,
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
                    # Get query embedding for similarity search
                    t6a = time.time()
                    query_embedding = Settings.embed_model.get_query_embedding(query)
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
            from dbnotebook.core.prompt import get_system_prompt, get_context_prompt

            system_prompt = get_system_prompt("eng", is_rag_prompt=True)
            context_prompt_template = get_context_prompt("eng")
            context_prompt = context_prompt_template.format(context_str=context)

            # Build conversation history section (only if use_memory and has history)
            history_section = ""
            if use_memory and history_messages:
                history_parts = []
                for msg in history_messages[-max_history * 2:]:  # Last N exchanges
                    role_label = "User" if msg["role"] == "user" else "Assistant"
                    history_parts.append(f"{role_label}: {msg['content']}")
                history_section = "\n\n## CONVERSATION HISTORY\n" + "\n\n".join(history_parts)

            prompt = f"""{system_prompt}

{context_prompt}
{history_section}

User question: {query}"""

            response = Settings.llm.complete(prompt)
            response_text = response.text
            timings["8_llm_completion_ms"] = int((time.time() - t8) * 1000)

            # Step 9: Save conversation to database (only if use_memory)
            if use_memory:
                t9 = time.time()
                with db_manager.get_session() as db_session:
                    # Save user message
                    user_msg = Conversation(
                        notebook_id=notebook_id,
                        user_id=user_id,
                        session_id=session_id,
                        role="user",
                        content=query,
                        timestamp=datetime.utcnow()
                    )
                    db_session.add(user_msg)

                    # Save assistant message
                    assistant_msg = Conversation(
                        notebook_id=notebook_id,
                        user_id=user_id,
                        session_id=session_id,
                        role="assistant",
                        content=response_text,
                        timestamp=datetime.utcnow()
                    )
                    db_session.add(assistant_msg)
                timings["9_save_history_ms"] = int((time.time() - t9) * 1000)

            execution_time_ms = int((time.time() - start_time) * 1000)

            logger.info(f"API query completed in {execution_time_ms}ms, session={session_id}, history_used={len(history_messages)}")

            return jsonify({
                "success": True,
                "response": response_text,
                "session_id": str(session_id),  # Always return for optional continuation
                "sources": sources,
                "metadata": {
                    "execution_time_ms": execution_time_ms,
                    "model": pipeline._default_model.model if pipeline._default_model else "unknown",
                    "retrieval_strategy": retrieval_strategy,
                    "node_count": len(nodes),
                    "history_messages_used": len(history_messages),
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
            user_id = request.args.get("user_id", DEFAULT_USER_ID)
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

    @app.route("/api/user/api-key", methods=["GET"])
    def api_get_user_api_key():
        """
        Get the API key for a user.

        Query params:
            user_id: UUID (optional, defaults to DEFAULT_USER_ID)

        Response JSON:
            {
                "success": true,
                "api_key": "user-api-key-string",
                "user_id": "uuid"
            }

        Note: This endpoint is intended for frontend use to display/copy
        the user's API key for programmatic access.
        """
        try:
            user_id = request.args.get("user_id", DEFAULT_USER_ID)

            with db_manager.get_session() as session:
                user = session.query(User).filter(User.user_id == user_id).first()

                if not user:
                    return jsonify({
                        "success": False,
                        "error": f"User not found: {user_id}"
                    }), 404

                return jsonify({
                    "success": True,
                    "api_key": user.api_key,
                    "user_id": str(user.user_id)
                })

        except Exception as e:
            logger.error(f"Error getting user API key: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    return app
