"""
Platform API Module.
All API route definitions for the platform.
"""

from app.platform.api.auth import router as auth_router
from app.platform.api.clients import router as clients_router
from app.platform.api.assessments import router as assessments_router
from app.platform.api.plans import router as plans_router
from app.platform.api.admin import router as admin_router
from app.platform.api.quizzes import router as quizzes_router

__all__ = [
    "auth_router",
    "clients_router",
    "assessments_router",
    "plans_router",
    "admin_router",
    "quizzes_router",
]
