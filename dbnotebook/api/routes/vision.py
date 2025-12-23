"""Vision API routes for image understanding."""

import logging
import os
from flask import request, jsonify
from pathlib import Path
from werkzeug.utils import secure_filename

from ...core.vision import VisionManager, get_vision_manager

logger = logging.getLogger(__name__)

# Project root directory for resolving relative paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Allowed image extensions
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def allowed_file(filename: str) -> bool:
    """Check if file has an allowed extension."""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def create_vision_routes(app, upload_folder: str = None):
    """Create Vision API routes.

    Args:
        app: Flask application instance
        upload_folder: Folder for uploaded images (default: uploads/)
    """
    # Set up upload folder
    if upload_folder is None:
        upload_folder = str(PROJECT_ROOT / "uploads")
    os.makedirs(upload_folder, exist_ok=True)

    @app.route("/api/vision/providers", methods=["GET"])
    def get_vision_providers():
        """
        Get available vision providers.

        Response JSON:
            {
                "success": true,
                "providers": [
                    {
                        "name": "gemini",
                        "display_name": "Google Gemini Vision",
                        "available": true,
                        "is_default": true,
                        "supported_formats": [".png", ".jpg", ...]
                    }
                ],
                "default_provider": "gemini"
            }
        """
        try:
            vision_manager = get_vision_manager()
            providers_info = vision_manager.get_providers_info()
            default_provider = os.getenv("VISION_PROVIDER", "gemini")

            return jsonify({
                "success": True,
                "providers": providers_info,
                "default_provider": default_provider,
                "supported_formats": vision_manager.get_supported_formats(),
            })
        except Exception as e:
            logger.error(f"Failed to get vision providers: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/vision/analyze", methods=["POST"])
    def analyze_image():
        """
        Analyze an image and extract description/text.

        Request JSON:
            {
                "image_path": "/path/to/image.png",  # or use file upload
                "prompt": "Optional analysis prompt",
                "provider": "gemini"  # optional, uses default if not specified
            }

        Or multipart form with:
            - image: File upload
            - prompt: Optional text
            - provider: Optional provider name

        Response JSON:
            {
                "success": true,
                "result": {
                    "description": "Detailed description...",
                    "text_content": "Extracted text...",
                    "provider": "gemini",
                    "model": "gemini-2.0-flash-exp"
                }
            }
        """
        try:
            vision_manager = get_vision_manager()

            if not vision_manager.is_available():
                return jsonify({
                    "success": False,
                    "error": "No vision providers available. Set GOOGLE_API_KEY or OPENAI_API_KEY."
                }), 503

            # Handle file upload or JSON request
            if request.content_type and "multipart/form-data" in request.content_type:
                # File upload
                if "image" not in request.files:
                    return jsonify({
                        "success": False,
                        "error": "No image file provided"
                    }), 400

                file = request.files["image"]
                if file.filename == "":
                    return jsonify({
                        "success": False,
                        "error": "No selected file"
                    }), 400

                if not allowed_file(file.filename):
                    return jsonify({
                        "success": False,
                        "error": f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
                    }), 400

                # Save uploaded file
                filename = secure_filename(file.filename)
                image_path = os.path.join(upload_folder, filename)
                file.save(image_path)

                prompt = request.form.get("prompt")
                provider = request.form.get("provider")

            else:
                # JSON request
                data = request.get_json() or {}
                image_path = data.get("image_path")
                prompt = data.get("prompt")
                provider = data.get("provider")

                if not image_path:
                    return jsonify({
                        "success": False,
                        "error": "image_path is required"
                    }), 400

            # Analyze the image
            result = vision_manager.analyze_image(
                image_path=image_path,
                prompt=prompt,
                provider=provider,
            )

            return jsonify({
                "success": True,
                "result": {
                    "description": result.description,
                    "text_content": result.text_content,
                    "provider": result.provider,
                    "model": result.model,
                    "confidence": result.confidence,
                    "metadata": result.metadata,
                }
            })

        except FileNotFoundError as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 404
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/vision/extract-text", methods=["POST"])
    def extract_text_from_image():
        """
        Extract text from an image (OCR).

        Request JSON:
            {
                "image_path": "/path/to/image.png",
                "provider": "gemini"  # optional
            }

        Or multipart form with:
            - image: File upload
            - provider: Optional provider name

        Response JSON:
            {
                "success": true,
                "text": "Extracted text content..."
            }
        """
        try:
            vision_manager = get_vision_manager()

            if not vision_manager.is_available():
                return jsonify({
                    "success": False,
                    "error": "No vision providers available. Set GOOGLE_API_KEY or OPENAI_API_KEY."
                }), 503

            # Handle file upload or JSON request
            if request.content_type and "multipart/form-data" in request.content_type:
                # File upload
                if "image" not in request.files:
                    return jsonify({
                        "success": False,
                        "error": "No image file provided"
                    }), 400

                file = request.files["image"]
                if file.filename == "":
                    return jsonify({
                        "success": False,
                        "error": "No selected file"
                    }), 400

                if not allowed_file(file.filename):
                    return jsonify({
                        "success": False,
                        "error": f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
                    }), 400

                # Save uploaded file
                filename = secure_filename(file.filename)
                image_path = os.path.join(upload_folder, filename)
                file.save(image_path)

                provider = request.form.get("provider")

            else:
                # JSON request
                data = request.get_json() or {}
                image_path = data.get("image_path")
                provider = data.get("provider")

                if not image_path:
                    return jsonify({
                        "success": False,
                        "error": "image_path is required"
                    }), 400

            # Extract text from image
            text = vision_manager.extract_text(
                image_path=image_path,
                provider=provider,
            )

            return jsonify({
                "success": True,
                "text": text,
            })

        except FileNotFoundError as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 404
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/vision/status", methods=["GET"])
    def get_vision_status():
        """
        Get vision system status.

        Response JSON:
            {
                "success": true,
                "available": true,
                "providers": ["gemini", "openai"],
                "default_provider": "gemini"
            }
        """
        try:
            vision_manager = get_vision_manager()

            return jsonify({
                "success": True,
                "available": vision_manager.is_available(),
                "providers": vision_manager.get_available_providers(),
                "default_provider": os.getenv("VISION_PROVIDER", "gemini"),
            })
        except Exception as e:
            logger.error(f"Failed to get vision status: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    logger.info("Vision API routes registered")
