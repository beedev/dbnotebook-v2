"""UI package for DBNotebook.

Provides the Flask-based web interface and route registration utilities.

Usage:
    from dbnotebook.ui import FlaskChatbotUI, register_all_routes

    # Full UI with all features
    ui = FlaskChatbotUI(pipeline, db_manager=db_manager, notebook_manager=notebook_manager)
    ui.run()

    # Or use route registration separately
    register_all_routes(app, pipeline, db_manager, notebook_manager)
"""

from .web import FlaskChatbotUI
from .route_registration import register_all_routes, register_notebook_routes

__all__ = [
    "FlaskChatbotUI",
    "register_all_routes",
    "register_notebook_routes",
]
