"""Authentication API routes.

Provides endpoints for:
- Login/logout
- Current user info
- Password change
- API key regeneration
"""

import logging
from flask import Blueprint, request, jsonify, session

from dbnotebook.core.auth import AuthService, RBACService

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def create_auth_routes(app, db_manager):
    """Create authentication API routes.

    Args:
        app: Flask application instance
        db_manager: DatabaseManager instance
    """

    @auth_bp.route("/login", methods=["POST"])
    def login():
        """Login with username and password.

        Request JSON:
            {
                "username": "admin",
                "password": "admin123"
            }

        Response JSON:
            {
                "success": true,
                "user": {
                    "user_id": "uuid",
                    "username": "admin",
                    "email": "admin@example.com",
                    "roles": ["admin"],
                    "api_key": "dbn_..."
                }
            }
        """
        try:
            data = request.get_json() or {}
            username = data.get("username")
            password = data.get("password")

            if not username or not password:
                return jsonify({
                    "success": False,
                    "error": "Username and password are required"
                }), 400

            with db_manager.get_session() as db_session:
                auth_service = AuthService(db_session)
                user = auth_service.login(username, password)

                if not user:
                    return jsonify({
                        "success": False,
                        "error": "Invalid username or password"
                    }), 401

                # Get user roles
                rbac_service = RBACService(db_session)
                roles = rbac_service.get_user_roles(str(user.user_id))
                role_names = [r.name for r in roles]

                # Store user in session
                session["user_id"] = str(user.user_id)
                session["username"] = user.username

                return jsonify({
                    "success": True,
                    "user": {
                        "user_id": str(user.user_id),
                        "username": user.username,
                        "email": user.email,
                        "roles": role_names,
                        "api_key": user.api_key
                    }
                })

        except Exception as e:
            logger.error(f"Login error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @auth_bp.route("/logout", methods=["POST"])
    def logout():
        """Logout current user.

        Response JSON:
            {
                "success": true,
                "message": "Logged out successfully"
            }
        """
        session.clear()
        return jsonify({
            "success": True,
            "message": "Logged out successfully"
        })

    @auth_bp.route("/me", methods=["GET"])
    def get_current_user():
        """Get current logged-in user info.

        Response JSON:
            {
                "success": true,
                "authenticated": true,
                "user": {
                    "user_id": "uuid",
                    "username": "admin",
                    "email": "admin@example.com",
                    "roles": ["admin"],
                    "api_key": "dbn_..."
                }
            }
        """
        try:
            user_id = session.get("user_id")

            if not user_id:
                return jsonify({
                    "success": True,
                    "authenticated": False,
                    "user": None
                })

            with db_manager.get_session() as db_session:
                auth_service = AuthService(db_session)
                user = auth_service.get_user_by_id(user_id)

                if not user:
                    session.clear()
                    return jsonify({
                        "success": True,
                        "authenticated": False,
                        "user": None
                    })

                # Get user roles
                rbac_service = RBACService(db_session)
                roles = rbac_service.get_user_roles(str(user.user_id))
                role_names = [r.name for r in roles]

                return jsonify({
                    "success": True,
                    "authenticated": True,
                    "user": {
                        "user_id": str(user.user_id),
                        "username": user.username,
                        "email": user.email,
                        "roles": role_names,
                        "api_key": user.api_key
                    }
                })

        except Exception as e:
            logger.error(f"Get current user error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @auth_bp.route("/password", methods=["POST"])
    def change_password():
        """Change current user's password.

        Request JSON:
            {
                "old_password": "current",
                "new_password": "newpassword"
            }

        Response JSON:
            {
                "success": true,
                "message": "Password changed successfully"
            }
        """
        try:
            user_id = session.get("user_id")

            if not user_id:
                return jsonify({
                    "success": False,
                    "error": "Not authenticated"
                }), 401

            data = request.get_json() or {}
            old_password = data.get("old_password")
            new_password = data.get("new_password")

            if not old_password or not new_password:
                return jsonify({
                    "success": False,
                    "error": "Old password and new password are required"
                }), 400

            if len(new_password) < 6:
                return jsonify({
                    "success": False,
                    "error": "New password must be at least 6 characters"
                }), 400

            with db_manager.get_session() as db_session:
                auth_service = AuthService(db_session)
                success = auth_service.change_password(user_id, old_password, new_password)

                if not success:
                    return jsonify({
                        "success": False,
                        "error": "Invalid old password"
                    }), 400

                return jsonify({
                    "success": True,
                    "message": "Password changed successfully"
                })

        except Exception as e:
            logger.error(f"Change password error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @auth_bp.route("/api-key", methods=["POST"])
    def regenerate_api_key():
        """Regenerate API key for current user.

        Response JSON:
            {
                "success": true,
                "api_key": "dbn_newapikey..."
            }
        """
        try:
            user_id = session.get("user_id")

            if not user_id:
                return jsonify({
                    "success": False,
                    "error": "Not authenticated"
                }), 401

            with db_manager.get_session() as db_session:
                auth_service = AuthService(db_session)
                new_api_key = auth_service.generate_api_key(user_id)

                if not new_api_key:
                    return jsonify({
                        "success": False,
                        "error": "Failed to generate API key"
                    }), 500

                return jsonify({
                    "success": True,
                    "api_key": new_api_key
                })

        except Exception as e:
            logger.error(f"Regenerate API key error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    # Register blueprint
    app.register_blueprint(auth_bp)

    logger.info("Auth routes registered")
    return app
