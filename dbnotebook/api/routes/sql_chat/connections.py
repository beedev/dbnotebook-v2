"""SQL Chat connection management routes.

Endpoints for database connection CRUD operations:
- Create new connections (PostgreSQL, MySQL, SQLite)
- List user's connections
- Test connection before saving
- Parse connection strings
- Delete connections
"""

import logging

from flask import Blueprint, request

from dbnotebook.api.core.response import (
    success_response, error_response, validation_error, not_found
)
from dbnotebook.core.sql_chat import MaskingPolicy

from .utils import get_service, get_current_user_id

logger = logging.getLogger(__name__)

# Blueprint for connection endpoints
connections_bp = Blueprint('sql_chat_connections', __name__)


@connections_bp.route('/connections', methods=['POST'])
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
            "schema": "public",  // Optional: PostgreSQL schema(s)
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
        schema = data.get('schema')

        # Validate required fields
        if not all([name, db_type, database]):
            return validation_error('Missing required fields: name, db_type, database')

        # Validate db_type
        if db_type not in ['postgresql', 'mysql', 'sqlite']:
            return validation_error(
                f'Unsupported database type: {db_type}. Supported: postgresql, mysql, sqlite'
            )

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
            return error_response(error, 400)

        logger.info(f"Database connection created: {name} (type={db_type})")

        return success_response({
            'connectionId': conn_id,
            'message': 'Connection created successfully'
        })

    except Exception as e:
        logger.error(f"Error creating connection: {e}")
        return error_response(str(e), 500)


@connections_bp.route('/connections', methods=['GET'])
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

        return success_response({
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
        return error_response(str(e), 500)


@connections_bp.route('/connections/test', methods=['POST'])
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
            "password": "secret",
            "schema": "public"  // Optional
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
        schema = data.get('schema')
        username = data.get('username', '')
        password = data.get('password', '')

        if not all([db_type, database]):
            return validation_error('Missing required fields: db_type, database')

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

        if success:
            return success_response({'message': message})
        else:
            return error_response(message, 400)

    except Exception as e:
        logger.error(f"Error testing connection: {e}")
        return error_response(str(e), 500)


@connections_bp.route('/connections/parse-string', methods=['POST'])
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
            return validation_error('connection_string is required')

        config, error = service.parse_connection_string(conn_string)

        if error:
            return error_response(error, 400)

        return success_response({'config': config})

    except Exception as e:
        logger.error(f"Error parsing connection string: {e}")
        return error_response(str(e), 500)


@connections_bp.route('/connections/<connection_id>', methods=['DELETE'])
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
            return not_found('Connection', connection_id)

        logger.info(f"Database connection deleted: {connection_id}")

        return success_response({'message': 'Connection deleted successfully'})

    except Exception as e:
        logger.error(f"Error deleting connection: {e}")
        return error_response(str(e), 500)
