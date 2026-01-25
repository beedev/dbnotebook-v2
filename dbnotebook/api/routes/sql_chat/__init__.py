"""SQL Chat (Chat with Data) API routes package.

Provides endpoints for:
- Database connection management (PostgreSQL, MySQL, SQLite)
- Schema introspection and dictionary management
- Natural language to SQL query execution
- Multi-turn conversation with refinement
- Query history and telemetry

This package splits the monolithic sql_chat.py into smaller modules:
- connections.py: Connection CRUD operations
- sessions.py: Session management
- queries.py: Query execution and history
- schema.py: Schema introspection, dictionary, telemetry
- utils.py: Shared utilities
"""

import logging

from dbnotebook.core.sql_chat import SQLChatService

from .utils import set_service
from .connections import connections_bp
from .sessions import sessions_bp
from .queries import queries_bp
from .schema import schema_bp

logger = logging.getLogger(__name__)

# Re-export blueprints for external use
__all__ = [
    'create_sql_chat_routes',
    'connections_bp',
    'sessions_bp',
    'queries_bp',
    'schema_bp',
]


def create_sql_chat_routes(app, pipeline, db_manager, notebook_manager):
    """
    Register SQL Chat routes with Flask app.

    Args:
        app: Flask application instance
        pipeline: LocalRAGPipeline for LLM/embedding access
        db_manager: DatabaseManager instance
        notebook_manager: NotebookManager instance
    """
    # Initialize SQL Chat service
    sql_chat_service = SQLChatService(
        pipeline=pipeline,
        db_manager=db_manager,
        notebook_manager=notebook_manager
    )

    # Set service in utils module for route handlers
    set_service(sql_chat_service)

    # Register all blueprints with consistent URL prefix
    app.register_blueprint(connections_bp, url_prefix='/api/sql-chat')
    app.register_blueprint(sessions_bp, url_prefix='/api/sql-chat')
    app.register_blueprint(queries_bp, url_prefix='/api/sql-chat')
    app.register_blueprint(schema_bp, url_prefix='/api/sql-chat')

    logger.info("SQL Chat API routes registered (modular)")

    return app
