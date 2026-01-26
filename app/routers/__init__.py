"""
路由模块包
"""

from .embedding import router as embedding_router
from .vector_db import router as vector_db_router
from .search import router as search_router
from .storage import router as storage_router
from .agent import router as agent_router
from .social import router as social_router
from .image_recommendation import router as image_recommendation_router
from .image_edit import router as image_edit_router

__all__ = [
    "embedding_router",
    "vector_db_router",
    "search_router",
    "storage_router",
    "agent_router",
    "social_router",
    "image_recommendation_router",
    "image_edit_router",
]
