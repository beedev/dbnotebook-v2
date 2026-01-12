"""Chat API routes for RAG chatbot.

Includes two-stage LLM document routing for intelligent retrieval:
- Stage 1: Analyze query against document summaries to determine routing strategy
- Stage 2: Execute retrieval based on routing decision (if needed)
"""

import logging
import time
from flask import Blueprint, request, jsonify
from llama_index.core.llms import ChatMessage
from llama_index.core import Settings

from ...core.services import DocumentRoutingService
from ...core.interfaces import RoutingStrategy

logger = logging.getLogger(__name__)


def create_chat_routes(app, pipeline, db_manager=None):
    """Create chat-related API routes.

    Args:
        app: Flask application instance
        pipeline: LocalRAGPipeline instance
        db_manager: DatabaseManager instance for routing service
    """
    # Initialize routing service if db_manager is available
    routing_service = None
    if db_manager and pipeline:
        routing_service = DocumentRoutingService(
            pipeline=pipeline,
            db_manager=db_manager
        )
        logger.info("DocumentRoutingService initialized for two-stage routing")

    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        """
        Send chat message and get response with source attribution.

        Request JSON:
            {
                "message": "User query",
                "notebook_ids": ["uuid1", "uuid2"],  # Optional list of notebook UUIDs
                "mode": "chat|QA",
                "stream": false
            }

        Response JSON:
            {
                "success": true,
                "response": "LLM response text",
                "sources": [
                    {
                        "document_name": "paper1.pdf",
                        "chunk_location": "Chunk 5",
                        "relevance_score": 0.92,
                        "excerpt": "First 200 chars of chunk...",
                        "notebook_id": "notebook-uuid",
                        "source_id": "source-uuid"
                    }
                ],
                "notebook_ids": ["uuid1", "uuid2"],
                "retrieval_strategy": "hybrid"
            }
        """
        start_time = time.time()
        timings = {}  # Track per-stage timing

        try:
            data = request.json

            # Validate required fields
            message = data.get("message")
            if not message:
                return jsonify({
                    "success": False,
                    "error": "Message is required"
                }), 400

            # Support both singular notebook_id and plural notebook_ids
            notebook_ids = data.get("notebook_ids", [])
            if not notebook_ids and data.get("notebook_id"):
                notebook_ids = [data.get("notebook_id")]

            mode = data.get("mode", "chat")
            stream = data.get("stream", False)

            logger.info(f"Chat request: mode={mode}, notebook_ids={notebook_ids}, stream={stream}")

            # Configure pipeline settings
            pipeline.set_language(pipeline._language)
            pipeline.set_model()

            # =========================================================================
            # Stage 1: Two-Stage LLM Document Routing
            # =========================================================================
            routing_result = None
            selected_notebook_ids = notebook_ids  # Default to all requested notebooks

            if routing_service and notebook_ids and len(notebook_ids) == 1:
                # Use routing service for single-notebook queries
                try:
                    t1 = time.time()
                    notebook_id = notebook_ids[0]
                    routing_result = routing_service.route_query(
                        query=message,
                        notebook_id=notebook_id
                    )
                    timings["1_routing_analysis_ms"] = int((time.time() - t1) * 1000)

                    logger.info(
                        f"Routing decision: strategy={routing_result.strategy.value}, "
                        f"selected_docs={len(routing_result.selected_document_ids)}, "
                        f"confidence={routing_result.confidence}"
                    )

                    # Handle DIRECT_SYNTHESIS - return immediately without retrieval
                    if routing_result.strategy == RoutingStrategy.DIRECT_SYNTHESIS:
                        logger.info("Using DIRECT_SYNTHESIS - returning synthesized response")
                        execution_time_ms = int((time.time() - start_time) * 1000)
                        return jsonify({
                            "success": True,
                            "response": routing_result.direct_response,
                            "sources": [],  # No sources for direct synthesis
                            "notebook_ids": notebook_ids,
                            "retrieval_strategy": "direct_synthesis",
                            "routing": {
                                "strategy": routing_result.strategy.value,
                                "reasoning": routing_result.reasoning,
                                "confidence": routing_result.confidence
                            },
                            "metadata": {
                                "execution_time_ms": execution_time_ms,
                                "timings": timings
                            }
                        })

                    # For DEEP_DIVE or MULTI_DOC_ANALYSIS, we'll filter retrieval
                    # to the selected documents in Stage 2

                except Exception as e:
                    logger.warning(f"Routing failed, falling back to standard retrieval: {e}")
                    routing_result = None

            # =========================================================================
            # Stage 2: Focused Retrieval (if routing didn't return direct synthesis)
            # =========================================================================

            # Initialize chat engine WITH notebook filter so it uses the right documents
            # This is critical - set_engine() loads nodes from the specified notebooks
            t2 = time.time()
            if notebook_ids:
                pipeline.set_engine(offering_filter=notebook_ids, force_reset=True)
                logger.info(f"Engine configured with notebook filter: {notebook_ids}")
            else:
                pipeline.set_engine(force_reset=True)
                logger.info("Engine configured without notebook filter")
            timings["2_notebook_switch_ms"] = int((time.time() - t2) * 1000)

            # Get nodes from cache for source attribution (uses pipeline's node cache)
            t3 = time.time()
            nodes = []
            if notebook_ids and hasattr(pipeline, '_get_cached_nodes'):
                for nb_id in notebook_ids:
                    nb_nodes = pipeline._get_cached_nodes(nb_id)
                    nodes.extend(nb_nodes)
                logger.debug(f"Got {len(nodes)} cached nodes for source attribution")

                # Filter nodes to selected documents if routing provided specific docs
                if routing_result and routing_result.selected_document_ids:
                    selected_source_ids = set(routing_result.selected_document_ids)
                    original_count = len(nodes)
                    nodes = [
                        n for n in nodes
                        if n.metadata.get("source_id") in selected_source_ids
                    ]
                    logger.info(
                        f"Filtered nodes from {original_count} to {len(nodes)} "
                        f"based on routing selection: {selected_source_ids}"
                    )
            timings["3_node_cache_ms"] = int((time.time() - t3) * 1000)

            # Perform retrieval to get source metadata BEFORE chat response
            sources = []
            retrieval_strategy = "hybrid"

            if nodes and notebook_ids:
                try:
                    # Get retriever configured for these notebooks (uses retriever cache)
                    t4 = time.time()
                    retriever = pipeline._engine._retriever.get_retrievers(
                        llm=Settings.llm,
                        language="eng",
                        nodes=nodes,
                        offering_filter=notebook_ids,  # offering_filter actually filters by notebook_id!
                        vector_store=pipeline._vector_store,
                        notebook_id=notebook_ids[0] if len(notebook_ids) == 1 else None  # Cache for single notebook
                    )
                    timings["4_retriever_creation_ms"] = int((time.time() - t4) * 1000)

                    # Retrieve relevant chunks with scores
                    t5 = time.time()
                    from llama_index.core.schema import QueryBundle
                    query_bundle = QueryBundle(query_str=message)
                    retrieval_results = retriever.retrieve(query_bundle)
                    timings["5_chunk_retrieval_ms"] = int((time.time() - t5) * 1000)

                    logger.info(f"Retrieved {len(retrieval_results)} chunks for source attribution")

                    # Format sources from retrieval results
                    t6 = time.time()
                    for idx, node_with_score in enumerate(retrieval_results[:6], 1):  # Top 6 sources
                        node = node_with_score.node
                        metadata = node.metadata or {}

                        # Extract location info from metadata
                        chunk_location = f"Chunk {idx}"
                        if "page" in metadata:
                            chunk_location = f"Page {metadata['page']}"
                        elif "section" in metadata:
                            chunk_location = metadata["section"]

                        sources.append({
                            "document_name": metadata.get("file_name", "Unknown"),
                            "chunk_location": chunk_location,
                            "relevance_score": round(node_with_score.score or 0.0, 2),
                            "excerpt": node.text[:200] + "..." if len(node.text) > 200 else node.text,
                            "notebook_id": metadata.get("notebook_id", ""),
                            "source_id": metadata.get("source_id", "")
                        })
                    timings["6_source_formatting_ms"] = int((time.time() - t6) * 1000)

                    retrieval_strategy = retriever.__class__.__name__.replace("Retriever", "").lower()

                    # Add routing info to strategy name if routing was used
                    if routing_result:
                        retrieval_strategy = f"{routing_result.strategy.value}+{retrieval_strategy}"

                except Exception as e:
                    logger.warning(f"Could not extract sources: {e}")
                    # Continue without sources rather than failing the entire request

            # Create chat history with user message
            chat_history = [
                ChatMessage(role="user", content=message)
            ]

            # Get response from pipeline
            if stream:
                # TODO: Implement streaming response
                return jsonify({
                    "success": False,
                    "error": "Streaming not yet implemented"
                }), 501
            else:
                # Non-streaming response - collect all chunks from streaming response
                # Convert chat_history from ChatMessage objects to list[list[str]] format
                chatbot_history = []
                for msg in chat_history:
                    chatbot_history.append([msg.content, ""])  # [user_msg, assistant_msg]

                # Call pipeline.query() which returns StreamingAgentChatResponse
                t7 = time.time()
                streaming_response = pipeline.query(
                    mode=mode,
                    message=message,
                    chatbot=chatbot_history
                )

                # Collect all response chunks into a single string
                response_text = ""
                for chunk in streaming_response.response_gen:
                    response_text += chunk
                timings["7_llm_completion_ms"] = int((time.time() - t7) * 1000)

                logger.debug(f"Chat response received: {response_text[:100]}...")
                logger.info(f"Returning response with {len(sources)} sources")

                execution_time_ms = int((time.time() - start_time) * 1000)

                response_data = {
                    "success": True,
                    "response": response_text,
                    "sources": sources,
                    "notebook_ids": notebook_ids,
                    "retrieval_strategy": retrieval_strategy,
                    "metadata": {
                        "execution_time_ms": execution_time_ms,
                        "node_count": len(nodes),
                        "timings": timings
                    }
                }

                # Add routing metadata if routing was used
                if routing_result:
                    response_data["routing"] = {
                        "strategy": routing_result.strategy.value,
                        "reasoning": routing_result.reasoning,
                        "confidence": routing_result.confidence,
                        "selected_documents": routing_result.selected_document_ids
                    }

                return jsonify(response_data)

        except Exception as e:
            logger.error(f"Error in chat endpoint: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    return app
