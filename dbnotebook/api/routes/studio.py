"""Content Studio API routes."""

import logging
import os
from flask import request, jsonify, send_file
from pathlib import Path

from ...core.studio import StudioManager, InfographicGenerator, MindMapGenerator
from ...core.ingestion import SynopsisManager

logger = logging.getLogger(__name__)

# Project root directory for resolving relative paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def create_studio_routes(
    app,
    studio_manager: StudioManager,
    synopsis_manager: SynopsisManager = None,
):
    """Create Content Studio API routes.

    Args:
        app: Flask application instance
        studio_manager: StudioManager instance
        synopsis_manager: SynopsisManager for getting notebook content
    """

    # Initialize generators
    generators = {}
    try:
        generators["infographic"] = InfographicGenerator()
        generators["mindmap"] = MindMapGenerator()
        logger.info("Content Studio generators initialized")
    except Exception as e:
        logger.warning(f"Some generators not available: {e}")

    @app.route("/api/studio/gallery", methods=["GET"])
    def get_gallery():
        """
        Get gallery of generated content.

        Query params:
            type: Optional content type filter
            notebook_id: Optional notebook filter
            limit: Max results (default 50)
            offset: Pagination offset

        Response JSON:
            {
                "success": true,
                "items": [
                    {
                        "content_id": "uuid",
                        "content_type": "infographic",
                        "title": "...",
                        "thumbnail_url": "/api/studio/content/uuid/thumbnail",
                        "created_at": "2024-01-01T00:00:00"
                    }
                ],
                "total": 10
            }
        """
        try:
            # Get default user ID for now
            user_id = "00000000-0000-0000-0000-000000000001"

            content_type = request.args.get("type")
            notebook_id = request.args.get("notebook_id")
            limit = min(int(request.args.get("limit", 50)), 100)
            offset = int(request.args.get("offset", 0))

            items = studio_manager.list_gallery(
                user_id=user_id,
                content_type=content_type,
                notebook_id=notebook_id,
                limit=limit,
                offset=offset,
            )

            # Add thumbnail URLs
            for item in items:
                item["thumbnail_url"] = f"/api/studio/content/{item['content_id']}/thumbnail"
                item["file_url"] = f"/api/studio/content/{item['content_id']}/file"

            return jsonify({
                "success": True,
                "items": items,
                "total": len(items),
            })

        except Exception as e:
            logger.error(f"Error getting gallery: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/studio/generate", methods=["POST"])
    def generate_content():
        """
        Generate new content from a notebook.

        Request JSON:
            {
                "notebook_id": "uuid",
                "type": "infographic" | "mindmap",
                "prompt": "Optional additional instructions",
                "aspect_ratio": "16:9" (optional)
            }

        Response JSON:
            {
                "success": true,
                "content": {
                    "content_id": "uuid",
                    "content_type": "infographic",
                    "title": "...",
                    "file_url": "..."
                }
            }
        """
        try:
            data = request.json or {}
            notebook_id = data.get("notebook_id")
            content_type = data.get("type", "infographic")
            prompt = data.get("prompt")
            aspect_ratio = data.get("aspect_ratio")

            if not notebook_id:
                return jsonify({
                    "success": False,
                    "error": "notebook_id is required"
                }), 400

            if content_type not in generators:
                return jsonify({
                    "success": False,
                    "error": f"Unknown content type: {content_type}. Available: {list(generators.keys())}"
                }), 400

            generator = generators[content_type]

            if not generator.validate():
                return jsonify({
                    "success": False,
                    "error": f"Generator {content_type} is not available. Check API keys."
                }), 503

            # Get notebook content
            content = ""
            if synopsis_manager:
                try:
                    synopsis = synopsis_manager.get_synopsis(notebook_id)
                    content = synopsis.get("synopsis", "") if synopsis else ""
                except Exception as e:
                    logger.warning(f"Could not get synopsis: {e}")

            if not content:
                content = f"Generate a {content_type} about the notebook content."

            # Generate the content
            kwargs = {}
            if aspect_ratio:
                kwargs["aspect_ratio"] = aspect_ratio

            result = generator.generate(
                content=content,
                prompt=prompt,
                **kwargs
            )

            # Get default user ID
            user_id = "00000000-0000-0000-0000-000000000001"

            # Save to database
            created = studio_manager.create_content(
                user_id=user_id,
                content_type=content_type,
                title=result["title"],
                file_path=result["file_path"],
                prompt_used=prompt,
                source_notebook_id=notebook_id,
                thumbnail_path=result.get("thumbnail_path"),
                metadata=result.get("metadata"),
            )

            # Add URLs
            created["file_url"] = f"/api/studio/content/{created['content_id']}/file"
            created["thumbnail_url"] = f"/api/studio/content/{created['content_id']}/thumbnail"

            return jsonify({
                "success": True,
                "content": created,
            })

        except RuntimeError as e:
            logger.error(f"Generation failed: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 503
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/studio/content/<content_id>", methods=["GET"])
    def get_content(content_id):
        """
        Get content details.

        Response JSON:
            {
                "success": true,
                "content": {
                    "content_id": "uuid",
                    "content_type": "infographic",
                    "title": "...",
                    "file_url": "...",
                    "metadata": {...}
                }
            }
        """
        try:
            content = studio_manager.get_content(content_id)

            if not content:
                return jsonify({
                    "success": False,
                    "error": "Content not found"
                }), 404

            # Add URLs
            content["file_url"] = f"/api/studio/content/{content_id}/file"
            content["thumbnail_url"] = f"/api/studio/content/{content_id}/thumbnail"

            return jsonify({
                "success": True,
                "content": content,
            })

        except Exception as e:
            logger.error(f"Error getting content: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/studio/content/<content_id>/file", methods=["GET"])
    def get_content_file(content_id):
        """Serve the generated content file."""
        try:
            content = studio_manager.get_content(content_id)

            if not content:
                return jsonify({
                    "success": False,
                    "error": "Content not found"
                }), 404

            # Resolve relative paths from project root
            file_path = Path(content["file_path"])
            if not file_path.is_absolute():
                file_path = PROJECT_ROOT / file_path

            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return jsonify({
                    "success": False,
                    "error": "File not found"
                }), 404

            # Determine mimetype from extension
            mimetype = "image/jpeg" if file_path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"

            return send_file(
                file_path,
                mimetype=mimetype,
                as_attachment=False,
            )

        except Exception as e:
            logger.error(f"Error serving file: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/studio/content/<content_id>/thumbnail", methods=["GET"])
    def get_content_thumbnail(content_id):
        """Serve the content thumbnail."""
        try:
            content = studio_manager.get_content(content_id)

            if not content:
                return jsonify({
                    "success": False,
                    "error": "Content not found"
                }), 404

            thumbnail_path = content.get("thumbnail_path") or content.get("file_path")
            if not thumbnail_path:
                return jsonify({
                    "success": False,
                    "error": "Thumbnail not found"
                }), 404

            # Resolve relative paths from project root
            file_path = Path(thumbnail_path)
            if not file_path.is_absolute():
                file_path = PROJECT_ROOT / file_path

            if not file_path.exists():
                logger.error(f"Thumbnail not found: {file_path}")
                return jsonify({
                    "success": False,
                    "error": "Thumbnail file not found"
                }), 404

            # Determine mimetype from extension
            mimetype = "image/jpeg" if file_path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"

            return send_file(
                file_path,
                mimetype=mimetype,
                as_attachment=False,
            )

        except Exception as e:
            logger.error(f"Error serving thumbnail: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/studio/content/<content_id>", methods=["DELETE"])
    def delete_content(content_id):
        """
        Delete generated content.

        Response JSON:
            {
                "success": true,
                "message": "Content deleted"
            }
        """
        try:
            deleted = studio_manager.delete_content(content_id)

            if not deleted:
                return jsonify({
                    "success": False,
                    "error": "Content not found"
                }), 404

            return jsonify({
                "success": True,
                "message": "Content deleted"
            })

        except Exception as e:
            logger.error(f"Error deleting content: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/studio/generators", methods=["GET"])
    def list_generators():
        """
        List available generators.

        Response JSON:
            {
                "success": true,
                "generators": [
                    {
                        "type": "infographic",
                        "name": "Infographic Generator",
                        "available": true,
                        "description": "..."
                    }
                ]
            }
        """
        try:
            generator_info = []
            for gen_type, generator in generators.items():
                info = generator.get_generator_info()
                generator_info.append(info)

            return jsonify({
                "success": True,
                "generators": generator_info,
            })

        except Exception as e:
            logger.error(f"Error listing generators: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    return app
