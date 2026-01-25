"""SQL Chat session management routes.

Endpoints for chat session lifecycle:
- Create new sessions
- Get session details
- Refresh session schema
"""

import logging

from flask import Blueprint, request

from dbnotebook.api.core.response import (
    success_response, error_response, validation_error, not_found
)

from .utils import get_service, get_current_user_id

logger = logging.getLogger(__name__)

# Blueprint for session endpoints
sessions_bp = Blueprint('sql_chat_sessions', __name__)


@sessions_bp.route('/sessions', methods=['POST'])
def create_session():
    """
    Create a new SQL chat session.

    Request JSON:
        {
            "connectionId": "uuid",
            "skipSchemaRefresh": false  // Optional: skip schema introspection if already loaded
        }

    Response JSON:
        {
            "success": true,
            "sessionId": "uuid",
            "connectionId": "uuid",
            "schemaFormatted": "..."
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()
        data = request.get_json() or {}

        connection_id = data.get('connectionId')
        if not connection_id:
            return validation_error('connectionId is required')

        # Performance optimization: skip schema refresh if frontend already loaded it
        skip_schema_refresh = data.get('skipSchemaRefresh', False)

        session_id, error = service.create_session(
            user_id, connection_id, skip_schema_refresh=skip_schema_refresh
        )

        if error:
            return error_response(error, 400)

        # Get session info
        session = service.get_session(session_id, user_id)
        schema_formatted = service.get_schema_formatted(connection_id) if session else None

        logger.info(f"SQL chat session created: {session_id}")

        return success_response({
            'sessionId': session_id,
            'connectionId': connection_id,
            'schemaFormatted': schema_formatted
        })

    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return error_response(str(e), 500)


@sessions_bp.route('/sessions/<session_id>', methods=['GET'])
def get_session(session_id: str):
    """
    Get session details.

    Multi-user safe: Validates user has access to the session.

    Query params:
        - user_id: Optional user ID for access validation

    Response JSON:
        {
            "success": true,
            "session": {
                "sessionId": "uuid",
                "connectionId": "uuid",
                "status": "complete",
                "createdAt": "...",
                "lastQueryAt": "..."
            }
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        session = service.get_session(session_id, user_id)

        if not session:
            return not_found('Session', session_id)

        return success_response({
            'session': {
                'sessionId': session.session_id,
                'connectionId': session.connection_id,
                'status': session.status,
                'createdAt': session.created_at.isoformat() if session.created_at else None,
                'lastQueryAt': session.last_query_at.isoformat() if session.last_query_at else None
            }
        })

    except Exception as e:
        logger.error(f"Error getting session {session_id}: {e}")
        return error_response(str(e), 500)


@sessions_bp.route('/sessions/<session_id>/refresh-schema', methods=['POST'])
def refresh_session_schema(session_id: str):
    """
    Refresh database schema for a session.

    Forces reload of schema from database and recreates the query engine.
    Use this when database schema has changed (columns added/removed/renamed).

    Multi-user safe: Validates user has access to the session.

    Response JSON:
        {
            "success": true,
            "message": "Schema refreshed: 10 tables, 50 columns",
            "schemaFormatted": "..."
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        success, message = service.refresh_session_schema(session_id, user_id)

        if not success:
            return error_response(message, 400)

        # Get updated formatted schema
        session = service.get_session(session_id, user_id)
        schema_formatted = service.get_schema_formatted(session.connection_id) if session else None

        logger.info(f"Schema refreshed for session {session_id}: {message}")

        return success_response({
            'message': message,
            'schemaFormatted': schema_formatted
        })

    except Exception as e:
        logger.error(f"Error refreshing schema for session {session_id}: {e}")
        return error_response(str(e), 500)
