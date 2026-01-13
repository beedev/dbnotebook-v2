"""Admin API routes for RBAC management.

Provides endpoints for managing:
- User roles (assign/remove)
- Notebook access (grant/revoke)
- SQL connection access (grant/revoke)

All endpoints require admin permission.
"""

import logging
from flask import Blueprint, request, jsonify
from uuid import UUID

from dbnotebook.core.auth.rbac import (
    RBACService,
    AccessLevel,
    Permission,
    require_permission,
    get_rbac_service,
)
from dbnotebook.core.db.models import User, Role, Notebook, DatabaseConnection

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def create_admin_routes(app, db_manager, notebook_manager):
    """Create admin API routes.

    Args:
        app: Flask application instance
        db_manager: DatabaseManager instance
        notebook_manager: NotebookManager instance
    """

    # ========== Role Management ==========

    @admin_bp.route("/roles", methods=["GET"])
    @require_permission(Permission.MANAGE_ROLES)
    def list_roles():
        """List all available roles.

        Response JSON:
            {
                "success": true,
                "roles": [
                    {
                        "role_id": "uuid",
                        "name": "admin",
                        "description": "Full access",
                        "permissions": ["manage_users", ...]
                    }
                ]
            }
        """
        try:
            session = db_manager.get_session()
            roles = session.query(Role).all()

            role_list = []
            for role in roles:
                role_list.append({
                    "role_id": str(role.role_id),
                    "name": role.name,
                    "description": role.description,
                    "permissions": role.permissions or [],
                    "created_at": role.created_at.isoformat() if role.created_at else None
                })

            return jsonify({
                "success": True,
                "roles": role_list
            })
        except Exception as e:
            logger.error(f"Error listing roles: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @admin_bp.route("/users", methods=["GET"])
    @require_permission(Permission.MANAGE_USERS)
    def list_users():
        """List all users with their roles.

        Response JSON:
            {
                "success": true,
                "users": [
                    {
                        "user_id": "uuid",
                        "username": "john",
                        "email": "john@example.com",
                        "roles": ["user", "viewer"]
                    }
                ]
            }
        """
        try:
            session = db_manager.get_session()
            users = session.query(User).all()
            rbac = RBACService(session)

            user_list = []
            for user in users:
                roles = rbac.get_user_roles(str(user.user_id))
                user_list.append({
                    "user_id": str(user.user_id),
                    "username": user.username,
                    "email": user.email,
                    "roles": [r.name for r in roles],
                    "created_at": user.created_at.isoformat() if user.created_at else None
                })

            return jsonify({
                "success": True,
                "users": user_list
            })
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @admin_bp.route("/users/<user_id>/role", methods=["POST"])
    @require_permission(Permission.MANAGE_ROLES)
    def assign_role(user_id: str):
        """Assign a role to a user.

        Request JSON:
            {
                "role_name": "user"  # or "admin", "viewer"
            }

        Response JSON:
            {
                "success": true,
                "message": "Role assigned successfully"
            }
        """
        try:
            data = request.get_json() or {}
            role_name = data.get("role_name")

            if not role_name:
                return jsonify({
                    "success": False,
                    "error": "role_name is required"
                }), 400

            session = db_manager.get_session()
            rbac = RBACService(session)

            # Get the assigner's user_id from request
            assigner_id = request.headers.get("X-User-ID")
            if not assigner_id:
                assigner_id = data.get("assigned_by")

            success = rbac.assign_role(user_id, role_name, assigned_by=assigner_id)

            if success:
                return jsonify({
                    "success": True,
                    "message": f"Role '{role_name}' assigned to user {user_id}"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": f"Role '{role_name}' not found"
                }), 404

        except Exception as e:
            logger.error(f"Error assigning role: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @admin_bp.route("/users/<user_id>/role/<role_name>", methods=["DELETE"])
    @require_permission(Permission.MANAGE_ROLES)
    def remove_role(user_id: str, role_name: str):
        """Remove a role from a user.

        Response JSON:
            {
                "success": true,
                "message": "Role removed successfully"
            }
        """
        try:
            session = db_manager.get_session()
            rbac = RBACService(session)

            success = rbac.remove_role(user_id, role_name)

            return jsonify({
                "success": True,
                "message": f"Role '{role_name}' removed from user {user_id}"
            })

        except Exception as e:
            logger.error(f"Error removing role: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    # ========== Notebook Access Management ==========

    @admin_bp.route("/notebooks", methods=["POST"])
    @require_permission(Permission.MANAGE_NOTEBOOKS)
    def create_notebook():
        """Create a notebook for any user (admin only).

        Request JSON:
            {
                "name": "Notebook Name",
                "user_id": "uuid"  # Owner of the notebook
            }

        Response JSON:
            {
                "success": true,
                "notebook_id": "uuid",
                "name": "Notebook Name"
            }
        """
        try:
            data = request.get_json() or {}
            name = data.get("name")
            owner_id = data.get("user_id")

            if not name:
                return jsonify({
                    "success": False,
                    "error": "name is required"
                }), 400

            if not owner_id:
                return jsonify({
                    "success": False,
                    "error": "user_id is required"
                }), 400

            notebook = notebook_manager.create_notebook(name, owner_id)

            return jsonify({
                "success": True,
                "notebook_id": str(notebook.notebook_id),
                "name": notebook.name
            })

        except Exception as e:
            logger.error(f"Error creating notebook: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @admin_bp.route("/notebooks/<notebook_id>/access", methods=["GET"])
    @require_permission(Permission.MANAGE_NOTEBOOKS)
    def list_notebook_access(notebook_id: str):
        """List all users with access to a notebook.

        Response JSON:
            {
                "success": true,
                "notebook_id": "uuid",
                "users": [
                    {
                        "user_id": "uuid",
                        "username": "john",
                        "email": "john@example.com",
                        "access_level": "editor",
                        "granted_at": "2024-01-01T00:00:00Z"
                    }
                ]
            }
        """
        try:
            session = db_manager.get_session()
            rbac = RBACService(session)

            users = rbac.list_notebook_users(notebook_id)

            return jsonify({
                "success": True,
                "notebook_id": notebook_id,
                "users": users
            })

        except Exception as e:
            logger.error(f"Error listing notebook access: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @admin_bp.route("/notebooks/<notebook_id>/access", methods=["POST"])
    @require_permission(Permission.MANAGE_NOTEBOOKS)
    def grant_notebook_access(notebook_id: str):
        """Grant a user access to a notebook.

        Request JSON:
            {
                "user_id": "uuid",
                "access_level": "viewer"  # or "editor", "owner"
            }

        Response JSON:
            {
                "success": true,
                "message": "Access granted successfully"
            }
        """
        try:
            data = request.get_json() or {}
            user_id = data.get("user_id")
            access_level_str = data.get("access_level", "viewer")

            if not user_id:
                return jsonify({
                    "success": False,
                    "error": "user_id is required"
                }), 400

            # Validate access level
            try:
                access_level = AccessLevel(access_level_str)
            except ValueError:
                return jsonify({
                    "success": False,
                    "error": f"Invalid access_level. Must be one of: viewer, editor, owner"
                }), 400

            session = db_manager.get_session()
            rbac = RBACService(session)

            # Get granter's user_id
            granter_id = request.headers.get("X-User-ID")
            if not granter_id:
                granter_id = data.get("granted_by")

            success = rbac.grant_notebook_access(
                notebook_id=notebook_id,
                user_id=user_id,
                access_level=access_level,
                granted_by=granter_id
            )

            if success:
                return jsonify({
                    "success": True,
                    "message": f"Granted {access_level.value} access to notebook {notebook_id} for user {user_id}"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Failed to grant access"
                }), 500

        except Exception as e:
            logger.error(f"Error granting notebook access: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @admin_bp.route("/notebooks/<notebook_id>/access/<user_id>", methods=["DELETE"])
    @require_permission(Permission.MANAGE_NOTEBOOKS)
    def revoke_notebook_access(notebook_id: str, user_id: str):
        """Revoke a user's access to a notebook.

        Response JSON:
            {
                "success": true,
                "message": "Access revoked successfully"
            }
        """
        try:
            session = db_manager.get_session()
            rbac = RBACService(session)

            success = rbac.revoke_notebook_access(notebook_id, user_id)

            return jsonify({
                "success": True,
                "message": f"Revoked access to notebook {notebook_id} for user {user_id}"
            })

        except Exception as e:
            logger.error(f"Error revoking notebook access: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    # ========== SQL Connection Access Management ==========

    @admin_bp.route("/sql-connections/<connection_id>/access", methods=["GET"])
    @require_permission(Permission.MANAGE_CONNECTIONS)
    def list_sql_connection_access(connection_id: str):
        """List all users with access to a SQL connection.

        Response JSON:
            {
                "success": true,
                "connection_id": "uuid",
                "users": [
                    {
                        "user_id": "uuid",
                        "username": "john",
                        "access_level": "user",
                        "granted_at": "2024-01-01T00:00:00Z"
                    }
                ]
            }
        """
        try:
            from dbnotebook.core.db.models import SQLConnectionAccess

            session = db_manager.get_session()

            accesses = session.query(SQLConnectionAccess).filter(
                SQLConnectionAccess.connection_id == UUID(connection_id)
            ).all()

            users = []
            for access in accesses:
                user = session.query(User).filter(
                    User.user_id == access.user_id
                ).first()
                if user:
                    users.append({
                        "user_id": str(access.user_id),
                        "username": user.username,
                        "email": user.email,
                        "access_level": access.access_level,
                        "granted_at": access.granted_at.isoformat() if access.granted_at else None
                    })

            return jsonify({
                "success": True,
                "connection_id": connection_id,
                "users": users
            })

        except Exception as e:
            logger.error(f"Error listing SQL connection access: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @admin_bp.route("/sql-connections/<connection_id>/access", methods=["POST"])
    @require_permission(Permission.MANAGE_CONNECTIONS)
    def grant_sql_connection_access(connection_id: str):
        """Grant a user access to a SQL connection.

        Request JSON:
            {
                "user_id": "uuid",
                "access_level": "user"  # or "owner"
            }

        Response JSON:
            {
                "success": true,
                "message": "Access granted successfully"
            }
        """
        try:
            data = request.get_json() or {}
            user_id = data.get("user_id")
            access_level_str = data.get("access_level", "user")

            if not user_id:
                return jsonify({
                    "success": False,
                    "error": "user_id is required"
                }), 400

            # Validate access level
            try:
                access_level = AccessLevel(access_level_str)
            except ValueError:
                return jsonify({
                    "success": False,
                    "error": f"Invalid access_level. Must be one of: user, owner"
                }), 400

            session = db_manager.get_session()
            rbac = RBACService(session)

            # Get granter's user_id
            granter_id = request.headers.get("X-User-ID")
            if not granter_id:
                granter_id = data.get("granted_by")

            success = rbac.grant_sql_connection_access(
                connection_id=connection_id,
                user_id=user_id,
                access_level=access_level,
                granted_by=granter_id
            )

            if success:
                return jsonify({
                    "success": True,
                    "message": f"Granted {access_level.value} access to connection {connection_id} for user {user_id}"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Failed to grant access"
                }), 500

        except Exception as e:
            logger.error(f"Error granting SQL connection access: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @admin_bp.route("/sql-connections/<connection_id>/access/<user_id>", methods=["DELETE"])
    @require_permission(Permission.MANAGE_CONNECTIONS)
    def revoke_sql_connection_access(connection_id: str, user_id: str):
        """Revoke a user's access to a SQL connection.

        Response JSON:
            {
                "success": true,
                "message": "Access revoked successfully"
            }
        """
        try:
            session = db_manager.get_session()
            rbac = RBACService(session)

            success = rbac.revoke_sql_connection_access(connection_id, user_id)

            return jsonify({
                "success": True,
                "message": f"Revoked access to connection {connection_id} for user {user_id}"
            })

        except Exception as e:
            logger.error(f"Error revoking SQL connection access: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    # Register blueprint
    app.register_blueprint(admin_bp)

    logger.info("Admin routes registered")
    return app
