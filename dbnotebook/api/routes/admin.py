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
from dbnotebook.core.auth.auth_service import AuthService
from dbnotebook.core.db.models import User, Role, Notebook, DatabaseConnection
from dbnotebook.core.constants import DEFAULT_USER_ID

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
        """List all available roles."""
        try:
            with db_manager.get_session() as session:
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
        """List all users with their roles."""
        try:
            with db_manager.get_session() as session:
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
                        "api_key": user.api_key,
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
        """Assign a role to a user."""
        try:
            data = request.get_json() or {}
            role_name = data.get("role_name")

            if not role_name:
                return jsonify({
                    "success": False,
                    "error": "role_name is required"
                }), 400

            with db_manager.get_session() as session:
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
        """Remove a role from a user."""
        try:
            with db_manager.get_session() as session:
                rbac = RBACService(session)
                success = rbac.remove_role(user_id, role_name)

                return jsonify({
                    "success": True,
                    "message": f"Role '{role_name}' removed from user {user_id}"
                })

        except Exception as e:
            logger.error(f"Error removing role: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    # ========== User Management ==========

    @admin_bp.route("/users", methods=["POST"])
    @require_permission(Permission.MANAGE_USERS)
    def create_user():
        """Create a new user."""
        try:
            data = request.get_json() or {}
            username = data.get("username")
            email = data.get("email")
            password = data.get("password")
            role_name = data.get("role", "user")

            if not username:
                return jsonify({
                    "success": False,
                    "error": "username is required"
                }), 400

            if not email:
                return jsonify({
                    "success": False,
                    "error": "email is required"
                }), 400

            if not password:
                return jsonify({
                    "success": False,
                    "error": "password is required"
                }), 400

            if len(password) < 6:
                return jsonify({
                    "success": False,
                    "error": "password must be at least 6 characters"
                }), 400

            with db_manager.get_session() as session:
                auth_service = AuthService(session)

                # Create user
                user = auth_service.create_user(
                    username=username,
                    email=email,
                    password=password,
                    generate_api_key=True
                )

                if not user:
                    return jsonify({
                        "success": False,
                        "error": "Username or email already exists"
                    }), 409

                # Assign role
                rbac = RBACService(session)
                assigner_id = request.headers.get("X-User-ID")
                rbac.assign_role(str(user.user_id), role_name, assigned_by=assigner_id)

                return jsonify({
                    "success": True,
                    "user": {
                        "user_id": str(user.user_id),
                        "username": user.username,
                        "email": user.email,
                        "api_key": user.api_key
                    }
                })

        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @admin_bp.route("/users/<user_id>/password", methods=["PUT"])
    @require_permission(Permission.MANAGE_USERS)
    def reset_user_password(user_id: str):
        """Reset a user's password (admin operation)."""
        try:
            data = request.get_json() or {}
            new_password = data.get("new_password")

            if not new_password:
                return jsonify({
                    "success": False,
                    "error": "new_password is required"
                }), 400

            if len(new_password) < 6:
                return jsonify({
                    "success": False,
                    "error": "password must be at least 6 characters"
                }), 400

            with db_manager.get_session() as session:
                auth_service = AuthService(session)
                success = auth_service.set_password(user_id, new_password)

                if not success:
                    return jsonify({
                        "success": False,
                        "error": "User not found"
                    }), 404

                return jsonify({
                    "success": True,
                    "message": "Password reset successfully"
                })

        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @admin_bp.route("/users/<user_id>/api-key", methods=["POST"])
    @require_permission(Permission.MANAGE_USERS)
    def generate_user_api_key(user_id: str):
        """Generate a new API key for a user."""
        try:
            with db_manager.get_session() as session:
                auth_service = AuthService(session)
                new_api_key = auth_service.generate_api_key(user_id)

                if not new_api_key:
                    return jsonify({
                        "success": False,
                        "error": "User not found"
                    }), 404

                return jsonify({
                    "success": True,
                    "api_key": new_api_key
                })

        except Exception as e:
            logger.error(f"Error generating API key: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @admin_bp.route("/users/<user_id>", methods=["DELETE"])
    @require_permission(Permission.MANAGE_USERS)
    def delete_user(user_id: str):
        """Delete a user (cannot delete default admin)."""
        try:
            # Prevent deleting default admin
            if user_id == DEFAULT_USER_ID:
                return jsonify({
                    "success": False,
                    "error": "Cannot delete the default admin user"
                }), 403

            with db_manager.get_session() as session:
                user = session.query(User).filter(User.user_id == UUID(user_id)).first()

                if not user:
                    return jsonify({
                        "success": False,
                        "error": "User not found"
                    }), 404

                session.delete(user)

                return jsonify({
                    "success": True,
                    "message": "User deleted successfully"
                })

        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    # ========== Notebook Access Management ==========

    @admin_bp.route("/notebooks", methods=["GET"])
    @require_permission(Permission.MANAGE_NOTEBOOKS)
    def list_all_notebooks():
        """List all notebooks (admin view)."""
        try:
            with db_manager.get_session() as session:
                notebooks = session.query(Notebook).all()

                notebook_list = []
                for nb in notebooks:
                    # Get owner info
                    owner = session.query(User).filter(User.user_id == nb.user_id).first()
                    owner_name = owner.username if owner else "Unknown"

                    # Check if global (owned by default admin)
                    is_global = str(nb.user_id) == DEFAULT_USER_ID

                    notebook_list.append({
                        "notebook_id": str(nb.notebook_id),
                        "name": nb.name,
                        "user_id": str(nb.user_id),
                        "username": owner_name,
                        "is_global": is_global,
                        "document_count": nb.document_count or 0,
                        "created_at": nb.created_at.isoformat() if nb.created_at else None
                    })

                return jsonify({
                    "success": True,
                    "notebooks": notebook_list
                })

        except Exception as e:
            logger.error(f"Error listing notebooks: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @admin_bp.route("/notebooks", methods=["POST"])
    @require_permission(Permission.MANAGE_NOTEBOOKS)
    def create_notebook():
        """Create a global notebook (owned by default admin)."""
        try:
            data = request.get_json() or {}
            name = data.get("name")

            if not name:
                return jsonify({
                    "success": False,
                    "error": "name is required"
                }), 400

            # Create as default admin's notebook (makes it global)
            # Note: create_notebook signature is (user_id, name, description) -> Dict with "id" key
            notebook_data = notebook_manager.create_notebook(DEFAULT_USER_ID, name)

            return jsonify({
                "success": True,
                "notebook_id": str(notebook_data["id"]),
                "name": notebook_data["name"]
            })

        except Exception as e:
            logger.error(f"Error creating notebook: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @admin_bp.route("/notebooks/<notebook_id>/access", methods=["GET"])
    @require_permission(Permission.MANAGE_NOTEBOOKS)
    def list_notebook_access(notebook_id: str):
        """List all users with access to a notebook."""
        try:
            with db_manager.get_session() as session:
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
        """Grant a user access to a notebook."""
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

            with db_manager.get_session() as session:
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
        """Revoke a user's access to a notebook."""
        try:
            with db_manager.get_session() as session:
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
        """List all users with access to a SQL connection."""
        try:
            from dbnotebook.core.db.models import SQLConnectionAccess

            with db_manager.get_session() as session:
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
        """Grant a user access to a SQL connection."""
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

            with db_manager.get_session() as session:
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
        """Revoke a user's access to a SQL connection."""
        try:
            with db_manager.get_session() as session:
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
