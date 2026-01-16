"""API route modules."""

from .chat import create_chat_routes
from .chat_v2 import create_chat_v2_routes
from .web_content import create_web_content_routes
from .studio import create_studio_routes
from .vision import create_vision_routes
from .transformations import create_transformation_routes
from .agents import create_agent_routes
from .multi_notebook import create_multi_notebook_routes
from .analytics import create_analytics_routes
from .sql_chat import create_sql_chat_routes
from .query import create_query_routes
from .admin import create_admin_routes
from .settings import create_settings_routes

__all__ = [
    'create_chat_routes',
    'create_chat_v2_routes',
    'create_web_content_routes',
    'create_studio_routes',
    'create_vision_routes',
    'create_transformation_routes',
    'create_agent_routes',
    'create_multi_notebook_routes',
    'create_analytics_routes',
    'create_sql_chat_routes',
    'create_query_routes',
    'create_admin_routes',
    'create_settings_routes',
]
