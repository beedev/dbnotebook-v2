"""Common utilities for SQL Chat routes.

Provides shared functions and classes used across all SQL Chat route modules.
"""

import json
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from flask import request

from dbnotebook.core.constants import DEFAULT_USER_ID

logger = logging.getLogger(__name__)


class SQLChatJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for SQL Chat results.

    Handles special types that standard JSON encoder can't serialize:
    - UUID -> string
    - datetime/date -> ISO format string
    - Decimal -> float
    - bytes -> UTF-8 decoded string
    """

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


# SQL Chat service instance (initialized in create_sql_chat_routes)
_sql_chat_service = None


def set_service(service) -> None:
    """Set the SQL Chat service instance.

    Called during route registration.

    Args:
        service: SQLChatService instance
    """
    global _sql_chat_service
    _sql_chat_service = service


def get_service():
    """Get the SQL Chat service instance.

    Returns:
        SQLChatService instance

    Raises:
        RuntimeError: If service not initialized
    """
    global _sql_chat_service
    if _sql_chat_service is None:
        raise RuntimeError("SQLChatService not initialized")
    return _sql_chat_service


def get_current_user_id() -> str:
    """Get current user ID from request context.

    Multi-user safe: Checks request body/args for user_id, falls back to default.
    This enables multi-user support while maintaining backward compatibility.

    Priority:
    1. Request body 'user_id' or 'userId'
    2. Request query parameter 'user_id'
    3. Default user ID (for single-user deployments)

    Returns:
        User ID string
    """
    # Check request body (for POST/PUT requests)
    if request.method in ['POST', 'PUT', 'PATCH']:
        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id') or data.get('userId')
        if user_id:
            return str(user_id)

    # Check query parameters (for GET/DELETE requests)
    user_id = request.args.get('user_id') or request.args.get('userId')
    if user_id:
        return str(user_id)

    # Fall back to default for backward compatibility
    return DEFAULT_USER_ID
