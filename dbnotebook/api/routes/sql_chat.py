"""SQL Chat (Chat with Data) API routes.

Provides endpoints for:
- Database connection management (PostgreSQL, MySQL, SQLite)
- Schema introspection
- Natural language to SQL query execution
- Multi-turn conversation with refinement
- Query history and telemetry
"""

import logging
from typing import Optional

from flask import Blueprint, Response, request, jsonify
import json

from ...core.sql_chat import SQLChatService, DatabaseType, MaskingPolicy

logger = logging.getLogger(__name__)

# Blueprint for SQL Chat endpoints
sql_chat_bp = Blueprint('sql_chat', __name__, url_prefix='/api/sql-chat')

# SQL Chat service instance (initialized in create_sql_chat_routes)
_sql_chat_service: Optional[SQLChatService] = None

# Default user ID (will be replaced with proper auth later)
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"


def get_current_user_id() -> str:
    """Get current user ID from request context.

    Returns:
        User ID string. Currently returns default user ID.
        Will be replaced with proper auth integration.
    """
    return DEFAULT_USER_ID


def get_service() -> SQLChatService:
    """Get the SQL Chat service instance."""
    global _sql_chat_service
    if _sql_chat_service is None:
        raise RuntimeError("SQLChatService not initialized")
    return _sql_chat_service


# =============================================================================
# Connection Management Endpoints
# =============================================================================

@sql_chat_bp.route('/connections', methods=['POST'])
def create_connection():
    """
    Create a new database connection.

    Request JSON:
        {
            "name": "My Database",
            "db_type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "mydb",
            "username": "user",
            "password": "secret",
            "masking_policy": {  // Optional
                "mask_columns": ["email", "phone"],
                "redact_columns": ["ssn", "password"],
                "hash_columns": ["user_id"]
            }
        }

    Response JSON:
        {
            "success": true,
            "connectionId": "uuid",
            "message": "Connection created successfully"
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()
        data = request.get_json() or {}

        # Required fields
        name = data.get('name')
        db_type = data.get('db_type')
        host = data.get('host')
        database = data.get('database')
        username = data.get('username')
        password = data.get('password')

        # Validate required fields
        if not all([name, db_type, database]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: name, db_type, database'
            }), 400

        # Validate db_type
        if db_type not in ['postgresql', 'mysql', 'sqlite']:
            return jsonify({
                'success': False,
                'error': f'Unsupported database type: {db_type}. Supported: postgresql, mysql, sqlite'
            }), 400

        # Get port (use default if not specified)
        port = data.get('port')
        if port is None:
            port = service.get_default_port(db_type)

        # Parse masking policy
        masking_policy = None
        if data.get('masking_policy'):
            mp_data = data['masking_policy']
            masking_policy = MaskingPolicy(
                mask_columns=mp_data.get('mask_columns', []),
                redact_columns=mp_data.get('redact_columns', []),
                hash_columns=mp_data.get('hash_columns', [])
            )

        # Create connection
        conn_id, error = service.create_connection(
            user_id=user_id,
            name=name,
            db_type=db_type,
            host=host or 'localhost',
            database=database,
            username=username or '',
            password=password or '',
            port=port,
            masking_policy=masking_policy
        )

        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 400

        logger.info(f"Database connection created: {name} (type={db_type})")

        return jsonify({
            'success': True,
            'connectionId': conn_id,
            'message': 'Connection created successfully'
        })

    except Exception as e:
        logger.error(f"Error creating connection: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sql_chat_bp.route('/connections', methods=['GET'])
def list_connections():
    """
    List all database connections for the current user.

    Response JSON:
        {
            "success": true,
            "connections": [
                {
                    "id": "uuid",
                    "name": "My Database",
                    "dbType": "postgresql",
                    "host": "localhost",
                    "port": 5432,
                    "database": "mydb",
                    "username": "user",
                    "createdAt": "2024-01-01T00:00:00",
                    "lastUsedAt": "2024-01-02T00:00:00"
                }
            ]
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        connections = service.list_connections(user_id)

        return jsonify({
            'success': True,
            'connections': [
                {
                    'id': conn.id,
                    'name': conn.name,
                    'dbType': conn.type,
                    'host': conn.host,
                    'port': conn.port,
                    'database': conn.database,
                    'username': conn.username,
                    'hasMaskingPolicy': conn.masking_policy is not None,
                    'createdAt': conn.created_at.isoformat() if conn.created_at else None,
                    'lastUsedAt': conn.last_used_at.isoformat() if conn.last_used_at else None
                }
                for conn in connections
            ]
        })

    except Exception as e:
        logger.error(f"Error listing connections: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sql_chat_bp.route('/connections/test', methods=['POST'])
def test_connection():
    """
    Test database connection without saving.

    Request JSON:
        {
            "db_type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "mydb",
            "username": "user",
            "password": "secret"
        }

    Response JSON:
        {
            "success": true,
            "message": "Connection successful (read-only verified)"
        }
    """
    try:
        service = get_service()
        data = request.get_json() or {}

        db_type = data.get('db_type')
        host = data.get('host', 'localhost')
        port = data.get('port')
        database = data.get('database')
        username = data.get('username', '')
        password = data.get('password', '')

        if not all([db_type, database]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: db_type, database'
            }), 400

        # Use default port if not specified
        if port is None:
            port = service.get_default_port(db_type)

        success, message = service.test_connection(
            db_type=db_type,
            host=host,
            port=port,
            database=database,
            username=username,
            password=password
        )

        return jsonify({
            'success': success,
            'message': message
        }), 200 if success else 400

    except Exception as e:
        logger.error(f"Error testing connection: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sql_chat_bp.route('/connections/parse-string', methods=['POST'])
def parse_connection_string():
    """
    Parse a connection string into components.

    Request JSON:
        {
            "connection_string": "postgresql://user:pass@host:5432/mydb"
        }

    Response JSON:
        {
            "success": true,
            "config": {
                "db_type": "postgresql",
                "host": "localhost",
                "port": 5432,
                "database": "mydb",
                "username": "user"
            }
        }
    """
    try:
        service = get_service()
        data = request.get_json() or {}

        conn_string = data.get('connection_string', '').strip()
        if not conn_string:
            return jsonify({
                'success': False,
                'error': 'connection_string is required'
            }), 400

        config, error = service.parse_connection_string(conn_string)

        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 400

        return jsonify({
            'success': True,
            'config': config
        })

    except Exception as e:
        logger.error(f"Error parsing connection string: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sql_chat_bp.route('/connections/<connection_id>', methods=['DELETE'])
def delete_connection(connection_id: str):
    """
    Delete a database connection.

    Response JSON:
        {
            "success": true,
            "message": "Connection deleted successfully"
        }
    """
    try:
        service = get_service()

        success = service.delete_connection(connection_id)

        if not success:
            return jsonify({
                'success': False,
                'error': 'Connection not found'
            }), 404

        logger.info(f"Database connection deleted: {connection_id}")

        return jsonify({
            'success': True,
            'message': 'Connection deleted successfully'
        })

    except Exception as e:
        logger.error(f"Error deleting connection: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# Schema Endpoints
# =============================================================================

@sql_chat_bp.route('/schema/<connection_id>', methods=['GET'])
def get_schema(connection_id: str):
    """
    Get database schema for a connection.

    Query params:
        - refresh: If "true", force cache refresh

    Response JSON:
        {
            "success": true,
            "schema": {
                "tables": [
                    {
                        "name": "users",
                        "columns": [...],
                        "rowCount": 1000
                    }
                ],
                "relationships": [...],
                "cachedAt": "2024-01-01T00:00:00"
            },
            "formatted": "Table: users\\n  - id (INTEGER)\\n  - name (VARCHAR)..."
        }
    """
    try:
        service = get_service()

        force_refresh = request.args.get('refresh', 'false').lower() == 'true'

        schema = service.get_schema(connection_id, force_refresh=force_refresh)

        if not schema:
            return jsonify({
                'success': False,
                'error': 'Schema not available. Check connection.'
            }), 404

        # Format schema for display
        formatted = service.get_schema_formatted(connection_id)

        return jsonify({
            'success': True,
            'schema': {
                'tables': [
                    {
                        'name': t.name,
                        'columns': [
                            {
                                'name': c.name,
                                'type': c.type,
                                'nullable': c.nullable,
                                'primaryKey': c.primary_key,
                                'foreignKey': c.foreign_key
                            }
                            for c in t.columns
                        ],
                        'rowCount': t.row_count,
                        'sampleValues': t.sample_values
                    }
                    for t in schema.tables
                ],
                'relationships': [
                    {
                        'fromTable': r.from_table,
                        'fromColumn': r.from_column,
                        'toTable': r.to_table,
                        'toColumn': r.to_column
                    }
                    for r in schema.relationships
                ],
                'cachedAt': schema.cached_at.isoformat() if schema.cached_at else None
            },
            'formatted': formatted
        })

    except Exception as e:
        logger.error(f"Error getting schema for connection {connection_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# Session Management Endpoints
# =============================================================================

@sql_chat_bp.route('/sessions', methods=['POST'])
def create_session():
    """
    Create a new SQL chat session.

    Request JSON:
        {
            "connectionId": "uuid"
        }

    Response JSON:
        {
            "success": true,
            "sessionId": "uuid",
            "schema": {...}
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()
        data = request.get_json() or {}

        connection_id = data.get('connectionId')
        if not connection_id:
            return jsonify({
                'success': False,
                'error': 'connectionId is required'
            }), 400

        session_id, error = service.create_session(user_id, connection_id)

        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 400

        # Get session info
        session = service.get_session(session_id)
        schema_formatted = service.get_schema_formatted(connection_id) if session else None

        logger.info(f"SQL chat session created: {session_id}")

        return jsonify({
            'success': True,
            'sessionId': session_id,
            'connectionId': connection_id,
            'schemaFormatted': schema_formatted
        })

    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sql_chat_bp.route('/sessions/<session_id>', methods=['GET'])
def get_session(session_id: str):
    """
    Get session details.

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

        session = service.get_session(session_id)

        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404

        return jsonify({
            'success': True,
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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# Query Execution Endpoints
# =============================================================================

@sql_chat_bp.route('/query/<session_id>', methods=['POST'])
def execute_query(session_id: str):
    """
    Execute a natural language query against the database.

    Request JSON:
        {
            "query": "Show me the top 10 customers by revenue"
        }

    Response JSON:
        {
            "success": true,
            "result": {
                "sqlGenerated": "SELECT ...",
                "data": [...],
                "columns": [...],
                "rowCount": 10,
                "executionTimeMs": 45,
                "confidence": {
                    "score": 0.85,
                    "level": "high",
                    "factors": {...}
                },
                "intent": {
                    "type": "top_k",
                    "confidence": 0.9
                }
            }
        }
    """
    try:
        service = get_service()
        data = request.get_json() or {}

        nl_query = data.get('query', '').strip()
        if not nl_query:
            return jsonify({
                'success': False,
                'error': 'query is required'
            }), 400

        # Execute query (async)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(service.execute_query(session_id, nl_query))
        finally:
            loop.close()

        # Format response
        response = {
            'success': result.success,
            'result': {
                'sqlGenerated': result.sql_generated,
                'data': result.data,
                'columns': [
                    {
                        'name': c.name,
                        'type': c.type
                    }
                    for c in result.columns
                ],
                'rowCount': result.row_count,
                'executionTimeMs': result.execution_time_ms,
                'errorMessage': result.error_message
            }
        }

        # Add confidence if available
        if result.confidence:
            response['result']['confidence'] = {
                'score': result.confidence.score,
                'level': result.confidence.level,
                'factors': result.confidence.factors
            }

        # Add intent if available
        if result.intent:
            response['result']['intent'] = {
                'type': result.intent.intent.value,
                'confidence': result.intent.confidence,
                'hints': result.intent.prompt_hints
            }

        # Add cost estimate if available
        if result.cost_estimate:
            response['result']['costEstimate'] = {
                'totalCost': result.cost_estimate.total_cost,
                'estimatedRows': result.cost_estimate.estimated_rows,
                'hasSeqScan': result.cost_estimate.has_seq_scan,
                'hasCartesian': result.cost_estimate.has_cartesian
            }

        return jsonify(response), 200 if result.success else 400

    except Exception as e:
        logger.error(f"Error executing query in session {session_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sql_chat_bp.route('/query/<session_id>/stream', methods=['POST'])
def execute_query_stream(session_id: str):
    """
    Execute a natural language query with SSE streaming.

    Request JSON:
        {
            "query": "Show me the top 10 customers by revenue"
        }

    Response:
        SSE stream with events:
        - status: Current processing status
        - sql: Generated SQL query
        - result: Final query result
        - error: Error message if failed
    """
    try:
        service = get_service()
        data = request.get_json() or {}

        nl_query = data.get('query', '').strip()
        if not nl_query:
            return jsonify({
                'success': False,
                'error': 'query is required'
            }), 400

        def generate():
            """Generate SSE events for query execution."""
            import asyncio

            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'status': 'generating'})}\n\n"

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(service.execute_query(session_id, nl_query))

                # Send SQL generated
                yield f"data: {json.dumps({'type': 'sql', 'sql': result.sql_generated})}\n\n"

                # Send final result
                response = {
                    'type': 'result',
                    'success': result.success,
                    'data': result.data,
                    'columns': [{'name': c.name, 'type': c.type} for c in result.columns],
                    'rowCount': result.row_count,
                    'executionTimeMs': result.execution_time_ms,
                    'errorMessage': result.error_message
                }

                if result.confidence:
                    response['confidence'] = {
                        'score': result.confidence.score,
                        'level': result.confidence.level
                    }

                yield f"data: {json.dumps(response)}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            finally:
                loop.close()

            yield "data: [DONE]\n\n"

        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )

    except Exception as e:
        logger.error(f"Error streaming query in session {session_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sql_chat_bp.route('/history/<session_id>', methods=['GET'])
def get_query_history(session_id: str):
    """
    Get query history for a session.

    Query params:
        - limit: Max results (default 50)

    Response JSON:
        {
            "success": true,
            "history": [
                {
                    "userQuery": "...",
                    "sqlGenerated": "...",
                    "rowCount": 10,
                    "success": true,
                    "executionTimeMs": 45,
                    "createdAt": "..."
                }
            ]
        }
    """
    try:
        service = get_service()

        limit = int(request.args.get('limit', 50))

        history = service.get_query_history(session_id)

        # Limit results
        history = history[:limit]

        return jsonify({
            'success': True,
            'history': [
                {
                    'sqlGenerated': h.sql_generated,
                    'data': h.data[:5] if h.data else [],  # Only first 5 rows for history
                    'rowCount': h.row_count,
                    'success': h.success,
                    'executionTimeMs': h.execution_time_ms,
                    'errorMessage': h.error_message
                }
                for h in history
            ]
        })

    except Exception as e:
        logger.error(f"Error getting history for session {session_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# Telemetry Endpoints
# =============================================================================

@sql_chat_bp.route('/metrics', methods=['GET'])
def get_accuracy_metrics():
    """
    Get accuracy metrics from telemetry.

    Query params:
        - days: Number of days to look back (default 30)
        - session_id: Optional session filter

    Response JSON:
        {
            "success": true,
            "metrics": {
                "successRate": 0.92,
                "avgRetries": 0.3,
                "avgConfidence": 0.85,
                "emptyResultRate": 0.05
            }
        }
    """
    try:
        service = get_service()

        days = int(request.args.get('days', 30))
        session_id = request.args.get('session_id')

        metrics = service.get_accuracy_metrics(days=days, session_id=session_id)

        return jsonify({
            'success': True,
            'metrics': metrics
        })

    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# Health Check
# =============================================================================

@sql_chat_bp.route('/health', methods=['GET'])
def health():
    """
    Health check for SQL Chat service.

    Response JSON:
        {
            "success": true,
            "status": "healthy",
            "serviceInitialized": true
        }
    """
    try:
        service = get_service()
        return jsonify({
            'success': True,
            'status': 'healthy',
            'serviceInitialized': service is not None
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500


# =============================================================================
# Route Registration
# =============================================================================

def create_sql_chat_routes(app, pipeline, db_manager, notebook_manager):
    """
    Register SQL Chat routes with Flask app.

    Args:
        app: Flask application instance
        pipeline: LocalRAGPipeline for LLM/embedding access
        db_manager: DatabaseManager instance
        notebook_manager: NotebookManager instance
    """
    global _sql_chat_service

    # Initialize SQL Chat service
    _sql_chat_service = SQLChatService(
        pipeline=pipeline,
        db_manager=db_manager,
        notebook_manager=notebook_manager
    )

    # Register blueprint
    app.register_blueprint(sql_chat_bp)
    logger.info("SQL Chat API routes registered")

    return app
