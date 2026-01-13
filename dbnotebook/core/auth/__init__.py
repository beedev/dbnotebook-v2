"""Authentication and Authorization module.

Provides RBAC (Role-Based Access Control) for all features:
- API endpoints
- Notebook Chat
- SQL Chat

RBAC Strict Mode:
    Set RBAC_STRICT_MODE=true to enforce access control.
    When disabled (default), all users have access to all resources.
"""

from .rbac import (
    RBACService,
    AccessLevel,
    Permission,
    require_permission,
    require_notebook_access,
    require_sql_connection_access,
    get_rbac_service,
    check_notebook_access,
    check_multi_notebook_access,
    check_sql_connection_access,
)

__all__ = [
    "RBACService",
    "AccessLevel",
    "Permission",
    "require_permission",
    "require_notebook_access",
    "require_sql_connection_access",
    "get_rbac_service",
    "check_notebook_access",
    "check_multi_notebook_access",
    "check_sql_connection_access",
]
