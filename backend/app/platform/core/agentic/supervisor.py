"""
LangGraph supervisor for progressive diet plan.
Collects state, applies policy, and runs NCP pipeline (full or partial).
"""
import logging
from typing import Any, Dict, Literal
from uuid import UUID

from sqlalchemy.orm import Session

from app.platform.core.agentic.state import SupervisorState
from app.platform.core.orchestration.ncp_orchestrator import NCPOrchestrator
from app.platform.data.repositories.platform_monitoring_record_repository import (
    PlatformMonitoringRecordRepository,
)

logger = logging.getLogger(__name__)

PipelineMode = Literal["full", "from_target", "from_meal_structure", "existing_only"]


def collect_state_node(state: SupervisorState, config: dict = None) -> Dict[str, Any]:
    """
    Load monitoring records and merge user_feedback into client_preferences.
    Requires db in config.configurable or state["_db"].
    """
    configurable = (config or {}).get("configurable") or {}
    db: Session = configurable.get("db") or state.get("_db")
    if not db:
        return {"error": "db not provided in config.configurable"}

    client_id_str = state.get("client_id")
    assessment_id_str = state.get("assessment_id")
    if not client_id_str or not assessment_id_str:
        return {"error": "client_id and assessment_id required"}

    client_id = UUID(client_id_str)
    assessment_id = UUID(assessment_id_str)

    monitoring_repo = PlatformMonitoringRecordRepository(db)
    records = monitoring_repo.get_by_client_id(client_id)
    monitoring_records = [
        {
            "metric_type": r.metric_type,
            "metric_value": r.metric_value or {},
            "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
        }
        for r in records
    ]

    user_feedback = state.get("user_feedback") or {}
    client_preferences = dict(user_feedback)

    return {
        "monitoring_records": monitoring_records,
        "client_preferences": client_preferences,
        # Keep explicit so LangGraph state always carries feedback for policy_node
        "user_feedback": user_feedback,
    }


def policy_node(state: SupervisorState) -> Dict[str, Any]:
    """
    Decide pipeline mode from user_feedback and monitoring (MVP: deterministic rules).
    """
    user_feedback = state.get("user_feedback") or {}
    feedback_text = (user_feedback.get("text") or user_feedback.get("message") or "").lower()
    feedback_keys = [k.lower() for k in (user_feedback.keys() if isinstance(user_feedback, dict) else [])]

    if user_feedback.get("force_full_pipeline"):
        return {"pipeline_mode": "full"}

    if any(
        x in feedback_text or x in str(feedback_keys)
        for x in ("target", "calorie", "calories", "macro", "energy target", "reduce intake", "increase intake")
    ):
        return {"pipeline_mode": "from_target"}

    if any(
        x in feedback_text or x in str(feedback_keys)
        for x in ("meal structure", "meal count", "meals", "energy distribution", "timing", "breakfast", "lunch", "dinner")
    ):
        return {"pipeline_mode": "from_meal_structure"}

    return {"pipeline_mode": "existing_only"}


def execute_pipeline_node(state: SupervisorState, config: dict = None) -> Dict[str, Any]:
    """
    Run NCP pipeline per policy; persist plan with program_id/week_index when provided.
    """
    configurable = (config or {}).get("configurable") or {}
    pipeline_mode: PipelineMode = state.get("pipeline_mode") or "existing_only"

    db: Session = configurable.get("db") or state.get("_db")
    if not db:
        return {"error": "db not provided in config.configurable", "pipeline_mode": pipeline_mode}

    client_id_str = state.get("client_id")
    assessment_id_str = state.get("assessment_id")
    if not client_id_str or not assessment_id_str:
        return {
            "error": "client_id and assessment_id required",
            "pipeline_mode": pipeline_mode,
        }

    client_id = UUID(client_id_str)
    assessment_id = UUID(assessment_id_str)
    program_id = UUID(state["program_id"]) if state.get("program_id") else None
    week_index = state.get("week_index")
    client_preferences = state.get("client_preferences") or {}
    enable_ayurveda_flag = state.get("enable_ayurveda", True)
    if not isinstance(enable_ayurveda_flag, bool):
        enable_ayurveda_flag = True
    skip_recipe_llm = bool(state.get("skip_recipe_llm", False))

    try:
        orchestrator = NCPOrchestrator(
            db=db, client_id=client_id, enable_ayurveda=enable_ayurveda_flag
        )
        common_kw = {
            "assessment_id": assessment_id,
            "client_preferences": client_preferences,
            "program_id": program_id,
            "week_index": week_index,
            "skip_recipe_llm": skip_recipe_llm,
            "enable_ayurveda": enable_ayurveda_flag,
        }

        if pipeline_mode == "full":
            pipeline_result = orchestrator.execute_full_pipeline(**common_kw)
        elif pipeline_mode == "from_target":
            pipeline_result = orchestrator.run_from_target(**common_kw)
        elif pipeline_mode == "from_meal_structure":
            pipeline_result = orchestrator.run_from_meal_structure(**common_kw)
        else:
            pipeline_result = orchestrator.run_from_existing(**common_kw)

        intervention = pipeline_result.get("intervention")
        recipe = pipeline_result.get("recipe")
        plan_id = intervention.plan_id if intervention else None
        plan_version = intervention.plan_version if intervention else None

        # Top-level keys: LangGraph 1.x merge makes nested-only "result" easy to lose
        # when building the API response (run_weekly_plan).
        payload = {
            "pipeline_mode": pipeline_mode,
            "plan_id": str(plan_id) if plan_id else None,
            "plan_version": plan_version,
            "recipe_context": recipe,
        }
        return {
            **payload,
            "error": None,
            "result": payload,
        }
    except Exception as e:
        logger.exception("Supervisor execute_pipeline_node failed")
        return {
            "pipeline_mode": pipeline_mode,
            "plan_id": None,
            "plan_version": None,
            "error": str(e),
            "result": {},
        }


def build_supervisor_graph() -> Any:
    """Build the supervisor LangGraph: collect_state -> policy -> execute -> END."""
    try:
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "The 'langgraph' package is required for POST /plans/generate-week. "
            "Install dependencies: pip install langgraph"
        ) from e

    graph = StateGraph(SupervisorState)

    graph.add_node("collect_state", collect_state_node)
    graph.add_node("policy", policy_node)
    graph.add_node("execute", execute_pipeline_node)

    graph.set_entry_point("collect_state")
    graph.add_edge("collect_state", "policy")
    graph.add_edge("policy", "execute")
    graph.add_edge("execute", END)

    return graph


def run_weekly_plan(
    db: Session,
    client_id: UUID,
    assessment_id: UUID,
    user_feedback: Dict[str, Any],
    program_id: UUID | None = None,
    week_index: int | None = None,
    enable_ayurveda: bool = True,
    skip_recipe_llm: bool = False,
) -> Dict[str, Any]:
    """
    Run the supervisor graph for weekly plan generation.
    Returns result dict with plan_id, plan_version, pipeline_mode, and optional error.
    """
    initial_state: SupervisorState = {
        "client_id": str(client_id),
        "assessment_id": str(assessment_id),
        "program_id": str(program_id) if program_id else None,
        "week_index": week_index,
        "user_feedback": user_feedback,
        "enable_ayurveda": enable_ayurveda,
        "skip_recipe_llm": skip_recipe_llm,
        "_db": db,
    }
    config = {"configurable": {"db": db}}

    compiled = build_supervisor_graph().compile()
    final_state = compiled.invoke(initial_state, config=config)
    if not isinstance(final_state, dict):
        final_state = dict(final_state)

    error = final_state.get("error")
    nested = final_state.get("result") if isinstance(final_state.get("result"), dict) else {}

    out: Dict[str, Any] = {
        "pipeline_mode": final_state.get("pipeline_mode") or nested.get("pipeline_mode"),
        "plan_id": final_state.get("plan_id") if final_state.get("plan_id") is not None else nested.get("plan_id"),
        "plan_version": final_state.get("plan_version")
        if final_state.get("plan_version") is not None
        else nested.get("plan_version"),
    }
    rc = final_state.get("recipe_context")
    if rc is None:
        rc = nested.get("recipe_context")
    if rc is not None:
        out["recipe_context"] = rc

    if error:
        out["error"] = error
    return out
