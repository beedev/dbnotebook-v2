"""API route modules."""

from .chat import create_chat_routes
from .web_content import create_web_content_routes
from .studio import create_studio_routes
from .vision import create_vision_routes
from .transformations import create_transformation_routes
# from .notebooks import create_notebook_routes  # TODO: MVP 2 - implement notebook routes
# from .documents import create_document_routes  # TODO: MVP 2 - implement document routes

__all__ = [
    'create_chat_routes',
    'create_web_content_routes',
    'create_studio_routes',
    'create_vision_routes',
    'create_transformation_routes',
    # 'create_notebook_routes',
    # 'create_document_routes',
]
