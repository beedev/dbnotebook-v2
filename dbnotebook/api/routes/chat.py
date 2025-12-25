"""Chat API routes for RAG chatbot."""

import logging
from flask import Blueprint, request, jsonify
from llama_index.core.llms import ChatMessage
from llama_index.core import Settings

logger = logging.getLogger(__name__)


def create_chat_routes(app, pipeline):
    """Create chat-related API routes.

    Args:
        app: Flask application instance
        pipeline: LocalRAGPipeline instance
    """

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

            # Initialize chat engine WITH notebook filter so it uses the right documents
            # This is critical - set_engine() loads nodes from the specified notebooks
            if notebook_ids:
                pipeline.set_engine(offering_filter=notebook_ids, force_reset=True)
                logger.info(f"Engine configured with notebook filter: {notebook_ids}")
            else:
                pipeline.set_engine(force_reset=True)
                logger.info("Engine configured without notebook filter")

            # Get fresh nodes from database for source attribution
            nodes = []
            if notebook_ids and hasattr(pipeline, '_vector_store') and pipeline._vector_store:
                for nb_id in notebook_ids:
                    nb_nodes = pipeline._vector_store.get_nodes_by_notebook_sql(nb_id)
                    nodes.extend(nb_nodes)
                logger.info(f"Retrieved {len(nodes)} nodes for source attribution")

            # Perform retrieval to get source metadata BEFORE chat response
            sources = []
            retrieval_strategy = "hybrid"

            if nodes and notebook_ids:
                try:
                    # Get retriever configured for these notebooks
                    retriever = pipeline._engine._retriever.get_retrievers(
                        llm=Settings.llm,
                        language="eng",
                        nodes=nodes,
                        offering_filter=notebook_ids,  # offering_filter actually filters by notebook_id!
                        vector_store=pipeline._vector_store
                    )

                    # Retrieve relevant chunks with scores
                    from llama_index.core.schema import QueryBundle
                    query_bundle = QueryBundle(query_str=message)
                    retrieval_results = retriever.retrieve(query_bundle)

                    logger.info(f"Retrieved {len(retrieval_results)} chunks for source attribution")

                    # Format sources from retrieval results
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

                    retrieval_strategy = retriever.__class__.__name__.replace("Retriever", "").lower()

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
                streaming_response = pipeline.query(
                    mode=mode,
                    message=message,
                    chatbot=chatbot_history
                )

                # Collect all response chunks into a single string
                response_text = ""
                for chunk in streaming_response.response_gen:
                    response_text += chunk

                logger.debug(f"Chat response received: {response_text[:100]}...")
                logger.info(f"Returning response with {len(sources)} sources")

                return jsonify({
                    "success": True,
                    "response": response_text,
                    "sources": sources,
                    "notebook_ids": notebook_ids,
                    "retrieval_strategy": retrieval_strategy
                })

        except Exception as e:
            logger.error(f"Error in chat endpoint: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    return app
