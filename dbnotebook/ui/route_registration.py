"""Route registration for Flask application.

Centralizes the registration of all API route modules.
This allows the FlaskChatbotUI class to delegate route setup.

Usage:
    from dbnotebook.ui.route_registration import register_all_routes

    register_all_routes(
        app=app,
        pipeline=pipeline,
        db_manager=db_manager,
        notebook_manager=notebook_manager
    )
"""

import logging
from typing import Optional

from flask import Flask

logger = logging.getLogger(__name__)


def register_all_routes(
    app: Flask,
    pipeline,
    db_manager,
    notebook_manager,
    metadata_manager=None,
    web_ingestion=None,
    synopsis_manager=None,
    studio_manager=None,
) -> None:
    """Register all API route modules with the Flask application.

    This function centralizes the registration of all route blueprints
    and route factories, making it easier to manage and modify routes.

    Args:
        app: Flask application instance
        pipeline: LocalRAGPipeline instance
        db_manager: DatabaseManager instance (optional)
        notebook_manager: NotebookManager instance (optional)
        metadata_manager: MetadataManager instance (optional)
        web_ingestion: WebContentIngestion instance (optional)
        synopsis_manager: SynopsisManager instance (optional)
        studio_manager: StudioManager instance (optional)
    """
    # Import route creators
    from ..api.routes.web_content import create_web_content_routes
    from ..api.routes.studio import create_studio_routes
    from ..api.routes.vision import create_vision_routes
    from ..api.routes.transformations import create_transformation_routes
    from ..api.routes.agents import create_agent_routes
    from ..api.routes.analytics import create_analytics_routes
    from ..api.routes.sql_chat import create_sql_chat_routes
    from ..api.routes.query import create_query_routes
    from ..api.routes.chat_v2 import create_chat_v2_routes
    from ..api.routes.admin import create_admin_routes
    from ..api.routes.auth import create_auth_routes
    from ..api.routes.settings import create_settings_routes

    # Set db_manager in decorators module for RBAC
    try:
        from ..api.core.decorators import set_db_manager
        if db_manager:
            set_db_manager(db_manager)
            logger.debug("Database manager set for API decorators")
    except ImportError:
        logger.debug("API decorators module not available")

    # Track registered routes
    registered = []

    # Authentication routes (no auth required)
    try:
        create_auth_routes(app, db_manager)
        registered.append("auth")
    except Exception as e:
        logger.warning(f"Failed to register auth routes: {e}")

    # Admin routes (admin auth required)
    try:
        create_admin_routes(app, db_manager)
        registered.append("admin")
    except Exception as e:
        logger.warning(f"Failed to register admin routes: {e}")

    # Chat V2 routes (multi-user safe)
    try:
        create_chat_v2_routes(app, pipeline, db_manager, notebook_manager)
        registered.append("chat_v2")
    except Exception as e:
        logger.warning(f"Failed to register chat_v2 routes: {e}")

    # Query API routes (programmatic access)
    try:
        create_query_routes(app, pipeline, db_manager, notebook_manager)
        registered.append("query")
    except Exception as e:
        logger.warning(f"Failed to register query routes: {e}")

    # Web content routes (scraping, search)
    if web_ingestion:
        try:
            create_web_content_routes(
                app, pipeline, db_manager, notebook_manager,
                web_ingestion, synopsis_manager
            )
            registered.append("web_content")
        except Exception as e:
            logger.warning(f"Failed to register web_content routes: {e}")

    # Studio routes (content generation)
    if studio_manager:
        try:
            create_studio_routes(
                app, pipeline, db_manager, notebook_manager,
                studio_manager=studio_manager
            )
            registered.append("studio")
        except Exception as e:
            logger.warning(f"Failed to register studio routes: {e}")

    # Vision routes (image analysis)
    try:
        create_vision_routes(app, pipeline, db_manager, notebook_manager)
        registered.append("vision")
    except Exception as e:
        logger.warning(f"Failed to register vision routes: {e}")

    # Transformation routes (AI transformations)
    try:
        create_transformation_routes(app, pipeline, db_manager, notebook_manager)
        registered.append("transformations")
    except Exception as e:
        logger.warning(f"Failed to register transformation routes: {e}")

    # Agent routes (agentic query analysis)
    try:
        create_agent_routes(app, pipeline, db_manager, notebook_manager)
        registered.append("agents")
    except Exception as e:
        logger.warning(f"Failed to register agent routes: {e}")

    # Analytics routes (Excel/CSV analysis)
    try:
        create_analytics_routes(app, pipeline, db_manager, notebook_manager)
        registered.append("analytics")
    except Exception as e:
        logger.warning(f"Failed to register analytics routes: {e}")

    # SQL Chat routes (natural language to SQL)
    if db_manager:
        try:
            create_sql_chat_routes(app, pipeline, db_manager, notebook_manager)
            registered.append("sql_chat")
        except Exception as e:
            logger.warning(f"Failed to register sql_chat routes: {e}")

    # Settings routes (user preferences)
    try:
        create_settings_routes(app, pipeline, db_manager)
        registered.append("settings")
    except Exception as e:
        logger.warning(f"Failed to register settings routes: {e}")

    logger.info(f"Registered {len(registered)} route modules: {', '.join(registered)}")


def register_notebook_routes(
    app: Flask,
    db_manager,
    notebook_manager,
) -> None:
    """Register notebook management routes.

    These routes handle CRUD operations for notebooks and their documents.

    Args:
        app: Flask application instance
        db_manager: DatabaseManager instance
        notebook_manager: NotebookManager instance
    """
    from flask import jsonify, request

    @app.route("/api/notebooks", methods=["GET"])
    def list_notebooks():
        """Get all notebooks for the current user."""
        if not notebook_manager:
            return jsonify({"success": False, "error": "Notebooks not available"}), 503

        try:
            from ..core.constants import DEFAULT_USER_ID
            user_id = request.headers.get("X-User-ID", DEFAULT_USER_ID)
            notebooks = notebook_manager.get_notebooks(user_id)
            return jsonify({"success": True, "notebooks": notebooks})
        except Exception as e:
            logger.error(f"Error listing notebooks: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/notebooks", methods=["POST"])
    def create_notebook():
        """Create a new notebook."""
        if not notebook_manager:
            return jsonify({"success": False, "error": "Notebooks not available"}), 503

        try:
            from ..core.constants import DEFAULT_USER_ID
            data = request.json or {}
            name = data.get("name", "Untitled Notebook")
            description = data.get("description", "")
            user_id = request.headers.get("X-User-ID", DEFAULT_USER_ID)

            notebook = notebook_manager.create_notebook(
                name=name,
                description=description,
                user_id=user_id
            )
            return jsonify({"success": True, "notebook": notebook})
        except Exception as e:
            logger.error(f"Error creating notebook: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/notebooks/<notebook_id>", methods=["DELETE"])
    def delete_notebook(notebook_id):
        """Delete a notebook."""
        if not notebook_manager:
            return jsonify({"success": False, "error": "Notebooks not available"}), 503

        try:
            success = notebook_manager.delete_notebook(notebook_id)
            if success:
                return jsonify({"success": True})
            return jsonify({"success": False, "error": "Notebook not found"}), 404
        except Exception as e:
            logger.error(f"Error deleting notebook: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    logger.debug("Notebook management routes registered")
