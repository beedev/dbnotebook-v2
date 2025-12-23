"""Web Content API routes for search and scraping."""

import logging
from flask import Blueprint, request, jsonify
from llama_index.core import Settings

from ...core.ingestion import WebContentIngestion

logger = logging.getLogger(__name__)


def create_web_content_routes(app, web_ingestion: WebContentIngestion, pipeline):
    """Create web content API routes.

    Args:
        app: Flask application instance
        web_ingestion: WebContentIngestion service instance
        pipeline: LocalRAGPipeline instance for embedding
    """

    @app.route("/api/web/search", methods=["POST"])
    def web_search():
        """
        Search the web for content.

        Request JSON:
            {
                "query": "search term",
                "num_results": 5
            }

        Response JSON:
            {
                "success": true,
                "results": [
                    {
                        "url": "https://...",
                        "title": "Page Title",
                        "description": "Page description...",
                        "score": 0.95
                    }
                ]
            }
        """
        try:
            data = request.json or {}
            query = data.get("query")

            if not query:
                return jsonify({
                    "success": False,
                    "error": "Query is required"
                }), 400

            num_results = min(max(data.get("num_results", 5), 1), 20)

            results = web_ingestion.search(query, num_results=num_results)

            return jsonify({
                "success": True,
                "results": results,
                "query": query
            })

        except RuntimeError as e:
            logger.error(f"Web search failed: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 503
        except Exception as e:
            logger.error(f"Error in web search: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/web/scrape-preview", methods=["POST"])
    def web_scrape_preview():
        """
        Get a preview of web page content.

        Request JSON:
            {
                "url": "https://..."
            }

        Response JSON:
            {
                "success": true,
                "url": "https://...",
                "title": "Page Title",
                "content_preview": "First 500 chars...",
                "word_count": 1234
            }
        """
        try:
            data = request.json or {}
            url = data.get("url")

            if not url:
                return jsonify({
                    "success": False,
                    "error": "URL is required"
                }), 400

            max_chars = min(max(data.get("max_chars", 500), 100), 2000)
            preview = web_ingestion.preview_url(url, max_chars=max_chars)

            return jsonify({
                "success": True,
                **preview
            })

        except RuntimeError as e:
            logger.error(f"Web scrape preview failed: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 503
        except Exception as e:
            logger.error(f"Error in web scrape preview: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/notebooks/<notebook_id>/web-sources", methods=["POST"])
    def add_web_sources(notebook_id):
        """
        Add web sources to a notebook after user confirmation.

        Request JSON:
            {
                "urls": ["https://...", "https://..."],
                "source_name": "optional search query for naming"
            }

        Response JSON:
            {
                "success": true,
                "sources_added": [
                    {
                        "source_id": "uuid",
                        "url": "https://...",
                        "title": "Page Title",
                        "chunk_count": 12
                    }
                ]
            }
        """
        try:
            data = request.json or {}
            urls = data.get("urls", [])
            source_name = data.get("source_name")  # Search query for naming

            if not urls:
                return jsonify({
                    "success": False,
                    "error": "At least one URL is required"
                }), 400

            if not isinstance(urls, list):
                urls = [urls]

            # Limit to 10 URLs at a time
            urls = urls[:10]

            # Ingest URLs to notebook with source_name for document naming
            ingested = web_ingestion.ingest_urls_to_notebook(
                notebook_id, urls, source_name=source_name
            )

            # Process embeddings for each ingested source
            for source in ingested:
                nodes = source.pop("nodes", [])
                if nodes and pipeline and hasattr(pipeline, "_vector_store"):
                    try:
                        # Generate embeddings using the configured embed model
                        embed_model = Settings.embed_model
                        if embed_model:
                            # Add notebook_id to node metadata before embedding
                            for node in nodes:
                                if hasattr(node, 'metadata'):
                                    node.metadata["notebook_id"] = notebook_id

                            # Generate embeddings for all nodes
                            texts = [node.get_content() for node in nodes]
                            embeddings = embed_model.get_text_embedding_batch(texts)

                            # Set embeddings on nodes
                            for node, embedding in zip(nodes, embeddings):
                                node.embedding = embedding

                            # Add embedded nodes to vector store
                            added = pipeline._vector_store.add_nodes(nodes, notebook_id=notebook_id)
                            logger.info(f"Added {added} embeddings for {source['url']}")
                        else:
                            logger.error("No embedding model configured")
                    except Exception as e:
                        logger.error(f"Failed to add embeddings: {e}")
                        import traceback
                        logger.error(traceback.format_exc())

            return jsonify({
                "success": True,
                "sources_added": ingested,
                "total_added": len(ingested)
            })

        except ValueError as e:
            # Duplicate content or other validation error
            logger.warning(f"Web source validation error: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 400
        except RuntimeError as e:
            logger.error(f"Web ingestion failed: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 503
        except Exception as e:
            logger.error(f"Error adding web sources: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/web/providers", methods=["GET"])
    def web_provider_info():
        """
        Get information about available web content providers.

        Response JSON:
            {
                "success": true,
                "search": {
                    "name": "firecrawl",
                    "available": true,
                    ...
                },
                "scraper": {
                    "name": "jina_reader",
                    "available": true,
                    ...
                }
            }
        """
        try:
            info = web_ingestion.get_provider_info()
            return jsonify({
                "success": True,
                **info
            })
        except Exception as e:
            logger.error(f"Error getting provider info: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    return app
