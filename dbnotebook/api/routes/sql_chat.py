"""SQL Chat (Chat with Data) API routes.

Provides endpoints for:
- Database connection management (PostgreSQL, MySQL, SQLite)
- Schema introspection
- Natural language to SQL query execution
- Multi-turn conversation with refinement
- Query history and telemetry
"""

import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from flask import Blueprint, Response, request, jsonify
import json

from ...core.sql_chat import SQLChatService, DatabaseType, MaskingPolicy
from ...core.services.document_service import DocumentService


class SQLChatJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for SQL Chat results."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, bytes):
            return obj.decode('utf-8', errors='replace')
        return super().default(obj)

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
        schema = data.get('schema')  # PostgreSQL schema(s) e.g., 'public' or 'sales,hr'

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
            schema=schema,
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
                    'schema': conn.schema,
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
        schema = data.get('schema')  # PostgreSQL schema(s)
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
            schema=schema,
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
                                'dataType': c.type,
                                'nullable': c.nullable,
                                'isPrimaryKey': c.primary_key,
                                'isForeignKey': bool(c.foreign_key)
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
            "connectionId": "uuid",
            "skipSchemaRefresh": false  // Optional: skip schema introspection if already loaded
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

        # Performance optimization: skip schema refresh if frontend already loaded it
        skip_schema_refresh = data.get('skipSchemaRefresh', False)

        session_id, error = service.create_session(
            user_id, connection_id, skip_schema_refresh=skip_schema_refresh
        )

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


@sql_chat_bp.route('/sessions/<session_id>/refresh-schema', methods=['POST'])
def refresh_session_schema(session_id: str):
    """
    Refresh database schema for a session.

    Forces reload of schema from database and recreates the query engine.
    Use this when database schema has changed (columns added/removed/renamed).

    Response JSON:
        {
            "success": true,
            "message": "Schema refreshed: 10 tables, 50 columns",
            "schemaFormatted": "..."
        }
    """
    try:
        service = get_service()

        success, message = service.refresh_session_schema(session_id)

        if not success:
            return jsonify({
                'success': False,
                'error': message
            }), 400

        # Get updated formatted schema
        session = service.get_session(session_id)
        schema_formatted = service.get_schema_formatted(session.connection_id) if session else None

        logger.info(f"Schema refreshed for session {session_id}: {message}")

        return jsonify({
            'success': True,
            'message': message,
            'schemaFormatted': schema_formatted
        })

    except Exception as e:
        logger.error(f"Error refreshing schema for session {session_id}: {e}")
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

        # Add validation warnings if available
        if result.validation_warnings:
            response['result']['validationWarnings'] = result.validation_warnings

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
            yield f"data: {json.dumps({'type': 'status', 'status': 'generating'}, cls=SQLChatJSONEncoder)}\n\n"

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(service.execute_query(session_id, nl_query))

                # Send SQL generated
                yield f"data: {json.dumps({'type': 'sql', 'sql': result.sql_generated}, cls=SQLChatJSONEncoder)}\n\n"

                # Send final result (uses custom encoder to handle UUID, datetime, Decimal)
                response = {
                    'type': 'result',
                    'success': result.success,
                    'sql': result.sql_generated,
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

                if result.explanation:
                    response['explanation'] = result.explanation

                # Add validation warnings if available
                if result.validation_warnings:
                    response['validationWarnings'] = result.validation_warnings

                yield f"data: {json.dumps(response, cls=SQLChatJSONEncoder)}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, cls=SQLChatJSONEncoder)}\n\n"
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
# Few-Shot Dataset Management
# =============================================================================

@sql_chat_bp.route('/few-shot/status', methods=['GET'])
def get_few_shot_status():
    """
    Get status of few-shot examples dataset.

    Response JSON:
        {
            "success": true,
            "initialized": false,
            "exampleCount": 0,
            "minRequired": 50000
        }
    """
    try:
        service = get_service()

        status = service.get_few_shot_status()

        return jsonify({
            'success': True,
            **status
        })

    except Exception as e:
        logger.error(f"Error getting few-shot status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sql_chat_bp.route('/few-shot/initialize', methods=['POST'])
def initialize_few_shot():
    """
    Initialize few-shot examples by loading Gretel dataset.

    This is a long-running operation (~30 min for full dataset).
    Consider using smaller maxExamples for faster setup.

    Request JSON:
        {
            "maxExamples": 10000  // Optional, default loads all ~100K
        }

    Response JSON:
        {
            "success": true,
            "message": "Few-shot initialization started",
            "examplesLoaded": 10000
        }
    """
    try:
        service = get_service()
        data = request.get_json() or {}

        max_examples = data.get('maxExamples')

        # Run initialization (async internally)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success = loop.run_until_complete(
                service.initialize_few_shot(max_examples=max_examples)
            )
        finally:
            loop.close()

        if success:
            status = service.get_few_shot_status()
            return jsonify({
                'success': True,
                'message': 'Few-shot dataset loaded successfully',
                'examplesLoaded': status.get('exampleCount', 0)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to initialize few-shot dataset. Check logs.'
            }), 500

    except Exception as e:
        logger.error(f"Error initializing few-shot dataset: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# Dictionary Management Endpoints
# =============================================================================

@sql_chat_bp.route('/connections/<connection_id>/dictionary', methods=['GET'])
def get_dictionary(connection_id: str):
    """
    Generate dictionary Markdown for a database connection and create notebook.

    This endpoint:
    1. Creates a "SQL: <connection_name>" notebook if it doesn't exist
    2. Generates the schema dictionary from current database
    3. Saves the dictionary as a source document in the notebook

    Query params:
        - connection_name: Optional display name for the dictionary

    Response JSON:
        {
            "success": true,
            "dictionary": "# Database Dictionary: ...",
            "connectionName": "My Database",
            "tableCount": 15,
            "columnCount": 85,
            "notebookId": "uuid-of-notebook"
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        connection_name = request.args.get('connection_name')

        # Get connection info
        connection = service._connections.get_connection(connection_id)
        if not connection:
            return jsonify({
                'success': False,
                'error': 'Connection not found'
            }), 404

        conn_name = connection.name if connection else connection_name or 'Unknown'

        # Check if notebook exists for this connection
        notebook_manager = service.notebook_manager
        notebook_id = None

        if notebook_manager:
            # Look for existing SQL dictionary notebook
            notebooks = notebook_manager.list_notebooks(user_id)
            sql_notebook_name = f"SQL: {conn_name}"

            for nb in notebooks:
                if nb.get('name') == sql_notebook_name:
                    notebook_id = nb.get('id')
                    break

            # Check if dictionary already exists - return lightweight version
            # (Full dictionary with samples is already in RAG embeddings)
            if notebook_id:
                existing_docs = notebook_manager.get_documents(notebook_id)
                has_dictionary = any(
                    'dictionary' in doc.get('file_name', '').lower() or
                    'schema' in doc.get('file_name', '').lower()
                    for doc in existing_docs
                )

                if has_dictionary:
                    # Dictionary already ingested - generate fast schema-only version for display
                    schema = service.get_schema(connection_id)
                    if schema:
                        # Use fast schema dictionary (no sample queries)
                        fast_dictionary = service._schema.generate_schema_dictionary(
                            service._connections.get_engine(connection_id),
                            conn_name
                        )
                        logger.info(f"Returning cached dictionary for {conn_name} (schema-only)")
                        return jsonify({
                            'success': True,
                            'dictionary': fast_dictionary,
                            'connectionName': conn_name,
                            'tableCount': len(schema.tables),
                            'columnCount': sum(len(t.columns) for t in schema.tables),
                            'notebookId': notebook_id,
                            'cached': True
                        })

            # Create notebook if it doesn't exist
            if not notebook_id:
                logger.info(f"Creating SQL dictionary notebook for connection {conn_name}")
                notebook = notebook_manager.create_notebook(
                    user_id=user_id,
                    name=sql_notebook_name,
                    description=f"Schema dictionary and query examples for {conn_name}"
                )
                notebook_id = notebook.get('id')

        # Generate dictionary from current schema
        dictionary, error = service.generate_dictionary(
            connection_id=connection_id,
            connection_name=conn_name
        )

        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 500

        # Get schema for table/column counts
        schema = service.get_schema(connection_id)

        # Save dictionary as source document if notebook exists
        # Uses web content pattern: in-memory ingestion without disk I/O
        source_id = None
        if notebook_id and notebook_manager and dictionary:
            dict_filename = f"{conn_name}_dictionary.md"
            pipeline = service.pipeline

            # Delete old dictionary if exists (handles both DB and embeddings)
            document_service = DocumentService(
                pipeline=pipeline,
                db_manager=service.db_manager,
                notebook_manager=notebook_manager
            )
            existing_docs = notebook_manager.get_documents(notebook_id)
            for doc in existing_docs:
                if doc.get('file_name') == dict_filename:
                    old_source_id = doc.get('source_id')
                    logger.info(f"Removing existing dictionary (source_id: {old_source_id}) before regeneration")
                    document_service.delete(old_source_id, notebook_id, user_id)
                    break

            try:
                # 1. Register in database (like web_ingestion.py pattern)
                source_id = notebook_manager.add_document(
                    notebook_id=notebook_id,
                    file_name=dict_filename,
                    file_content=dictionary.encode('utf-8'),
                    file_type="md",
                    chunk_count=0  # Updated after chunking
                )
                logger.info(f"Registered dictionary: source_id={source_id}")

                # 2. Create nodes from content (like web_ingestion.py)
                from llama_index.core.schema import Document as LlamaDocument
                from llama_index.core.node_parser import SentenceSplitter
                from llama_index.core import Settings

                splitter = SentenceSplitter(chunk_size=512, chunk_overlap=32)
                doc = LlamaDocument(
                    text=dictionary,
                    metadata={
                        "file_name": dict_filename,
                        "source_id": source_id,
                        "notebook_id": notebook_id,
                        "user_id": user_id,
                        "tree_level": 0
                    }
                )
                nodes = splitter.get_nodes_from_documents([doc])

                # 3. Add notebook metadata to nodes
                for node in nodes:
                    if hasattr(node, 'metadata'):
                        node.metadata["notebook_id"] = notebook_id
                        node.metadata["source_id"] = source_id
                        node.metadata["tree_level"] = 0

                # 4. Embed and store (like web_content.py pattern)
                if nodes and pipeline and hasattr(pipeline, "_vector_store"):
                    embed_model = Settings.embed_model
                    if embed_model:
                        texts = [node.get_content() for node in nodes]
                        embeddings = embed_model.get_text_embedding_batch(texts)
                        for node, embedding in zip(nodes, embeddings):
                            node.embedding = embedding
                        added = pipeline._vector_store.add_nodes(nodes, notebook_id=notebook_id)
                        logger.info(f"Added {added} embeddings for dictionary")

                # 5. Update chunk count
                notebook_manager.update_document_chunk_count(source_id, len(nodes))

                # 6. Queue transformation with actual document_text (fixes NULL issue)
                if hasattr(pipeline, '_ingestion') and pipeline._ingestion._transformation_callback:
                    pipeline._ingestion._transformation_callback(
                        source_id=source_id,
                        document_text=dictionary,  # Pass content directly!
                        notebook_id=notebook_id,
                        file_name=dict_filename
                    )
                    logger.info(f"Queued transformation for dictionary: source_id={source_id}")

                logger.info(f"Dictionary uploaded successfully: source_id={source_id}, nodes={len(nodes)}")

            except ValueError as e:
                # Duplicate document
                logger.warning(f"Dictionary already exists: {e}")
            except Exception as e:
                logger.error(f"Failed to upload dictionary: {e}")
                import traceback
                logger.error(traceback.format_exc())

        # Get table/column counts
        table_count = len(schema.tables) if schema else 0
        column_count = sum(len(t.columns) for t in schema.tables) if schema else 0

        return jsonify({
            'success': True,
            'dictionary': dictionary,
            'connectionName': conn_name,
            'tableCount': table_count,
            'columnCount': column_count,
            'notebookId': notebook_id,
            'sourceId': source_id
        })

    except Exception as e:
        logger.error(f"Error generating dictionary for connection {connection_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sql_chat_bp.route('/connections/<connection_id>/dictionary/regenerate', methods=['POST'])
def regenerate_dictionary(connection_id: str):
    """
    Regenerate dictionary for a connection (used when schema changes).

    This endpoint:
    1. Generates fresh schema dictionary + sample values
    2. Updates the SQL notebook with new content
    3. Re-indexes for RAG queries

    Response JSON:
        {
            "success": true,
            "message": "Dictionary regenerated successfully",
            "tableCount": 15
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        # Get connection
        connection = service._connections.get_connection(connection_id)
        if not connection:
            return jsonify({'success': False, 'error': 'Connection not found'}), 404

        conn_name = connection.name
        engine = service._connections.get_engine(connection_id)
        if not engine:
            return jsonify({'success': False, 'error': 'Could not connect to database'}), 500

        # Generate fresh dictionary files
        logger.info(f"Regenerating dictionary for {conn_name}")
        schema_md = service._schema.generate_schema_dictionary(engine, conn_name)
        samples_md = service._schema.generate_sample_values(engine, conn_name, limit=5)

        # Get or create SQL notebook
        notebook_manager = service.notebook_manager
        notebook_id = None

        if notebook_manager:
            notebooks = notebook_manager.list_notebooks(user_id)
            sql_notebook_name = f"SQL: {conn_name}"

            for nb in notebooks:
                if nb.get('name') == sql_notebook_name:
                    notebook_id = nb.get('id')
                    break

            if not notebook_id:
                notebook = notebook_manager.create_notebook(
                    user_id=user_id,
                    name=sql_notebook_name,
                    description=f"Schema dictionary and sample data for {conn_name}"
                )
                notebook_id = notebook.get('id')

        # Save and ingest dictionary files
        if notebook_id:
            from pathlib import Path

            upload_dir = Path("uploads") / "sql_dictionaries"
            upload_dir.mkdir(parents=True, exist_ok=True)

            # Save schema dictionary
            schema_file = upload_dir / f"schema_dictionary_{connection_id}.md"
            schema_file.write_text(schema_md, encoding='utf-8')

            # Save sample values
            samples_file = upload_dir / f"sample_values_{connection_id}.md"
            samples_file.write_text(samples_md, encoding='utf-8')

            # Store in vector store
            try:
                service.pipeline.store_nodes(
                    input_files=[str(schema_file), str(samples_file)],
                    notebook_id=notebook_id,
                    user_id=user_id
                )
                logger.info(f"Dictionary regenerated for {conn_name}")
            except Exception as e:
                logger.warning(f"Could not store dictionary nodes: {e}")

        # Get table count
        schema = service.get_schema(connection_id)
        table_count = len(schema.tables) if schema else 0

        return jsonify({
            'success': True,
            'message': f'Dictionary regenerated for {conn_name}',
            'tableCount': table_count,
            'notebookId': notebook_id
        })

    except Exception as e:
        logger.error(f"Error regenerating dictionary for {connection_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@sql_chat_bp.route('/connections/<connection_id>/dictionary/delta', methods=['POST'])
def get_dictionary_delta(connection_id: str):
    """
    Get schema changes (delta) between existing dictionary and current database schema.

    Use this before applying schema sync to preview changes.

    Request JSON:
        {
            "existingDictionary": "# Database Dictionary: ...",
            "connectionName": "My Database" (optional)
        }

    Response JSON:
        {
            "success": true,
            "delta": {
                "hasChanges": true,
                "addedTables": ["new_table"],
                "removedTables": [],
                "modifiedTables": {
                    "users": {
                        "addedColumns": ["email_verified"],
                        "removedColumns": []
                    }
                },
                "preview": "# Database Dictionary: ... (merged)"
            }
        }
    """
    try:
        service = get_service()
        data = request.get_json() or {}

        existing_dictionary = data.get('existingDictionary', '')
        connection_name = data.get('connectionName')

        if not existing_dictionary:
            return jsonify({
                'success': False,
                'error': 'existingDictionary is required'
            }), 400

        delta = service.get_schema_delta(
            connection_id=connection_id,
            existing_dictionary=existing_dictionary,
            connection_name=connection_name
        )

        return jsonify({
            'success': True,
            'delta': delta
        })

    except Exception as e:
        logger.error(f"Error computing dictionary delta for connection {connection_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sql_chat_bp.route('/connections/<connection_id>/dictionary/merge', methods=['POST'])
def merge_dictionary(connection_id: str):
    """
    Merge schema changes into existing dictionary while preserving user edits.

    Request JSON:
        {
            "existingDictionary": "# Database Dictionary: ..."
        }

    Response JSON:
        {
            "success": true,
            "dictionary": "# Database Dictionary: ... (merged)",
            "message": "Merged 2 new tables, 5 new columns"
        }
    """
    try:
        service = get_service()
        data = request.get_json() or {}

        existing_dictionary = data.get('existingDictionary', '')

        if not existing_dictionary:
            return jsonify({
                'success': False,
                'error': 'existingDictionary is required'
            }), 400

        merged_dictionary, message = service.merge_dictionary(
            connection_id=connection_id,
            existing_dictionary=existing_dictionary
        )

        return jsonify({
            'success': True,
            'dictionary': merged_dictionary,
            'message': message
        })

    except Exception as e:
        logger.error(f"Error merging dictionary for connection {connection_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# Schema Linking Endpoints
# =============================================================================

@sql_chat_bp.route('/sessions/<session_id>/table-relevance', methods=['POST'])
def get_table_relevance(session_id: str):
    """
    Get table relevance scores for a query.

    Shows which tables the schema linker considers most relevant
    for a given natural language query. Useful for debugging and
    understanding table selection.

    Request JSON:
        {
            "query": "Show me total sales by region"
        }

    Response JSON:
        {
            "success": true,
            "relevance": [
                {"table": "sales", "score": 0.92},
                {"table": "regions", "score": 0.85},
                {"table": "customers", "score": 0.45}
            ]
        }
    """
    try:
        service = get_service()
        data = request.get_json() or {}

        query = data.get('query', '').strip()
        if not query:
            return jsonify({
                'success': False,
                'error': 'query is required'
            }), 400

        scores = service.get_table_relevance_scores(session_id, query)

        return jsonify({
            'success': True,
            'relevance': [
                {'table': table, 'score': round(score, 3)}
                for table, score in scores
            ]
        })

    except Exception as e:
        logger.error(f"Error getting table relevance for session {session_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# Query Learning Endpoints
# =============================================================================

@sql_chat_bp.route('/connections/<connection_id>/learned-joins', methods=['GET'])
def get_learned_joins(connection_id: str):
    """
    Get learned JOIN patterns for a connection.

    Returns JOIN patterns extracted from successful queries,
    sorted by usage frequency. These patterns help improve
    SQL generation accuracy over time.

    Response JSON:
        {
            "success": true,
            "patterns": [
                {
                    "table1": "orders",
                    "column1": "customer_id",
                    "table2": "customers",
                    "column2": "id",
                    "joinType": "INNER",
                    "usageCount": 15
                }
            ]
        }
    """
    try:
        service = get_service()

        patterns = service.get_learned_join_patterns(connection_id)

        return jsonify({
            'success': True,
            'patterns': patterns
        })

    except Exception as e:
        logger.error(f"Error getting learned joins for connection {connection_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sql_chat_bp.route('/connections/<connection_id>/learned-joins', methods=['DELETE'])
def clear_learned_joins(connection_id: str):
    """
    Clear learned JOIN patterns for a connection.

    Use this to reset learning if the database schema has
    changed significantly or if patterns are causing issues.

    Response JSON:
        {
            "success": true,
            "message": "Learned patterns cleared"
        }
    """
    try:
        service = get_service()

        # Access the query learner to clear patterns
        service._query_learner.clear_cache(connection_id)

        logger.info(f"Cleared learned patterns for connection {connection_id}")

        return jsonify({
            'success': True,
            'message': 'Learned patterns cleared'
        })

    except Exception as e:
        logger.error(f"Error clearing learned joins for connection {connection_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# Schema Change Detection Endpoints
# =============================================================================

@sql_chat_bp.route('/connections/<connection_id>/schema-changed', methods=['GET'])
def check_schema_changed(connection_id: str):
    """
    Check if database schema has changed since last introspection.

    Uses fast fingerprint comparison (~10ms) instead of full
    schema introspection (500-2000ms).

    Response JSON:
        {
            "success": true,
            "changed": false,
            "fingerprint": "abc123..."
        }
    """
    try:
        service = get_service()

        # Get engine for this connection
        connection = service._connections.get_connection(connection_id)
        if not connection:
            return jsonify({
                'success': False,
                'error': 'Connection not found'
            }), 404

        engine = service._connections.get_engine(connection)
        if not engine:
            return jsonify({
                'success': False,
                'error': 'Could not create database engine'
            }), 400

        # Check if schema changed
        changed = service._schema.has_schema_changed(engine, connection_id)
        fingerprint = service._schema.get_fingerprint(engine)

        return jsonify({
            'success': True,
            'changed': changed,
            'fingerprint': fingerprint
        })

    except Exception as e:
        logger.error(f"Error checking schema change for connection {connection_id}: {e}")
        return jsonify({
            'success': False,
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
