"""
Supervisor graph state for progressive diet plan generation.
"""
from typing import Any, Dict, List, Optional, TypedDict

from typing_extensions import NotRequired


class SupervisorState(TypedDict, total=False):
    """State for the weekly plan supervisor graph."""

    client_id: str
    assessment_id: str
    program_id: Optional[str]
    week_index: Optional[int]
    user_feedback: Dict[str, Any]
    monitoring_records: List[Dict[str, Any]]
    client_preferences: Dict[str, Any]
    pipeline_mode: str  # "full" | "from_target" | "from_meal_structure" | "existing_only"
    enable_ayurveda: bool
    skip_recipe_llm: bool
    plan_id: NotRequired[Optional[str]]
    plan_version: NotRequired[Optional[int]]
    recipe_context: NotRequired[Any]
    result: Dict[str, Any]  # legacy nested payload; prefer top-level plan_* / pipeline_mode
    error: Optional[str]
