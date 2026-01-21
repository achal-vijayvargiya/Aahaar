"""
Legacy routers compatibility layer.
Re-exports routers from app.legacy.routers for backward compatibility.
"""
# Re-export all routers from legacy.routers to maintain backward compatibility
from app.legacy.routers import (
    auth,
    users,
    clients,
    appointments,
    health_profiles,
    dosha_quiz,
    gut_health_quiz,
    comprehensive_health_profiles,
    food_suitability,
    diet_plans,
)

__all__ = [
    "auth",
    "users",
    "clients",
    "appointments",
    "health_profiles",
    "dosha_quiz",
    "gut_health_quiz",
    "diet_plans",
    "comprehensive_health_profiles",
    "food_suitability",
]

