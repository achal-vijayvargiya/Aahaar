"""
Platform Assessments API Routes.
Assessment and intake endpoints for the platform.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.platform.data.repositories.platform_client_repository import PlatformClientRepository
from app.platform.data.repositories.platform_intake_repository import PlatformIntakeRepository
from app.platform.data.repositories.platform_assessment_repository import PlatformAssessmentRepository
from app.platform.data.repositories.platform_diagnosis_repository import PlatformDiagnosisRepository
from app.platform.data.repositories.platform_mnt_constraint_repository import PlatformMNTConstraintRepository
from app.platform.data.repositories.platform_nutrition_target_repository import PlatformNutritionTargetRepository
from app.platform.data.repositories.platform_meal_structure_repository import PlatformMealStructureRepository
from app.platform.data.repositories.platform_exchange_allocation_repository import PlatformExchangeAllocationRepository
from app.platform.data.repositories.platform_ayurveda_profile_repository import PlatformAyurvedaProfileRepository
from app.platform.data.repositories.platform_diet_plan_repository import PlatformDietPlanRepository
from app.platform.core.context import AssessmentContext, DiagnosisContext, MNTContext, TargetContext, MealStructureContext, ExchangeContext, AyurvedaContext, InterventionContext, RecipeContext
from app.platform.engines.diagnosis_engine.diagnosis_engine import DiagnosisEngine
from app.platform.engines.mnt_engine.mnt_engine import MNTEngine
from app.platform.engines.target_engine.target_engine import TargetEngine
from app.platform.engines.meal_structure_engine.meal_structure_engine import MealStructureEngine
from app.platform.engines.exchange_system_engine.exchange_system_engine import ExchangeSystemEngine
from app.platform.engines.ayurveda_engine.ayurveda_engine import AyurvedaEngine
from app.platform.engines.food_engine.food_engine import FoodEngine
from app.platform.engines.recipe_engine.meal_allocation_engine import MealAllocationEngine
from app.platform.engines.recipe_engine.recipe_generation_engine import RecipeGenerationEngine
from app.platform.data.repositories.platform_food_allocation_approval_repository import PlatformFoodAllocationApprovalRepository

router = APIRouter(prefix="/assessments", tags=["Platform Assessments"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _filter_approved_meals(
    meal_allocation: Dict[str, Any],
    approval_status_map: Dict[str, Dict[str, bool]]
) -> Dict[str, Any]:
    """
    Filter meal allocation to only include approved meals.
    
    Args:
        meal_allocation: Full meal allocation from Phase 1
        approval_status_map: {day_number: {meal_name: is_approved}}
        
    Returns:
        Filtered meal allocation with only approved meals
    """
    filtered_days = {}
    days = meal_allocation.get("days", {})
    
    for day_key, day_data in days.items():
        day_number = day_data.get("day_number", 0)
        day_key_str = f"day_{day_number}"
        
        # Get approvals for this day
        day_approvals = approval_status_map.get(day_key_str, {})
        
        # Filter meals to only approved ones
        meals = day_data.get("meals", {})
        approved_meals = {}
        
        for meal_name, meal_data in meals.items():
            # Check if meal is approved (default to False if not in map)
            is_approved = day_approvals.get(meal_name, False)
            
            if is_approved:
                approved_meals[meal_name] = meal_data
        
        # Only include day if it has approved meals
        if approved_meals:
            filtered_days[day_key] = {
                **day_data,
                "meals": approved_meals
            }
    
    # Return filtered meal allocation
    return {
        **meal_allocation,
        "days": filtered_days
    }


def transform_intake_to_assessment_snapshot(
    intake_data: Dict[str, Any],
    client_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Transform intake raw_input into structured assessment_snapshot.
    
    This function converts raw intake data into the structured format
    expected by the assessment snapshot, organizing data into logical sections.
    
    Args:
        intake_data: Raw intake data (from raw_input or normalized_input)
        client_data: Optional client data (age, gender, etc.) from client record
        
    Returns:
        Structured assessment snapshot dictionary
    """
    snapshot: Dict[str, Any] = {}
    
    # Extract client context
    client_context: Dict[str, Any] = {}
    if client_data:
        if client_data.get("age"):
            client_context["age"] = client_data["age"]
        if client_data.get("gender"):
            client_context["gender"] = client_data["gender"]
        if client_data.get("height_cm"):
            client_context["height_cm"] = client_data["height_cm"]
        if client_data.get("weight_kg"):
            client_context["weight_kg"] = client_data["weight_kg"]
    
    # Add from intake data
    if intake_data.get("height_cm"):
        client_context["height_cm"] = intake_data["height_cm"]
    if intake_data.get("weight_kg"):
        client_context["weight_kg"] = intake_data["weight_kg"]
    if intake_data.get("age"):
        client_context["age"] = intake_data["age"]
    if intake_data.get("gender"):
        client_context["gender"] = intake_data["gender"]
    if intake_data.get("activity_level"):
        client_context["activity_level"] = intake_data["activity_level"]
    
    # Extract client schedule fields
    if intake_data.get("wake_time"):
        client_context["wake_time"] = intake_data["wake_time"]
    if intake_data.get("sleep_time"):
        client_context["sleep_time"] = intake_data["sleep_time"]
    if intake_data.get("work_schedule"):
        if isinstance(intake_data["work_schedule"], dict):
            client_context["work_schedule"] = {
                "start": intake_data["work_schedule"].get("start"),
                "end": intake_data["work_schedule"].get("end")
            }
    
    # Calculate BMI if height and weight available
    if client_context.get("height_cm") and client_context.get("weight_kg"):
        height_m = client_context["height_cm"] / 100
        weight_kg = client_context["weight_kg"]
        if height_m > 0:
            client_context["bmi"] = round(weight_kg / (height_m ** 2), 2)
    
    # NEW: Add reproductive_context (Bug 1.1)
    reproductive_context: Dict[str, Any] = {}
    gender_lower = client_context.get("gender", "").lower() if isinstance(client_context.get("gender"), str) else ""
    
    # Extract pregnancy/reproductive information from intake data
    if intake_data.get("pregnancy_status"):
        reproductive_context["pregnancy_status"] = intake_data["pregnancy_status"]
        if intake_data.get("gestational_weeks") is not None:
            reproductive_context["gestational_weeks"] = intake_data["gestational_weeks"]
    elif intake_data.get("gestational_weeks") is not None:
        # If gestational_weeks is provided but pregnancy_status is not, infer pregnancy
        reproductive_context["pregnancy_status"] = "pregnant"
        reproductive_context["gestational_weeks"] = intake_data["gestational_weeks"]
    elif gender_lower in ["female", "f"]:
        # Default to not_pregnant for females if not specified
        reproductive_context["pregnancy_status"] = "not_pregnant"
    
    # Also check for menstruation_cycle data (might contain pregnancy info)
    if intake_data.get("menstruation_cycle"):
        menstruation_data = intake_data["menstruation_cycle"]
        if isinstance(menstruation_data, dict):
            # If menstruation data indicates pregnancy, set pregnancy status
            if menstruation_data.get("pregnancy_status"):
                reproductive_context["pregnancy_status"] = menstruation_data["pregnancy_status"]
            if menstruation_data.get("gestational_weeks") is not None:
                reproductive_context["gestational_weeks"] = menstruation_data["gestational_weeks"]
    
    if reproductive_context:
        snapshot["reproductive_context"] = reproductive_context
    
    if client_context:
        snapshot["client_context"] = client_context
    
    # Extract clinical data
    clinical_data: Dict[str, Any] = {}
    
    # Labs
    if intake_data.get("blood_report"):
        labs = {}
        blood_report = intake_data["blood_report"]
        if isinstance(blood_report, dict):
            if blood_report.get("hb"):
                labs["hb"] = blood_report["hb"]
            if blood_report.get("rbc"):
                labs["rbc"] = blood_report["rbc"]
            if blood_report.get("wbc"):
                labs["wbc"] = blood_report["wbc"]
            if blood_report.get("platelets"):
                labs["platelets"] = blood_report["platelets"]
        if labs:
            clinical_data["labs"] = labs
    
    # Anthropometry
    anthropometry: Dict[str, Any] = {}
    if client_context.get("bmi"):
        anthropometry["bmi"] = client_context["bmi"]
    if intake_data.get("waist_circumference"):
        anthropometry["waist_circumference"] = intake_data["waist_circumference"]
    if anthropometry:
        clinical_data["anthropometry"] = anthropometry
    
    # Medical history
    medical_history: Dict[str, Any] = {}
    conditions = []
    
    # From diagnosed_conditions array
    if intake_data.get("diagnosed_conditions"):
        if isinstance(intake_data["diagnosed_conditions"], list):
            for cond in intake_data["diagnosed_conditions"]:
                if isinstance(cond, dict) and cond.get("condition"):
                    conditions.append(cond["condition"])
                elif isinstance(cond, str):
                    conditions.append(cond)
    
    # From disease field (string or array)
    if intake_data.get("disease"):
        if isinstance(intake_data["disease"], str):
            # Split comma-separated diseases
            diseases = [d.strip() for d in intake_data["disease"].split(",") if d.strip()]
            conditions.extend(diseases)
        elif isinstance(intake_data["disease"], list):
            conditions.extend(intake_data["disease"])
    
    if conditions:
        medical_history["conditions"] = list(set(conditions))  # Remove duplicates
    
    # Surgery history
    if intake_data.get("surgery_history"):
        if isinstance(intake_data["surgery_history"], list):
            medical_history["surgery_history"] = intake_data["surgery_history"]
    
    if medical_history:
        clinical_data["medical_history"] = medical_history
    
    if clinical_data:
        snapshot["clinical_data"] = clinical_data
    
    # Extract diet data
    diet_data: Dict[str, Any] = {}
    
    # Dietary preferences
    dietary_preferences = []
    if intake_data.get("dietary_preferences"):
        if isinstance(intake_data["dietary_preferences"], list):
            dietary_preferences = intake_data["dietary_preferences"]
        elif isinstance(intake_data["dietary_preferences"], str):
            dietary_preferences = [p.strip() for p in intake_data["dietary_preferences"].split(",") if p.strip()]
    
    if intake_data.get("diet_type"):
        if intake_data["diet_type"] not in dietary_preferences:
            dietary_preferences.append(intake_data["diet_type"])
    
    if dietary_preferences:
        diet_data["dietary_preferences"] = dietary_preferences
    
    # Food preferences
    if intake_data.get("food_preferences"):
        diet_data["food_preferences"] = intake_data["food_preferences"]
    elif intake_data.get("likes") or intake_data.get("dislikes") or intake_data.get("favorite_foods"):
        food_prefs: Dict[str, Any] = {}
        if intake_data.get("likes"):
            food_prefs["likes"] = intake_data["likes"] if isinstance(intake_data["likes"], list) else [intake_data["likes"]]
        if intake_data.get("dislikes"):
            food_prefs["dislikes"] = intake_data["dislikes"] if isinstance(intake_data["dislikes"], list) else [intake_data["dislikes"]]
        if intake_data.get("favorite_foods"):
            food_prefs["favorite_foods"] = intake_data["favorite_foods"] if isinstance(intake_data["favorite_foods"], list) else [intake_data["favorite_foods"]]
        if intake_data.get("excluded_ingredients") or intake_data.get("structured_allergies"):
            excluded = []
            if intake_data.get("excluded_ingredients"):
                excluded.extend(intake_data["excluded_ingredients"] if isinstance(intake_data["excluded_ingredients"], list) else [intake_data["excluded_ingredients"]])
            if intake_data.get("structured_allergies"):
                excluded.extend(intake_data["structured_allergies"] if isinstance(intake_data["structured_allergies"], list) else [intake_data["structured_allergies"]])
            if excluded:
                food_prefs["excluded_ingredients"] = excluded
        if food_prefs:
            diet_data["food_preferences"] = food_prefs
    
    if diet_data:
        snapshot["diet_data"] = diet_data
    
    # Extract lifestyle data
    lifestyle_data: Dict[str, Any] = {}
    
    if intake_data.get("lifestyle"):
        lifestyle = intake_data["lifestyle"]
        if isinstance(lifestyle, dict):
            if lifestyle.get("work_nature"):
                lifestyle_data["work_nature"] = lifestyle["work_nature"]
            if lifestyle.get("daily_routine"):
                lifestyle_data["daily_routine"] = lifestyle["daily_routine"]
            if lifestyle.get("exercise_routine"):
                lifestyle_data["exercise_routine"] = lifestyle["exercise_routine"]
            if lifestyle.get("water_intake"):
                lifestyle_data["water_intake"] = lifestyle["water_intake"]
            if lifestyle.get("substance_use"):
                lifestyle_data["substance_use"] = lifestyle["substance_use"]
            if lifestyle.get("screen_time"):
                lifestyle_data["screen_time"] = lifestyle["screen_time"]
            if lifestyle.get("social_eating"):
                lifestyle_data["social_eating"] = lifestyle["social_eating"]
    
    # Direct fields
    if intake_data.get("sleep_cycle"):
        lifestyle_data["daily_routine"] = intake_data["sleep_cycle"]
    
    # Extract meal preferences
    meal_preferences = {}
    if intake_data.get("explicit_meal_count") is not None:
        meal_preferences["explicit_meal_count"] = intake_data["explicit_meal_count"]
    if intake_data.get("snack_preference") is not None:
        meal_preferences["snack_preference"] = intake_data["snack_preference"]
    if intake_data.get("liquid_meal_allowed") is not None:
        meal_preferences["liquid_meal_allowed"] = intake_data["liquid_meal_allowed"]
    if intake_data.get("fasting_window"):
        meal_preferences["fasting_window"] = intake_data["fasting_window"]
    if intake_data.get("max_meals") is not None:
        meal_preferences["max_meals"] = intake_data["max_meals"]
    
    if meal_preferences:
        lifestyle_data["meal_preferences"] = meal_preferences
    
    if lifestyle_data:
        snapshot["lifestyle_data"] = lifestyle_data
    
    # Extract goals
    goals: Dict[str, Any] = {}
    
    if intake_data.get("goals_extended"):
        goals_ext = intake_data["goals_extended"]
        if isinstance(goals_ext, dict):
            if goals_ext.get("primary_goal"):
                goals["primary_goal"] = goals_ext["primary_goal"]
            if goals_ext.get("secondary_goals"):
                goals["secondary_goals"] = goals_ext["secondary_goals"]
            if goals_ext.get("timeframe"):
                goals["timeframe"] = goals_ext["timeframe"]
            if goals_ext.get("motivation_level"):
                goals["motivation_level"] = goals_ext["motivation_level"]
            if goals_ext.get("past_attempts"):
                goals["past_attempts"] = goals_ext["past_attempts"]
            if goals_ext.get("readiness_to_change") is not None:
                goals["readiness_to_change"] = goals_ext["readiness_to_change"]
    
    # Simple goals field
    if intake_data.get("goals") and not goals.get("primary_goal"):
        goals["primary_goal"] = intake_data["goals"]
    
    if goals:
        snapshot["goals"] = goals
    
    # Extract Ayurveda data
    # Support both new comprehensive assessment and old dosha_answers format
    if intake_data.get("ayurveda_assessment"):
        # New comprehensive assessment format
        ayurveda_assessment = intake_data["ayurveda_assessment"]
        if isinstance(ayurveda_assessment, dict) and ayurveda_assessment:
            snapshot["ayurveda_data"] = {
                "ayurveda_assessment": ayurveda_assessment
            }
    elif intake_data.get("dosha_answers"):
        # Old format (backward compatibility)
        dosha_answers = intake_data["dosha_answers"]
        if isinstance(dosha_answers, dict) and dosha_answers:
            ayurveda_data: Dict[str, Any] = {
                "ayurveda_quiz": {
                    "dosha_answers": dosha_answers
                }
            }
            snapshot["ayurveda_data"] = ayurveda_data
    
    # Menstruation cycle (if applicable) - also extract pregnancy info if present
    if intake_data.get("menstruation_cycle"):
        menstruation_cycle = intake_data["menstruation_cycle"]
        snapshot["menstruation_cycle"] = menstruation_cycle
        
        # Extract pregnancy info from menstruation cycle data if available
        if isinstance(menstruation_cycle, dict):
            if menstruation_cycle.get("pregnancy_status") and not reproductive_context.get("pregnancy_status"):
                reproductive_context["pregnancy_status"] = menstruation_cycle["pregnancy_status"]
            if menstruation_cycle.get("gestational_weeks") is not None and reproductive_context.get("gestational_weeks") is None:
                reproductive_context["gestational_weeks"] = menstruation_cycle["gestational_weeks"]
            
            # Update reproductive_context in snapshot if it was updated
            if reproductive_context:
                snapshot["reproductive_context"] = reproductive_context
    
    return snapshot


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class IntakeRequest(BaseModel):
    """Intake creation request model."""
    client_id: UUID
    raw_input: Optional[Dict[str, Any]] = None
    source: Optional[str] = Field(default="manual", description="Source of intake data")

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: Optional[str]) -> Optional[str]:
        """Validate source value."""
        if v is not None and v not in ["manual", "upload", "ai_extracted"]:
            raise ValueError("source must be one of: manual, upload, ai_extracted")
        return v


class IntakeResponse(BaseModel):
    """Intake response model."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    client_id: UUID
    raw_input: Optional[Dict[str, Any]] = None
    normalized_input: Optional[Dict[str, Any]] = None
    source: Optional[str]
    created_at: datetime


class IntakeUpdateRequest(BaseModel):
    """Intake update request model."""
    raw_input: Optional[Dict[str, Any]] = None
    source: Optional[str] = None


class AssessmentUpdateRequest(BaseModel):
    """Assessment update request model."""
    assessment_snapshot: Optional[Dict[str, Any]] = None
    assessment_status: Optional[str] = None


class AssessmentRequest(BaseModel):
    """Assessment creation request model."""
    client_id: UUID
    intake_id: Optional[UUID] = None
    assessment_snapshot: Optional[Dict[str, Any]] = None


class AssessmentResponse(BaseModel):
    """Assessment response model."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    client_id: UUID
    intake_id: Optional[UUID]
    assessment_status: Optional[str]
    created_at: datetime


class DiagnosisRequest(BaseModel):
    """Diagnosis request model."""
    assessment_id: UUID


class DiagnosisResponse(BaseModel):
    """Diagnosis response model."""
    medical_conditions: List[Dict[str, Any]]
    nutrition_diagnoses: List[Dict[str, Any]]


class MNTRequest(BaseModel):
    """MNT processing request model."""
    assessment_id: UUID


class MNTResponse(BaseModel):
    """MNT response model."""
    macro_constraints: Dict[str, Any]
    micro_constraints: Dict[str, Any]
    food_exclusions: List[str]
    rule_ids_used: List[str]


class TargetRequest(BaseModel):
    """Target calculation request model."""
    assessment_id: UUID
    activity_level: Optional[str] = Field(
        default="moderately_active",
        description="Activity level for TDEE calculation"
    )


class TargetResponse(BaseModel):
    """Target response model."""
    calories_target: float
    macros: Dict[str, Any]
    key_micros: Dict[str, Any]
    calculation_source: str


class AyurvedaRequest(BaseModel):
    """Ayurveda processing request model."""
    assessment_id: UUID


class AyurvedaResponse(BaseModel):
    """Ayurveda response model."""
    dosha_primary: Optional[str]
    dosha_secondary: Optional[str]
    vikriti_notes: Optional[Dict[str, Any]]
    lifestyle_guidelines: Optional[Dict[str, Any]]


class MealStructureRequest(BaseModel):
    """Meal structure generation request model."""
    assessment_id: UUID
    client_preferences: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional behavioral preferences override"
    )


class MealStructureResponse(BaseModel):
    """Meal structure response model."""
    meal_count: int
    meals: List[str]
    timing_windows: Dict[str, List[str]]
    energy_weight: Dict[str, float]  # Relative allocation weights (sum = 1.0)
    flags: List[str] = Field(default_factory=list)
    # Legacy fields for backward compatibility (deprecated)
    calorie_split: Dict[str, float] = Field(default_factory=dict)
    protein_split: Dict[str, float] = Field(default_factory=dict)
    macro_guardrails: Dict[str, Dict[str, List[float]]] = Field(default_factory=dict)


class ExchangeAllocationRequest(BaseModel):
    """Exchange allocation generation request model."""
    assessment_id: UUID
    client_preferences: Optional[Dict[str, Any]] = None
    mandatory_exchanges_per_meal: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="User-selected mandatory exchanges per meal (meal_name -> [exchange_category_id, ...])"
    )


class ExchangeAllocationResponse(BaseModel):
    """Exchange allocation response model."""
    exchanges_per_meal: Dict[str, Dict[str, float]]  # {"breakfast": {"cereal": 2.0, "pulse": 1.5, ...}, ...}
    daily_exchange_allocation: Optional[Dict[str, float]] = None  # Daily exchange totals by category
    per_meal_nutrition: Optional[Dict[str, Dict[str, float]]] = None  # {"breakfast": {"total_calories": 500.0, "total_protein_g": 20.0}, ...}
    daily_nutrition: Optional[Dict[str, float]] = None  # {"total_calories": 2000.0, "total_protein_g": 80.0}
    user_mandatory_applied: Optional[Dict[str, Any]] = None  # User-mandated exchanges information
    notes: Optional[Dict[str, Any]] = Field(default_factory=dict)  # {"medical_modifiers_applied": [...], "ayurveda_modifiers_applied": [...]}


class InterventionRequest(BaseModel):
    """Food intervention generation request model."""
    assessment_id: UUID
    client_preferences: Optional[Dict[str, Any]] = None
    enable_ayurveda: Optional[bool] = True


class InterventionResponse(BaseModel):
    """Food intervention response model."""
    assessment_id: UUID
    plan_id: Optional[UUID] = None
    plan_version: Optional[int] = None
    meal_plan: Dict[str, Any]
    explanations: Optional[Dict[str, Any]] = None
    constraints_snapshot: Optional[Dict[str, Any]] = None


class FoodAllocationRequest(BaseModel):
    """Food allocation request model."""
    assessment_id: UUID
    client_preferences: Optional[Dict[str, Any]] = None


class FoodAllocationResponse(BaseModel):
    """Food allocation response model."""
    assessment_id: UUID
    plan_id: Optional[UUID] = None
    plan_version: Optional[int] = None
    meal_allocation: Dict[str, Any]  # Phase 1 output with allocated foods
    variety_metrics: Optional[Dict[str, Any]] = None
    nutrition_summary: Optional[Dict[str, Any]] = None


class FoodApprovalRequest(BaseModel):
    """Food allocation approval request model."""
    assessment_id: UUID
    approvals: Dict[str, Dict[str, bool]]  # {day_number: {meal_name: is_approved}}
    notes: Optional[Dict[str, Dict[str, str]]] = None  # Optional notes per meal


class FoodApprovalResponse(BaseModel):
    """Food allocation approval response model."""
    assessment_id: UUID
    approved_meals: List[Dict[str, str]]  # List of {day_number, meal_name}
    total_approved: int
    total_pending: int


class RecipeRequest(BaseModel):
    """Recipe generation request model."""
    assessment_id: UUID
    client_preferences: Optional[Dict[str, Any]] = None


class RecipeResponse(BaseModel):
    """Recipe generation response model."""
    assessment_id: UUID
    plan_id: Optional[UUID] = None
    plan_version: Optional[int] = None
    seven_day_plan: Dict[str, Any]
    variety_metrics: Optional[Dict[str, Any]] = None


@router.post("/intake", response_model=IntakeResponse, status_code=status.HTTP_201_CREATED)
async def create_intake(
    intake_data: IntakeRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new intake record.
    
    Intake is the raw user input/data collected from the client - the first step in the NCP flow.
    It collects lab results, vitals, medical history, diet history, lifestyle data, and more.
    
    Args:
        intake_data: Intake creation data
            - client_id: UUID of the client (required)
            - raw_input: Optional dict with raw user input (labs, vitals, medical_history, etc.)
            - source: Optional source type ("manual" | "upload" | "ai_extracted", default: "manual")
        db: Database session
        
    Returns:
        Created intake information with id, client_id, source, and created_at
        
    Raises:
        HTTPException: 
            - 404 if client not found
            - 400 for validation errors
            - 500 for database errors
    """
    # Validate client exists
    client_repository = PlatformClientRepository(db)
    client = client_repository.get_by_id(intake_data.client_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {intake_data.client_id} not found"
        )
    
    # Create intake using repository
    intake_repository = PlatformIntakeRepository(db)
    try:
        intake_dict = {
            "client_id": intake_data.client_id,
            "raw_input": intake_data.raw_input,
            "source": intake_data.source or "manual",
            "normalized_input": None  # Will be populated later by AI extraction service
        }
        intake = intake_repository.create(intake_dict)
        return IntakeResponse.model_validate(intake)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create intake: {str(e)}"
        )


@router.post("/", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    assessment_data: AssessmentRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new assessment record.
    
    Assessment is a structured snapshot of client data used in the NCP process.
    It can be linked to an intake record and contains organized assessment data.
    
    Args:
        assessment_data: Assessment creation data
            - client_id: UUID of the client (required)
            - intake_id: Optional UUID of linked intake record
            - assessment_snapshot: Optional dict with structured assessment data
        db: Database session
        
    Returns:
        Created assessment information with id, client_id, intake_id, status, and created_at
        
    Raises:
        HTTPException:
            - 404 if client not found
            - 404 if intake_id provided but intake not found
            - 400 if intake belongs to different client
            - 400 for validation errors
            - 500 for database errors
    """
    # Validate client exists
    client_repository = PlatformClientRepository(db)
    client = client_repository.get_by_id(assessment_data.client_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {assessment_data.client_id} not found"
        )
    
    # Get intake for auto-population if snapshot is empty
    intake_repository = PlatformIntakeRepository(db)
    intake = None
    
    # Validate intake if provided
    if assessment_data.intake_id is not None:
        intake = intake_repository.get_by_id(assessment_data.intake_id)
        if intake is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Intake with id {assessment_data.intake_id} not found"
            )
        # Verify intake belongs to the same client
        if intake.client_id != assessment_data.client_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Intake {assessment_data.intake_id} does not belong to client {assessment_data.client_id}"
            )
    
    # Auto-populate assessment_snapshot from intake if snapshot is empty
    assessment_snapshot = assessment_data.assessment_snapshot
    if (not assessment_snapshot or 
        (isinstance(assessment_snapshot, dict) and len(assessment_snapshot) == 0)):
        
        # Try to get intake if not already fetched
        if intake is None:
            # Get latest intake for client
            intakes = intake_repository.get_by_client_id(assessment_data.client_id)
            if intakes:
                # Sort by created_at descending and get latest
                intake = sorted(intakes, key=lambda x: x.created_at, reverse=True)[0]
        
        # Transform intake data to assessment snapshot
        if intake and (intake.raw_input or intake.normalized_input):
            intake_data = intake.normalized_input or intake.raw_input or {}
            
            # Prepare client data for transformation
            client_dict = {
                "age": client.age,
                "gender": client.gender,
                "height_cm": client.height_cm,
                "weight_kg": client.weight_kg,
            }
            
            # Transform intake to assessment snapshot
            assessment_snapshot = transform_intake_to_assessment_snapshot(
                intake_data=intake_data,
                client_data=client_dict
            )
            
            # Ensure intake_id is set if we used intake data
            if assessment_data.intake_id is None and intake:
                assessment_data.intake_id = intake.id
    
    # Create assessment using repository
    assessment_repository = PlatformAssessmentRepository(db)
    try:
        assessment_dict = {
            "client_id": assessment_data.client_id,
            "intake_id": assessment_data.intake_id,
            "assessment_snapshot": assessment_snapshot,
            "assessment_status": "draft"  # Initial status, can be finalized later
        }
        assessment = assessment_repository.create(assessment_dict)
        return AssessmentResponse.model_validate(assessment)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create assessment: {str(e)}"
        )


@router.get("/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment(
    assessment_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get assessment by ID.
    
    Args:
        assessment_id: Assessment UUID
        db: Database session
        
    Returns:
        Assessment information with all fields
        
    Raises:
        HTTPException: 404 if assessment not found
    """
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(assessment_id)
    
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {assessment_id} not found"
        )
    
    return AssessmentResponse.model_validate(assessment)


@router.get("/client/{client_id}", response_model=List[AssessmentResponse])
async def get_client_assessments(
    client_id: UUID,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Get all assessments for a client.
    
    Args:
        client_id: Client UUID
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return (for pagination)
        db: Database session
        
    Returns:
        List of assessments for the client (empty list if none found)
        
    Raises:
        HTTPException: 404 if client not found
    """
    # Validate client exists
    client_repository = PlatformClientRepository(db)
    client = client_repository.get_by_id(client_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {client_id} not found"
        )
    
    # Get assessments for client
    assessment_repository = PlatformAssessmentRepository(db)
    assessments = assessment_repository.get_by_client_id(client_id)
    
    # Apply pagination manually (repository doesn't support pagination for get_by_client_id)
    # For now, return all and let FastAPI handle pagination if needed
    # In future, we can add pagination to repository method
    paginated_assessments = assessments[skip:skip + limit]
    
    return [AssessmentResponse.model_validate(assessment) for assessment in paginated_assessments]


@router.get("/intake/client/{client_id}", response_model=List[IntakeResponse])
async def get_client_intakes(
    client_id: UUID,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Get all intakes for a client.
    
    Args:
        client_id: Client UUID
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return (for pagination)
        db: Database session
        
    Returns:
        List of intakes for the client (empty list if none found)
        
    Raises:
        HTTPException: 404 if client not found
    """
    # Validate client exists
    client_repository = PlatformClientRepository(db)
    client = client_repository.get_by_id(client_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {client_id} not found"
        )
    
    # Get intakes for client
    intake_repository = PlatformIntakeRepository(db)
    intakes = intake_repository.get_by_client_id(client_id)
    
    # Apply pagination
    paginated_intakes = intakes[skip:skip + limit]
    
    return [IntakeResponse.model_validate(intake) for intake in paginated_intakes]


@router.get("/intake/{intake_id}", response_model=IntakeResponse)
async def get_intake(
    intake_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get intake by ID.
    
    Args:
        intake_id: Intake UUID
        db: Database session
        
    Returns:
        Intake information with raw_input
        
    Raises:
        HTTPException: 404 if intake not found
    """
    intake_repository = PlatformIntakeRepository(db)
    intake = intake_repository.get_by_id(intake_id)
    
    if intake is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Intake with id {intake_id} not found"
        )
    
    return IntakeResponse.model_validate(intake)


@router.put("/intake/{intake_id}", response_model=IntakeResponse)
async def update_intake(
    intake_id: UUID,
    intake_update: IntakeUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update an intake record.
    
    Args:
        intake_id: Intake UUID
        intake_update: Intake update data
        db: Database session
        
    Returns:
        Updated intake information
        
    Raises:
        HTTPException: 404 if intake not found
    """
    intake_repository = PlatformIntakeRepository(db)
    intake = intake_repository.get_by_id(intake_id)
    
    if intake is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Intake with id {intake_id} not found"
        )
    
    update_data = {}
    if intake_update.raw_input is not None:
        update_data["raw_input"] = intake_update.raw_input
    if intake_update.source is not None:
        update_data["source"] = intake_update.source
    
    updated_intake = intake_repository.update(intake_id, update_data)
    return IntakeResponse.model_validate(updated_intake)


@router.patch("/{assessment_id}", response_model=AssessmentResponse)
async def update_assessment(
    assessment_id: UUID,
    assessment_update: AssessmentUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update an assessment record.
    
    Args:
        assessment_id: Assessment UUID
        assessment_update: Assessment update data
        db: Database session
        
    Returns:
        Updated assessment information
        
    Raises:
        HTTPException: 404 if assessment not found
    """
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(assessment_id)
    
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {assessment_id} not found"
        )
    
    update_data = {}
    if assessment_update.assessment_snapshot is not None:
        update_data["assessment_snapshot"] = assessment_update.assessment_snapshot
    if assessment_update.assessment_status is not None:
        update_data["assessment_status"] = assessment_update.assessment_status
    
    updated_assessment = assessment_repository.update(assessment_id, update_data)
    return AssessmentResponse.model_validate(updated_assessment)


@router.post("/diagnosis", response_model=DiagnosisResponse)
async def process_diagnosis(
    diagnosis_request: DiagnosisRequest,
    db: Session = Depends(get_db)
):
    """
    Process diagnosis for an assessment.
    
    This endpoint executes the diagnosis stage of the NCP pipeline.
    It uses the Diagnosis Engine to convert assessment data into structured
    medical conditions and nutrition diagnoses.
    
    Args:
        diagnosis_request: Diagnosis request with assessment ID
        db: Database session
        
    Returns:
        Diagnosis results with:
        - medical_conditions: List of medical conditions with diagnosis_id, severity_score, evidence
        - nutrition_diagnoses: List of nutrition diagnoses with diagnosis_id, severity_score, evidence
        
    Raises:
        HTTPException:
            - 404 if assessment not found
            - 400 for processing errors
            - 500 for database errors
    """
    # Validate assessment exists
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(diagnosis_request.assessment_id)
    
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {diagnosis_request.assessment_id} not found"
        )
    
    try:
        # Create AssessmentContext from assessment
        assessment_context = AssessmentContext(
            client_id=assessment.client_id,
            assessment_id=assessment.id,
            intake_id=assessment.intake_id,
            assessment_snapshot=assessment.assessment_snapshot,
            assessment_status=assessment.assessment_status
        )
        
        # Process assessment using Diagnosis Engine
        diagnosis_engine = DiagnosisEngine()
        diagnosis_context = diagnosis_engine.process_assessment(assessment_context)
        
        # Validate that we got a diagnosis context
        if not diagnosis_context:
            raise ValueError("Diagnosis engine returned None")
        
        # Store diagnoses in database
        diagnosis_repository = PlatformDiagnosisRepository(db)
        
        # Store medical conditions
        medical_count = 0
        for condition in diagnosis_context.medical_conditions or []:
            if not isinstance(condition, dict):
                continue
            diagnosis_repository.create({
                "assessment_id": assessment.id,
                "diagnosis_type": "medical",
                "diagnosis_id": condition.get("diagnosis_id"),
                "severity_score": condition.get("severity_score"),
                "evidence": condition.get("evidence", {})
            })
            medical_count += 1
        
        # Store nutrition diagnoses
        nutrition_count = 0
        for diagnosis in diagnosis_context.nutrition_diagnoses or []:
            if not isinstance(diagnosis, dict):
                continue
            diagnosis_repository.create({
                "assessment_id": assessment.id,
                "diagnosis_type": "nutrition",
                "diagnosis_id": diagnosis.get("diagnosis_id"),
                "severity_score": diagnosis.get("severity_score"),
                "evidence": diagnosis.get("evidence", {})
            })
            nutrition_count += 1
        
        # IMPORTANT: If no diagnoses were found, create a marker record to indicate
        # that diagnosis was executed (healthy person case - no conditions found)
        # This allows the status API to mark diagnosis as complete and allows
        # subsequent steps (MNT, Targets, etc.) to proceed
        if medical_count == 0 and nutrition_count == 0:
            diagnosis_repository.create({
                "assessment_id": assessment.id,
                "diagnosis_type": "marker",  # Special marker type
                "diagnosis_id": "no_diagnoses_found",  # Marker ID
                "severity_score": None,
                "evidence": {"note": "Diagnosis executed but no medical conditions or nutrition diagnoses found. This is a valid healthy person case."}
            })
        
        # Commit the transaction explicitly
        db.commit()
        
        # Log the results
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"Diagnosis processed for assessment {assessment.id}: "
            f"{medical_count} medical conditions, {nutrition_count} nutrition diagnoses"
        )
        
        # Warn if no diagnoses were found - this might indicate an issue
        if medical_count == 0 and nutrition_count == 0:
            logger.warning(
                f"No diagnoses found for assessment {assessment.id}. "
                f"Assessment snapshot keys: {list((assessment.assessment_snapshot or {}).keys())}"
            )
            # Still return success, but with empty lists
            # The UI should handle this case
        
        # Return response
        return DiagnosisResponse(
            medical_conditions=diagnosis_context.medical_conditions or [],
            nutrition_diagnoses=diagnosis_context.nutrition_diagnoses or []
        )
        
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid assessment data: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error processing diagnosis for assessment {assessment.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process diagnosis: {str(e)}"
        )


@router.post("/mnt", response_model=MNTResponse)
async def process_mnt(
    mnt_request: MNTRequest,
    db: Session = Depends(get_db)
):
    """
    Process MNT (Medical Nutrition Therapy) constraints for an assessment.
    
    This endpoint executes the MNT stage of the NCP pipeline.
    It uses the MNT Engine to convert diagnoses into mandatory nutrition constraints.
    
    Args:
        mnt_request: MNT request with assessment ID
        db: Database session
        
    Returns:
        MNT constraints with:
        - macro_constraints: Macro nutrient constraints (carbohydrates, proteins, fats)
        - micro_constraints: Micronutrient constraints (vitamins, minerals)
        - food_exclusions: List of excluded food IDs/categories
        - rule_ids_used: List of MNT rule IDs applied
        
    Raises:
        HTTPException:
            - 404 if assessment not found
            - 404 if no diagnoses found for assessment
            - 400 for processing errors
            - 500 for database errors
            
    Note:
        MNT constraints are mandatory and cannot be bypassed.
        This engine must run after diagnosis stage.
    """
    # Validate assessment exists
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(mnt_request.assessment_id)
    
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {mnt_request.assessment_id} not found"
        )
    
    # Get diagnoses for assessment
    diagnosis_repository = PlatformDiagnosisRepository(db)
    stored_diagnoses = diagnosis_repository.get_by_assessment_id(mnt_request.assessment_id)
    
    # Check if diagnosis was executed (even if empty - healthy person case)
    if not stored_diagnoses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No diagnosis found for assessment {mnt_request.assessment_id}. Please run diagnosis first."
        )
    
    # Filter out marker records (they indicate execution but no actual diagnoses)
    actual_diagnoses = [
        d for d in stored_diagnoses 
        if d.diagnosis_type != "marker" and d.diagnosis_id != "no_diagnoses_found"
    ]
    
    # If only marker record exists (healthy person), proceed with empty diagnoses
    # The MNT engine will handle empty diagnoses and return empty constraints
    
    try:
        # Separate medical conditions and nutrition diagnoses
        # Filter out marker records
        medical_conditions = []
        nutrition_diagnoses = []
        
        for diagnosis in actual_diagnoses:  # Use filtered diagnoses
            diagnosis_dict = {
                "diagnosis_id": diagnosis.diagnosis_id,
                "severity_score": float(diagnosis.severity_score) if diagnosis.severity_score else 0.0,
                "evidence": diagnosis.evidence or {}
            }
            
            if diagnosis.diagnosis_type == "medical":
                medical_conditions.append(diagnosis_dict)
            elif diagnosis.diagnosis_type == "nutrition":
                nutrition_diagnoses.append(diagnosis_dict)
        
        # Note: If medical_conditions and nutrition_diagnoses are both empty,
        # the MNT engine will return empty constraints (healthy person case)
        
        # Create DiagnosisContext from stored diagnoses
        diagnosis_context = DiagnosisContext(
            assessment_id=mnt_request.assessment_id,
            medical_conditions=medical_conditions,
            nutrition_diagnoses=nutrition_diagnoses
        )
        
        # Process diagnoses using MNT Engine
        mnt_engine = MNTEngine()
        mnt_context = mnt_engine.process_diagnoses(diagnosis_context)
        
        # Store MNT constraints in database (one merged record per assessment)
        # IMPORTANT: Store even if empty (healthy person case - no constraints needed)
        mnt_repository = PlatformMNTConstraintRepository(db)
        
        # Get priority for the merged constraint (use highest priority from rules)
        priority = 2  # Default to medium
        if mnt_context.rule_ids_used:
            from app.platform.engines.mnt_engine.kb_mnt_rules import get_mnt_rule
            priorities = []
            for rule_id in mnt_context.rule_ids_used:
                rule = get_mnt_rule(rule_id)
                if rule:
                    priorities.append(rule.get("priority_level", 2))
            if priorities:
                priority = max(priorities)
        
        # Store merged constraint
        mnt_repository.create({
            "assessment_id": assessment.id,
            "rule_id": ",".join(mnt_context.rule_ids_used) if mnt_context.rule_ids_used else None,
            "priority": priority,
            "macro_constraints": mnt_context.macro_constraints,
            "micro_constraints": mnt_context.micro_constraints,
            "food_exclusions": mnt_context.food_exclusions
        })
        
        # Return response
        return MNTResponse(
            macro_constraints=mnt_context.macro_constraints or {},
            micro_constraints=mnt_context.micro_constraints or {},
            food_exclusions=mnt_context.food_exclusions or [],
            rule_ids_used=mnt_context.rule_ids_used or []
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid diagnosis data: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process MNT constraints: {str(e)}"
        )


@router.put("/{assessment_id}/finalize", response_model=AssessmentResponse)
async def finalize_assessment(
    assessment_id: UUID
):
    """
    Finalize an assessment.
    
    Args:
        assessment_id: Assessment UUID
        
    Returns:
        Finalized assessment information
        
    Raises:
        HTTPException: If assessment not found or cannot be finalized
        
    Note:
        Delegates to assessment service. No business logic here.
    """
    # Placeholder - delegate to service
    pass


@router.post("/ayurveda", response_model=AyurvedaResponse)
async def process_ayurveda(
    ayurveda_request: AyurvedaRequest,
    db: Session = Depends(get_db)
):
    """
    Process Ayurveda advisory for an assessment.

    This stage provides dosha assessment and lifestyle/food preferences that
    must not override MNT constraints. All outputs are advisory and modifiable.

    Args:
        ayurveda_request: Ayurveda request with assessment ID
        db: Database session

    Returns:
        AyurvedaResponse with dosha info and guidelines.

    Raises:
        HTTPException:
            - 404 if assessment not found
            - 404 if MNT constraints missing (Ayurveda must follow MNT)
            - 400 for processing errors
            - 500 for database errors
    """
    # Validate assessment exists
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(ayurveda_request.assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {ayurveda_request.assessment_id} not found"
        )

    # Fetch MNT constraints (required)
    mnt_repository = PlatformMNTConstraintRepository(db)
    mnt_constraints = mnt_repository.get_by_assessment_id(ayurveda_request.assessment_id)
    if not mnt_constraints:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No MNT constraints found for assessment {ayurveda_request.assessment_id}. Please run MNT first."
        )
    mnt_record = mnt_constraints[0]
    rule_ids_used = []
    if mnt_record.rule_id:
        rule_ids_used = [r for r in mnt_record.rule_id.split(",") if r]
    mnt_context = MNTContext(
        assessment_id=ayurveda_request.assessment_id,
        macro_constraints=mnt_record.macro_constraints or {},
        micro_constraints=mnt_record.micro_constraints or {},
        food_exclusions=mnt_record.food_exclusions or [],
        rule_ids_used=rule_ids_used
    )

    # Fetch targets (optional)
    target_repo = PlatformNutritionTargetRepository(db)
    target = target_repo.get_by_assessment_id(ayurveda_request.assessment_id)
    target_context = TargetContext(
        assessment_id=ayurveda_request.assessment_id,
        calories_target=float(target.calories_target) if target and target.calories_target is not None else None,
        macros=target.macros if target else None,
        key_micros=target.key_micros if target else None,
        calculation_source=target.calculation_source if target else None
    )

    # Build client profile from assessment snapshot
    snapshot = assessment.assessment_snapshot or {}
    client_context = snapshot.get("client_context", {})
    anthropometry = snapshot.get("clinical_data", {}).get("anthropometry", {})
    intake_data = snapshot.get("ayurveda_data") or snapshot.get("intake_data") or {}

    client_profile = {
        "age": client_context.get("age") or snapshot.get("age"),
        "gender": client_context.get("gender") or snapshot.get("gender"),
        "height_cm": client_context.get("height_cm") or anthropometry.get("height_cm"),
        "weight_kg": client_context.get("weight_kg") or anthropometry.get("weight_kg"),
        "activity_level": client_context.get("activity_level") or snapshot.get("activity_level"),
        "intake_data": intake_data,
    }

    try:
        ayurveda_engine = AyurvedaEngine()
        ayurveda_context = ayurveda_engine.process_ayurveda_assessment(
            client_profile=client_profile,
            mnt_context=mnt_context,
            target_context=target_context
        )

        # Store profile (one per assessment)
        ayurveda_repo = PlatformAyurvedaProfileRepository(db)
        existing = ayurveda_repo.get_by_assessment_id(assessment.id)
        payload = {
            "assessment_id": assessment.id,
            "dosha_primary": ayurveda_context.dosha_primary,
            "dosha_secondary": ayurveda_context.dosha_secondary,
            "vikriti_notes": ayurveda_context.vikriti_notes,
            "lifestyle_guidelines": ayurveda_context.lifestyle_guidelines,
        }
        if existing:
            ayurveda_repo.update(existing.id, payload)
        else:
            ayurveda_repo.create(payload)

        return AyurvedaResponse(
            dosha_primary=ayurveda_context.dosha_primary,
            dosha_secondary=ayurveda_context.dosha_secondary,
            vikriti_notes=ayurveda_context.vikriti_notes,
            lifestyle_guidelines=ayurveda_context.lifestyle_guidelines,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data for Ayurveda calculation: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process Ayurveda advisory: {str(e)}"
        )


@router.post("/targets", response_model=TargetResponse)
async def process_targets(
    target_request: TargetRequest,
    db: Session = Depends(get_db)
):
    """
    Calculate nutrition targets for an assessment.

    This endpoint executes the Target stage of the NCP pipeline.
    It uses the Target Engine to compute calories, macros, and key micros,
    respecting all MNT constraints (mandatory).

    Args:
        target_request: Target request with assessment ID and optional activity level
        db: Database session
        
    Returns:
        Target results with:
        - calories_target: Calculated calorie target
        - macros: Macro ranges in grams
        - key_micros: Key micronutrient targets
        - calculation_source: Source of calorie calculation (bmr | tdee | custom)
        
    Raises:
        HTTPException:
            - 404 if assessment not found
            - 404 if MNT constraints not found (must run MNT first)
            - 400 for processing errors
            - 500 for database errors
    """
    # Validate assessment exists
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(target_request.assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {target_request.assessment_id} not found"
        )

    # Get MNT constraints (must exist)
    mnt_repository = PlatformMNTConstraintRepository(db)
    mnt_constraints = mnt_repository.get_by_assessment_id(target_request.assessment_id)
    if not mnt_constraints:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No MNT constraints found for assessment {target_request.assessment_id}. Please run MNT first."
        )

    # Use the first (merged) constraint
    mnt_record = mnt_constraints[0]

    # Build MNTContext
    rule_ids_used = []
    if mnt_record.rule_id:
        rule_ids_used = [r for r in mnt_record.rule_id.split(",") if r]
    mnt_context = MNTContext(
        assessment_id=target_request.assessment_id,
        macro_constraints=mnt_record.macro_constraints or {},
        micro_constraints=mnt_record.micro_constraints or {},
        food_exclusions=mnt_record.food_exclusions or [],
        rule_ids_used=rule_ids_used
    )

    # Extract client profile from assessment snapshot (with safe defaults)
    snapshot = assessment.assessment_snapshot or {}
    client_context = snapshot.get("client_context", {})
    clinical_data = snapshot.get("clinical_data", {})
    anthropometry = client_context or clinical_data.get("anthropometry", {})

    client_profile = {
        "age": client_context.get("age") or snapshot.get("age"),
        "gender": client_context.get("gender") or snapshot.get("gender"),
        "height_cm": client_context.get("height_cm") or anthropometry.get("height_cm"),
        "weight_kg": client_context.get("weight_kg") or anthropometry.get("weight_kg"),
        "activity_level": target_request.activity_level,
    }

    try:
        # Calculate targets using Target Engine
        target_engine = TargetEngine()
        target_context = target_engine.calculate_targets(
            client_profile=client_profile,
            mnt_context=mnt_context,
            activity_level=target_request.activity_level
        )

        # Store targets (one record per assessment)
        target_repo = PlatformNutritionTargetRepository(db)
        existing = target_repo.get_by_assessment_id(assessment.id)
        if existing:
            target_repo.update(existing.id, {
                "calories_target": target_context.calories_target,
                "macros": target_context.macros,
                "key_micros": target_context.key_micros,
                "calculation_source": target_context.calculation_source
            })
        else:
            target_repo.create({
                "assessment_id": assessment.id,
                "calories_target": target_context.calories_target,
                "macros": target_context.macros,
                "key_micros": target_context.key_micros,
                "calculation_source": target_context.calculation_source
            })

        return TargetResponse(
            calories_target=target_context.calories_target or 0,
            macros=target_context.macros or {},
            key_micros=target_context.key_micros or {},
            calculation_source=target_context.calculation_source or "custom"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data for target calculation: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process targets: {str(e)}"
        )


@router.post("/meal-structure", response_model=MealStructureResponse)
async def process_meal_structure(
    meal_structure_request: MealStructureRequest,
    db: Session = Depends(get_db)
):
    """
    Generate meal structure for an assessment.

    This endpoint executes the Meal Structure stage of the NCP pipeline.
    It uses the Meal Structure Engine to generate the structural skeleton
    of the daily meal plan (no food items) based on nutrition targets and
    client schedule/preferences.

    Args:
        meal_structure_request: Meal structure request with assessment ID and optional preferences
        db: Database session
        
    Returns:
        Meal structure results with:
        - meal_count: Number of meals
        - meals: List of meal names
        - timing_windows: Timing windows for each meal
        - calorie_split: Calorie allocation per meal
        - protein_split: Protein distribution per meal
        - macro_guardrails: Macro guardrails per meal
        - flags: Validation flags
        
    Raises:
        HTTPException:
            - 404 if assessment not found
            - 404 if nutrition targets not found (must run targets first)
            - 400 for processing errors
            - 500 for database errors
            
    Note:
        Meal structure must run after nutrition target calculation.
        It requires wake_time and sleep_time in client_context.
    """
    # Validate assessment exists
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(meal_structure_request.assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {meal_structure_request.assessment_id} not found"
        )

    # Get nutrition targets (must exist)
    target_repository = PlatformNutritionTargetRepository(db)
    target = target_repository.get_by_assessment_id(meal_structure_request.assessment_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No nutrition targets found for assessment {meal_structure_request.assessment_id}. Please calculate targets first."
        )

    # Build TargetContext from stored targets
    target_context = TargetContext(
        assessment_id=meal_structure_request.assessment_id,
        calories_target=float(target.calories_target) if target.calories_target else None,
        macros=target.macros if target else None,
        key_micros=target.key_micros if target else None,
        calculation_source=target.calculation_source if target else None
    )

    # Get assessment snapshot
    assessment_snapshot = assessment.assessment_snapshot or {}
    
    # Ensure client_context has wake_time and sleep_time
    # Try to get from client record if not in snapshot
    client_context = assessment_snapshot.get("client_context", {})
    if not client_context.get("wake_time") or not client_context.get("sleep_time"):
        # Try to get from client record
        client_repository = PlatformClientRepository(db)
        client = client_repository.get_by_id(assessment.client_id)
        if client:
            if not client_context.get("wake_time") and client.wake_time:
                client_context["wake_time"] = client.wake_time
            if not client_context.get("sleep_time") and client.sleep_time:
                client_context["sleep_time"] = client.sleep_time
            if not client_context.get("work_schedule") and (client.work_schedule_start or client.work_schedule_end):
                client_context["work_schedule"] = {
                    "start": client.work_schedule_start,
                    "end": client.work_schedule_end
                }
            assessment_snapshot["client_context"] = client_context

    try:
        # Generate meal structure using Meal Structure Engine
        meal_structure_engine = MealStructureEngine()
        meal_structure_context = meal_structure_engine.generate_structure(
            target_context=target_context,
            assessment_snapshot=assessment_snapshot,
            client_preferences=meal_structure_request.client_preferences
        )

        # Store meal structure in database (one record per assessment)
        meal_structure_repo = PlatformMealStructureRepository(db)
        existing = meal_structure_repo.get_by_assessment_id(assessment.id)
        
        structure_data = {
            "assessment_id": assessment.id,
            "meal_count": meal_structure_context.meal_count,
            "meals": meal_structure_context.meals,
            "timing_windows": meal_structure_context.timing_windows,
            "energy_weight": meal_structure_context.energy_weight,
            "flags": meal_structure_context.flags,
            # Legacy fields for backward compatibility (deprecated)
            "calorie_split": {},  # Empty dict for backward compatibility
            "protein_split": {},  # Empty dict for backward compatibility
            "macro_guardrails": {}  # Empty dict for backward compatibility
        }
        
        if existing:
            meal_structure_repo.update_by_assessment_id(assessment.id, structure_data)
        else:
            meal_structure_repo.create(structure_data)

        return MealStructureResponse(
            meal_count=meal_structure_context.meal_count,
            meals=meal_structure_context.meals,
            timing_windows=meal_structure_context.timing_windows,
            energy_weight=meal_structure_context.energy_weight,
            flags=meal_structure_context.flags
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data for meal structure generation: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process meal structure: {str(e)}"
        )


@router.post("/exchange-allocation", response_model=ExchangeAllocationResponse)
async def process_exchange_allocation(
    exchange_request: ExchangeAllocationRequest,
    db: Session = Depends(get_db)
):
    """
    Process exchange allocation for an assessment.
    
    This endpoint executes the Exchange Allocation stage of the NCP pipeline.
    It uses the Exchange System Engine to translate meal-level calorie and protein 
    targets into exchange units based on meal structure, targets, MNT constraints,
    and optionally Ayurveda guidelines.
    
    Args:
        exchange_request: Exchange allocation request with assessment ID and optional preferences
        db: Database session
        
    Returns:
        Exchange allocation results with:
        - exchanges_per_meal: Dictionary mapping meal names to exchange counts by category
        - notes: Information about modifiers applied
        
    Raises:
        HTTPException:
            - 404 if assessment not found
            - 404 if meal structure not found (must run meal structure first)
            - 404 if targets not found
            - 404 if MNT constraints not found
            - 400 for processing errors
            - 500 for database errors
            
    Note:
        Exchange allocation must run after meal structure generation.
        It requires targets, MNT constraints, and optionally Ayurveda profile.
    """
    # Validate assessment exists
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(exchange_request.assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {exchange_request.assessment_id} not found"
        )

    # Get meal structure (must exist)
    meal_structure_repo = PlatformMealStructureRepository(db)
    meal_structure_record = meal_structure_repo.get_by_assessment_id(exchange_request.assessment_id)
    if not meal_structure_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No meal structure found for assessment {exchange_request.assessment_id}. Please generate meal structure first."
        )

    # Get targets (must exist)
    target_repo = PlatformNutritionTargetRepository(db)
    target_record = target_repo.get_by_assessment_id(exchange_request.assessment_id)
    if not target_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No targets found for assessment {exchange_request.assessment_id}. Please calculate targets first."
        )

    # Get MNT constraints (must exist)
    mnt_repo = PlatformMNTConstraintRepository(db)
    mnt_constraints = mnt_repo.get_by_assessment_id(exchange_request.assessment_id)
    if not mnt_constraints:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No MNT constraints found for assessment {exchange_request.assessment_id}. Please run MNT first."
        )

    try:
        # Build contexts from stored data
        from app.platform.core.orchestration.ncp_orchestrator import NCPOrchestrator
        orchestrator = NCPOrchestrator(
            db=db,
            client_id=assessment.client_id,
            enable_ayurveda=True
        )

        # Build contexts
        assessment_context = orchestrator.execute_assessment_stage(exchange_request.assessment_id)
        
        # Get diagnosis for building MNT context
        diagnosis_repo = PlatformDiagnosisRepository(db)
        diagnoses = diagnosis_repo.get_by_assessment_id(exchange_request.assessment_id)
        diagnosis_context = None
        if diagnoses:
            diagnosis_context = orchestrator.execute_diagnosis_stage(assessment_context)
        
        mnt_context = orchestrator.execute_mnt_stage(diagnosis_context) if diagnosis_context else None
        if not mnt_context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Failed to build MNT context"
            )

        target_context = TargetContext(
            assessment_id=exchange_request.assessment_id,
            calories_target=float(target_record.calories_target) if target_record.calories_target else None,
            macros=target_record.macros or {},
            key_micros=target_record.key_micros or {},
            calculation_source=target_record.calculation_source or "unknown"
        )

        meal_structure_context = MealStructureContext(
            assessment_id=exchange_request.assessment_id,
            meal_count=meal_structure_record.meal_count,
            meals=meal_structure_record.meals or [],
            timing_windows=meal_structure_record.timing_windows or {},
            energy_weight=getattr(meal_structure_record, 'energy_weight', None) or {},
            flags=meal_structure_record.flags or []
        )

        # Get Ayurveda context (optional)
        ayurveda_repo = PlatformAyurvedaProfileRepository(db)
        ayurveda_profile = ayurveda_repo.get_by_assessment_id(exchange_request.assessment_id)
        ayurveda_context = None
        if ayurveda_profile:
            ayurveda_context = AyurvedaContext(
                assessment_id=exchange_request.assessment_id,
                dosha_primary=ayurveda_profile.dosha_primary,
                dosha_secondary=ayurveda_profile.dosha_secondary,
                vikriti_notes=ayurveda_profile.vikriti_notes or {},
                lifestyle_guidelines=ayurveda_profile.lifestyle_guidelines or {}
            )

        # Prepare client preferences with mandatory exchanges if provided
        client_prefs = exchange_request.client_preferences or {}
        
        # Handle per-meal mandatory exchanges - pass directly to engine without converting to daily
        if exchange_request.mandatory_exchanges_per_meal:
            # Store per-meal format - engine will use this directly
            client_prefs["mandatory_exchanges_per_meal"] = exchange_request.mandatory_exchanges_per_meal
        
        # Execute exchange stage
        exchange_context = orchestrator.execute_exchange_stage(
            meal_structure=meal_structure_context,
            target_context=target_context,
            mnt_context=mnt_context,
            ayurveda_context=ayurveda_context,
            client_preferences=client_prefs
        )

        # Get stored exchange allocation
        exchange_repo = PlatformExchangeAllocationRepository(db)
        stored_allocation = exchange_repo.get_by_assessment_id(exchange_request.assessment_id)

        # Ensure notes is always a dict
        notes = {}
        if stored_allocation and stored_allocation.notes:
            notes = stored_allocation.notes if isinstance(stored_allocation.notes, dict) else {}
        elif exchange_context.notes:
            # Use notes from context if not in database
            notes = exchange_context.notes if isinstance(exchange_context.notes, dict) else {}

        # Log for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Exchange context - daily_exchange_allocation: {exchange_context.daily_exchange_allocation}")
        logger.info(f"Exchange context - exchanges_per_meal keys: {list(exchange_context.exchanges_per_meal.keys()) if exchange_context.exchanges_per_meal else 'None'}")

        # Extract nutrition data from exchange result if available
        per_meal_nutrition = exchange_context.per_meal_nutrition if hasattr(exchange_context, 'per_meal_nutrition') else None
        daily_nutrition = exchange_context.daily_nutrition if hasattr(exchange_context, 'daily_nutrition') else None
        
        return ExchangeAllocationResponse(
            exchanges_per_meal=exchange_context.exchanges_per_meal or {},
            daily_exchange_allocation=exchange_context.daily_exchange_allocation,
            per_meal_nutrition=per_meal_nutrition,
            daily_nutrition=daily_nutrition,
            user_mandatory_applied=exchange_context.user_mandatory_applied,
            notes=notes
        )

    except ValueError as e:
        error_msg = str(e)
        # Check if this is an allocation convergence failure
        if "failed to converge" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exchange allocation failed: {error_msg}. This may occur if target calories and protein requirements cannot be met with available exchanges."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid data for exchange allocation: {error_msg}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process exchange allocation: {str(e)}"
        )


@router.post("/intervention", response_model=InterventionResponse)
async def process_intervention(
    intervention_request: InterventionRequest,
    db: Session = Depends(get_db)
):
    """
    Process food intervention for an assessment.
    
    This endpoint executes the Food Intervention stage of the NCP pipeline.
    It uses the Food Engine to generate meal plans with specific foods based on
    exchange allocations, targets, MNT constraints, and Ayurveda guidelines.
    
    Args:
        intervention_request: Intervention request with assessment ID and optional preferences
        db: Database session
        
    Returns:
        Intervention results with:
        - assessment_id: Assessment UUID
        - plan_id: Generated plan UUID (if plan was created)
        - plan_version: Plan version number
        - meal_plan: Meal plan with category-wise food lists
        - explanations: Explanations and reasoning
        - constraints_snapshot: Snapshot of constraints used
        
    Raises:
        HTTPException:
            - 404 if assessment not found
            - 404 if exchange allocation not found (must run exchange allocation first)
            - 404 if targets not found
            - 404 if MNT constraints not found
            - 400 for processing errors
            - 500 for database errors
            
    Note:
        Food intervention must run after exchange allocation.
        It requires exchange allocation, targets, MNT constraints, and optionally Ayurveda.
    """
    # Validate assessment exists
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(intervention_request.assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {intervention_request.assessment_id} not found"
        )

    # Get exchange allocation (must exist)
    exchange_repo = PlatformExchangeAllocationRepository(db)
    exchange_allocation = exchange_repo.get_by_assessment_id(intervention_request.assessment_id)
    if not exchange_allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No exchange allocation found for assessment {intervention_request.assessment_id}. Please generate exchange allocation first."
        )

    # Get targets (must exist)
    target_repo = PlatformNutritionTargetRepository(db)
    target_record = target_repo.get_by_assessment_id(intervention_request.assessment_id)
    if not target_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No targets found for assessment {intervention_request.assessment_id}. Please calculate targets first."
        )

    # Get MNT constraints (must exist)
    mnt_repo = PlatformMNTConstraintRepository(db)
    mnt_constraints = mnt_repo.get_by_assessment_id(intervention_request.assessment_id)
    if not mnt_constraints:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No MNT constraints found for assessment {intervention_request.assessment_id}. Please run MNT first."
        )

    try:
        # Use orchestrator to build contexts and execute intervention
        from app.platform.core.orchestration.ncp_orchestrator import NCPOrchestrator
        orchestrator = NCPOrchestrator(
            db=db,
            client_id=assessment.client_id,
            enable_ayurveda=bool(intervention_request.enable_ayurveda)
        )

        # Build all required contexts
        assessment_context = orchestrator.execute_assessment_stage(intervention_request.assessment_id)
        
        diagnosis_repo = PlatformDiagnosisRepository(db)
        diagnoses = diagnosis_repo.get_by_assessment_id(intervention_request.assessment_id)
        diagnosis_context = None
        if diagnoses:
            diagnosis_context = orchestrator.execute_diagnosis_stage(assessment_context)
        
        mnt_context = orchestrator.execute_mnt_stage(diagnosis_context) if diagnosis_context else None
        if not mnt_context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Failed to build MNT context"
            )

        target_context = TargetContext(
            assessment_id=intervention_request.assessment_id,
            calories_target=float(target_record.calories_target) if target_record.calories_target else None,
            macros=target_record.macros or {},
            key_micros=target_record.key_micros or {},
            calculation_source=target_record.calculation_source or "unknown"
        )

        meal_structure_repo = PlatformMealStructureRepository(db)
        meal_structure_record = meal_structure_repo.get_by_assessment_id(intervention_request.assessment_id)
        if not meal_structure_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meal structure not found"
            )

        meal_structure_context = MealStructureContext(
            assessment_id=intervention_request.assessment_id,
            meal_count=meal_structure_record.meal_count,
            meals=meal_structure_record.meals or [],
            timing_windows=meal_structure_record.timing_windows or {},
            energy_weight=getattr(meal_structure_record, 'energy_weight', None) or {},
            flags=meal_structure_record.flags or []
        )

        # Build exchange context
        exchange_context = ExchangeContext(
            assessment_id=intervention_request.assessment_id,
            exchanges_per_meal=exchange_allocation.exchanges_per_meal or {},
            per_meal_targets={},  # Will be calculated if needed
            exchange_distribution_table={}
        )

        # Get Ayurveda context (optional)
        ayurveda_repo = PlatformAyurvedaProfileRepository(db)
        ayurveda_profile = ayurveda_repo.get_by_assessment_id(intervention_request.assessment_id)
        ayurveda_context = AyurvedaContext(assessment_id=intervention_request.assessment_id)
        if ayurveda_profile:
            ayurveda_context = AyurvedaContext(
                assessment_id=intervention_request.assessment_id,
                dosha_primary=ayurveda_profile.dosha_primary,
                dosha_secondary=ayurveda_profile.dosha_secondary,
                vikriti_notes=ayurveda_profile.vikriti_notes or {},
                lifestyle_guidelines=ayurveda_profile.lifestyle_guidelines or {}
            )

        # Execute intervention stage
        intervention_context = orchestrator.execute_intervention_stage(
            mnt_context=mnt_context,
            target_context=target_context,
            exchange_context=exchange_context,
            ayurveda_context=ayurveda_context,
            diagnosis_context=diagnosis_context,
            client_preferences=intervention_request.client_preferences
        )

        return InterventionResponse(
            assessment_id=str(intervention_context.assessment_id),
            plan_id=str(intervention_context.plan_id) if intervention_context.plan_id else None,
            plan_version=intervention_context.plan_version,
            meal_plan=intervention_context.meal_plan or {},
            explanations=intervention_context.explanations or {},
            constraints_snapshot=intervention_context.constraints_snapshot or {}
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data for intervention: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process intervention: {str(e)}"
        )


@router.post("/food-allocation", response_model=FoodAllocationResponse)
async def process_food_allocation(
    allocation_request: FoodAllocationRequest,
    db: Session = Depends(get_db)
):
    """
    Process food allocation (Phase 1) for an assessment.
    
    This endpoint executes Phase 1 of Recipe Generation: allocating foods to meals
    based on exchange targets. This is deterministic and does NOT use LLM.
    
    After this step, user must approve food selections before recipes can be generated.
    
    Args:
        allocation_request: Food allocation request with assessment ID
        db: Database session
        
    Returns:
        Food allocation results with:
        - assessment_id: Assessment UUID
        - plan_id: Plan UUID
        - plan_version: Plan version number
        - meal_allocation: 7-day meal plan with allocated foods (no recipes)
        - variety_metrics: Metrics about food variety
        - nutrition_summary: Nutrition summary across days
        
    Raises:
        HTTPException:
            - 404 if assessment not found
            - 404 if intervention not found (must run intervention first)
            - 404 if exchange allocation not found
            - 404 if meal structure not found
            - 400 for processing errors
            - 500 for database errors
    """
    # Validate assessment exists
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(allocation_request.assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {allocation_request.assessment_id} not found"
        )

    # Get plan (intervention result - must exist)
    plan_repo = PlatformDietPlanRepository(db)
    plans = plan_repo.get_by_assessment_id(allocation_request.assessment_id)
    if not plans:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No plan found for assessment {allocation_request.assessment_id}. Please run intervention first."
        )
    plan_record = max(plans, key=lambda p: p.plan_version or 1)

    # Get exchange allocation (must exist)
    exchange_repo = PlatformExchangeAllocationRepository(db)
    exchange_allocation = exchange_repo.get_by_assessment_id(allocation_request.assessment_id)
    if not exchange_allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No exchange allocation found for assessment {allocation_request.assessment_id}. Please generate exchange allocation first."
        )

    # Get meal structure (must exist)
    meal_structure_repo = PlatformMealStructureRepository(db)
    meal_structure_record = meal_structure_repo.get_by_assessment_id(allocation_request.assessment_id)
    if not meal_structure_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No meal structure found for assessment {allocation_request.assessment_id}. Please generate meal structure first."
        )

    try:
        # Use orchestrator to build contexts
        from app.platform.core.orchestration.ncp_orchestrator import NCPOrchestrator
        orchestrator = NCPOrchestrator(
            db=db,
            client_id=assessment.client_id,
            enable_ayurveda=True
        )

        # Build contexts
        assessment_context = orchestrator.execute_assessment_stage(allocation_request.assessment_id)
        
        diagnosis_repo = PlatformDiagnosisRepository(db)
        diagnoses = diagnosis_repo.get_by_assessment_id(allocation_request.assessment_id)
        diagnosis_context = None
        if diagnoses:
            diagnosis_context = orchestrator.execute_diagnosis_stage(assessment_context)
        
        mnt_context = orchestrator.execute_mnt_stage(diagnosis_context) if diagnosis_context else None
        if not mnt_context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Failed to build MNT context"
            )

        meal_structure_context = MealStructureContext(
            assessment_id=allocation_request.assessment_id,
            meal_count=meal_structure_record.meal_count,
            meals=meal_structure_record.meals or [],
            timing_windows=meal_structure_record.timing_windows or {},
            energy_weight=getattr(meal_structure_record, 'energy_weight', None) or {},
            flags=meal_structure_record.flags or []
        )

        exchange_context = ExchangeContext(
            assessment_id=allocation_request.assessment_id,
            exchanges_per_meal=exchange_allocation.exchanges_per_meal or {},
            per_meal_targets={},
            exchange_distribution_table={}
        )

        # Build intervention context from plan
        intervention_context = InterventionContext(
            assessment_id=allocation_request.assessment_id,
            client_id=assessment.client_id,
            plan_id=plan_record.id,
            plan_version=plan_record.plan_version or 1,
            meal_plan=plan_record.meal_plan or {},
            explanations=plan_record.explanations or {},
            constraints_snapshot=plan_record.constraints_snapshot or {}
        )

        # Execute Phase 1: Food Allocation (deterministic)
        meal_allocation_result = orchestrator.meal_allocation_engine.allocate_meal_plan(
            exchange_context=exchange_context,
            meal_structure=meal_structure_context,
            food_engine_output=intervention_context.meal_plan or {},
            num_days=7,
            start_date=None
        )

        # Store meal allocation in plan record
        updated_meal_plan = {
            **(plan_record.meal_plan or {}),
            "meal_allocation": meal_allocation_result
        }
        
        plan_repo.update(plan_record.id, {
            "meal_plan": updated_meal_plan
        })

        return FoodAllocationResponse(
            assessment_id=str(allocation_request.assessment_id),
            plan_id=str(plan_record.id),
            plan_version=plan_record.plan_version or 1,
            meal_allocation=meal_allocation_result,
            variety_metrics=meal_allocation_result.get("variety_metrics"),
            nutrition_summary=meal_allocation_result.get("nutrition_summary")
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data for food allocation: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process food allocation: {str(e)}"
        )


@router.post("/food-allocation/approve", response_model=FoodApprovalResponse)
async def approve_food_allocation(
    approval_request: FoodApprovalRequest,
    db: Session = Depends(get_db)
):
    """
    Approve food allocations for meals.
    
    This endpoint stores approval status for food allocations generated in Phase 1.
    Only approved meals will be used for recipe generation in Phase 2.
    
    Args:
        approval_request: Approval request with assessment ID and approval status per meal
        db: Database session
        
    Returns:
        Approval response with:
        - assessment_id: Assessment UUID
        - approved_meals: List of approved meals
        - total_approved: Total number of approved meals
        - total_pending: Total number of pending meals
        
    Raises:
        HTTPException:
            - 404 if assessment not found
            - 400 for invalid approval data
    """
    # Validate assessment exists
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(approval_request.assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {approval_request.assessment_id} not found"
        )

    try:
        approval_repo = PlatformFoodAllocationApprovalRepository(db)
        approved_meals = []
        
        # Process approvals
        for day_number, meal_approvals in approval_request.approvals.items():
            for meal_name, is_approved in meal_approvals.items():
                notes = None
                if approval_request.notes and day_number in approval_request.notes:
                    notes = approval_request.notes[day_number].get(meal_name)
                
                approval_repo.update_approval(
                    assessment_id=approval_request.assessment_id,
                    day_number=day_number,
                    meal_name=meal_name,
                    is_approved=is_approved,
                    approved_by=None,  # TODO: Get from auth context
                    notes={"notes": notes} if notes else None
                )
                
                if is_approved:
                    approved_meals.append({
                        "day_number": day_number,
                        "meal_name": meal_name
                    })
        
        # Calculate totals
        all_approvals = approval_repo.get_by_assessment_id(approval_request.assessment_id)
        total_approved = sum(1 for a in all_approvals if a.is_approved)
        total_pending = len(all_approvals) - total_approved
        
        return FoodApprovalResponse(
            assessment_id=str(approval_request.assessment_id),
            approved_meals=approved_meals,
            total_approved=total_approved,
            total_pending=total_pending
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process approvals: {str(e)}"
        )


@router.get("/{assessment_id}/food-allocation", response_model=FoodAllocationResponse)
async def get_food_allocation(
    assessment_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get food allocation results for an assessment.
    
    Retrieves stored food allocation results (Phase 1 output).
    
    Args:
        assessment_id: Assessment UUID
        db: Database session
        
    Returns:
        Food allocation results
        
    Raises:
        HTTPException:
            - 404 if assessment not found
            - 404 if food allocation not found
    """
    # Validate assessment exists
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {assessment_id} not found"
        )

    # Get plan
    plan_repo = PlatformDietPlanRepository(db)
    plans = plan_repo.get_by_assessment_id(assessment_id)
    if not plans:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No plan found for assessment {assessment_id}. Please run food allocation first."
        )
    
    plan_record = max(plans, key=lambda p: p.plan_version or 1)
    meal_plan = plan_record.meal_plan or {}
    meal_allocation = meal_plan.get("meal_allocation")
    
    if not meal_allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No food allocation found for assessment {assessment_id}. Please process food allocation first."
        )
    
    return FoodAllocationResponse(
        assessment_id=str(assessment_id),
        plan_id=str(plan_record.id),
        plan_version=plan_record.plan_version or 1,
        meal_allocation=meal_allocation,
        variety_metrics=meal_allocation.get("variety_metrics"),
        nutrition_summary=meal_allocation.get("nutrition_summary")
    )


@router.get("/{assessment_id}/food-allocation/approvals", response_model=FoodApprovalResponse)
async def get_food_allocation_approvals(
    assessment_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get food allocation approval status for an assessment.
    
    Args:
        assessment_id: Assessment UUID
        db: Database session
        
    Returns:
        Approval status with list of approved meals
    """
    # Validate assessment exists
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {assessment_id} not found"
        )

    approval_repo = PlatformFoodAllocationApprovalRepository(db)
    approved_meals = approval_repo.get_all_approved_meals(assessment_id)
    all_approvals = approval_repo.get_by_assessment_id(assessment_id)
    
    total_approved = len(approved_meals)
    total_pending = len(all_approvals) - total_approved
    
    return FoodApprovalResponse(
        assessment_id=str(assessment_id),
        approved_meals=approved_meals,
        total_approved=total_approved,
        total_pending=total_pending
    )


@router.post("/recipe-generation", response_model=RecipeResponse)
async def process_recipe_generation(
    recipe_request: RecipeRequest,
    db: Session = Depends(get_db)
):
    """
    Process recipe generation for an assessment.
    
    This endpoint executes the Recipe Generation stage of the NCP pipeline.
    It uses the Recipe Engine to generate 7-day meal plans with recipes and variety
    based on the food intervention output.
    
    Args:
        recipe_request: Recipe generation request with assessment ID and optional preferences
        db: Database session
        
    Returns:
        Recipe generation results with:
        - assessment_id: Assessment UUID
        - plan_id: Plan UUID
        - plan_version: Plan version number
        - seven_day_plan: 7-day meal plan with recipes and variety
        - variety_metrics: Metrics about recipe variety
        
    Raises:
        HTTPException:
            - 404 if assessment not found
            - 404 if intervention not found (must run intervention first)
            - 404 if exchange allocation not found
            - 404 if meal structure not found
            - 400 for processing errors
            - 500 for database errors
            
    Note:
        Recipe generation must run after food intervention.
        It requires intervention (plan), exchange allocation, and meal structure.
    """
    # Validate assessment exists
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(recipe_request.assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {recipe_request.assessment_id} not found"
        )

    # Get plan (intervention result - must exist)
    plan_repo = PlatformDietPlanRepository(db)
    plans = plan_repo.get_by_assessment_id(recipe_request.assessment_id)
    if not plans:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No plan found for assessment {recipe_request.assessment_id}. Please run intervention first."
        )
    # Use the latest plan
    plan_record = max(plans, key=lambda p: p.plan_version or 1)

    # Get exchange allocation (must exist)
    exchange_repo = PlatformExchangeAllocationRepository(db)
    exchange_allocation = exchange_repo.get_by_assessment_id(recipe_request.assessment_id)
    if not exchange_allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No exchange allocation found for assessment {recipe_request.assessment_id}. Please generate exchange allocation first."
        )

    # Get meal structure (must exist)
    meal_structure_repo = PlatformMealStructureRepository(db)
    meal_structure_record = meal_structure_repo.get_by_assessment_id(recipe_request.assessment_id)
    if not meal_structure_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No meal structure found for assessment {recipe_request.assessment_id}. Please generate meal structure first."
        )

    try:
        # Use orchestrator to build contexts and execute recipe generation
        from app.platform.core.orchestration.ncp_orchestrator import NCPOrchestrator
        orchestrator = NCPOrchestrator(
            db=db,
            client_id=assessment.client_id,
            enable_ayurveda=True
        )

        # Build contexts
        assessment_context = orchestrator.execute_assessment_stage(recipe_request.assessment_id)
        
        diagnosis_repo = PlatformDiagnosisRepository(db)
        diagnoses = diagnosis_repo.get_by_assessment_id(recipe_request.assessment_id)
        diagnosis_context = None
        if diagnoses:
            diagnosis_context = orchestrator.execute_diagnosis_stage(assessment_context)
        
        mnt_context = orchestrator.execute_mnt_stage(diagnosis_context) if diagnosis_context else None
        if not mnt_context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Failed to build MNT context"
            )

        meal_structure_context = MealStructureContext(
            assessment_id=recipe_request.assessment_id,
            meal_count=meal_structure_record.meal_count,
            meals=meal_structure_record.meals or [],
            timing_windows=meal_structure_record.timing_windows or {},
            energy_weight=getattr(meal_structure_record, 'energy_weight', None) or {},
            flags=meal_structure_record.flags or []
        )

        exchange_context = ExchangeContext(
            assessment_id=recipe_request.assessment_id,
            exchanges_per_meal=exchange_allocation.exchanges_per_meal or {},
            per_meal_targets={},
            exchange_distribution_table={}
        )

        # Get Ayurveda context
        ayurveda_repo = PlatformAyurvedaProfileRepository(db)
        ayurveda_profile = ayurveda_repo.get_by_assessment_id(recipe_request.assessment_id)
        ayurveda_context = AyurvedaContext(assessment_id=recipe_request.assessment_id)
        if ayurveda_profile:
            ayurveda_context = AyurvedaContext(
                assessment_id=recipe_request.assessment_id,
                dosha_primary=ayurveda_profile.dosha_primary,
                dosha_secondary=ayurveda_profile.dosha_secondary,
                vikriti_notes=ayurveda_profile.vikriti_notes or {},
                lifestyle_guidelines=ayurveda_profile.lifestyle_guidelines or {}
            )

        # Get approval status - only generate recipes for approved meals
        approval_repo = PlatformFoodAllocationApprovalRepository(db)
        approval_status_map = approval_repo.get_approval_status_map(recipe_request.assessment_id)
        
        # Get meal allocation from plan
        meal_plan = plan_record.meal_plan or {}
        meal_allocation = meal_plan.get("meal_allocation")
        
        if not meal_allocation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No food allocation found for assessment {recipe_request.assessment_id}. Please run food allocation first."
            )
        
        # Filter meal allocation to only include approved meals
        filtered_meal_allocation = _filter_approved_meals(meal_allocation, approval_status_map)
        
        # Build intervention context from plan
        intervention_context = InterventionContext(
            assessment_id=recipe_request.assessment_id,
            client_id=assessment.client_id,
            plan_id=plan_record.id,
            plan_version=plan_record.plan_version or 1,
            meal_plan=meal_plan,
            explanations=plan_record.explanations or {},
            constraints_snapshot=plan_record.constraints_snapshot or {}
        )

        # Execute Phase 2: Recipe Generation (only for approved meals)
        recipe_result = orchestrator.recipe_generation_engine.generate_recipes_for_meal_plan(
            meal_plan=filtered_meal_allocation,
            mnt_context=mnt_context,
            ayurveda_context=ayurveda_context,
            num_days=7
        )
        
        # Merge with original meal allocation to preserve all data
        final_result = {
            **meal_allocation,  # Preserve Phase 1 data
            "days": recipe_result.get("days", {}),  # Override with recipes
            "summary": recipe_result.get("summary", {}),  # Phase 2 summary
            "variety_metrics": meal_allocation.get("variety_metrics"),  # Preserve Phase 1 metrics
            "nutrition_summary": meal_allocation.get("nutrition_summary"),  # Preserve Phase 1 summary
        }
        
        # Create RecipeContext
        recipe_context = RecipeContext(
            assessment_id=intervention_context.assessment_id,
            client_id=intervention_context.client_id,
            plan_id=intervention_context.plan_id,
            plan_version=intervention_context.plan_version,
            meals_with_recipes=final_result,
            total_daily_nutrition=final_result.get("nutrition_summary", {}).get("average_daily"),
            meal_plan_structure=meal_plan
        )
        
        # Update plan record
        updated_meal_plan = {
            **meal_plan,
            "seven_day_plan": final_result
        }
        
        explanations = plan_record.explanations or {}
        explanations["recipe_generation"] = {
            "recipes_generated": True,
            "plan_duration_days": 7,
            "start_date": final_result.get("start_date"),
            "total_meals": recipe_result.get("summary", {}).get("total_meals", 0),
            "successful_recipes": recipe_result.get("summary", {}).get("successful_recipes", 0),
            "failed_recipes": recipe_result.get("summary", {}).get("failed_recipes", 0),
            "approved_meals_only": True
        }
        
        plan_repo.update(plan_record.id, {
            "meal_plan": updated_meal_plan,
            "explanations": explanations
        })

        seven_day_plan = recipe_context.meals_with_recipes or {}
        variety_metrics = seven_day_plan.get("variety_metrics", {})

        return RecipeResponse(
            assessment_id=str(recipe_context.assessment_id),
            plan_id=str(recipe_context.plan_id) if recipe_context.plan_id else None,
            plan_version=recipe_context.plan_version,
            seven_day_plan=seven_day_plan,
            variety_metrics=variety_metrics
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data for recipe generation: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process recipe generation: {str(e)}"
        )


# ============================================================================
# GET ENDPOINTS - Retrieve Step Results
# ============================================================================

@router.get("/{assessment_id}/diagnosis", response_model=DiagnosisResponse)
async def get_diagnosis(
    assessment_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get diagnosis results for an assessment.
    
    Retrieves stored diagnosis results (medical conditions and nutrition diagnoses)
    that were previously processed for this assessment.
    
    Args:
        assessment_id: Assessment UUID
        db: Database session
        
    Returns:
        Diagnosis results with:
        - medical_conditions: List of medical conditions
        - nutrition_diagnoses: List of nutrition diagnoses
        
    Raises:
        HTTPException:
            - 404 if assessment not found
            - 404 if no diagnosis found (diagnosis not yet processed)
    """
    # Validate assessment exists
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(assessment_id)
    
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {assessment_id} not found"
        )
    
    # Get diagnoses from database
    diagnosis_repository = PlatformDiagnosisRepository(db)
    diagnoses = diagnosis_repository.get_by_assessment_id(assessment_id)
    
    if not diagnoses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No diagnosis found for assessment {assessment_id}. Please run diagnosis first."
        )
    
    # Filter out marker records (they indicate execution but no actual diagnoses)
    actual_diagnoses = [
        d for d in diagnoses 
        if d.diagnosis_type != "marker" and d.diagnosis_id != "no_diagnoses_found"
    ]
    
    # Separate medical conditions and nutrition diagnoses
    medical_conditions = []
    nutrition_diagnoses = []
    
    for diag in actual_diagnoses:
        diag_dict = {
            "diagnosis_id": diag.diagnosis_id,
            "severity_score": float(diag.severity_score) if diag.severity_score else 0.0,
            "evidence": diag.evidence or {}
        }
        
        if diag.diagnosis_type == "medical":
            medical_conditions.append(diag_dict)
        elif diag.diagnosis_type == "nutrition":
            nutrition_diagnoses.append(diag_dict)
    
    return DiagnosisResponse(
        medical_conditions=medical_conditions,
        nutrition_diagnoses=nutrition_diagnoses
    )


@router.get("/{assessment_id}/mnt", response_model=MNTResponse)
async def get_mnt(
    assessment_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get MNT (Medical Nutrition Therapy) constraints for an assessment.
    
    Retrieves stored MNT constraints that were previously processed for this assessment.
    
    Args:
        assessment_id: Assessment UUID
        db: Database session
        
    Returns:
        MNT constraints with:
        - macro_constraints: Macro nutrient constraints
        - micro_constraints: Micronutrient constraints
        - food_exclusions: List of excluded food IDs/categories
        - rule_ids_used: List of MNT rule IDs applied
        
    Raises:
        HTTPException:
            - 404 if assessment not found
            - 404 if no MNT constraints found (MNT not yet processed)
    """
    # Validate assessment exists
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(assessment_id)
    
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {assessment_id} not found"
        )
    
    # Get MNT constraints from database
    mnt_repository = PlatformMNTConstraintRepository(db)
    constraints = mnt_repository.get_by_assessment_id(assessment_id)
    
    if not constraints:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No MNT constraints found for assessment {assessment_id}. Please run MNT first."
        )
    
    # Use the first (merged) constraint
    constraint = constraints[0]
    rule_ids = []
    if constraint.rule_id:
        rule_ids = [r.strip() for r in constraint.rule_id.split(",") if r.strip()]
    
    return MNTResponse(
        macro_constraints=constraint.macro_constraints or {},
        micro_constraints=constraint.micro_constraints or {},
        food_exclusions=constraint.food_exclusions or [],
        rule_ids_used=rule_ids
    )


@router.get("/{assessment_id}/targets", response_model=TargetResponse)
async def get_targets(
    assessment_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get nutrition targets for an assessment.
    
    Retrieves stored nutrition targets (calories, macros, micros) that were
    previously calculated for this assessment.
    
    Args:
        assessment_id: Assessment UUID
        db: Database session
        
    Returns:
        Target results with:
        - calories_target: Calculated calorie target
        - macros: Macro ranges in grams
        - key_micros: Key micronutrient targets
        - calculation_source: Source of calorie calculation
        
    Raises:
        HTTPException:
            - 404 if assessment not found
            - 404 if no targets found (targets not yet calculated)
    """
    # Validate assessment exists
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(assessment_id)
    
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {assessment_id} not found"
        )
    
    # Get targets from database
    target_repository = PlatformNutritionTargetRepository(db)
    target = target_repository.get_by_assessment_id(assessment_id)
    
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No targets found for assessment {assessment_id}. Please calculate targets first."
        )
    
    return TargetResponse(
        calories_target=float(target.calories_target) if target.calories_target else 0.0,
        macros=target.macros or {},
        key_micros=target.key_micros or {},
        calculation_source=target.calculation_source or "unknown"
    )


@router.get("/{assessment_id}/meal-structure", response_model=MealStructureResponse)
async def get_meal_structure(
    assessment_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get meal structure for an assessment.
    
    Retrieves stored meal structure (structural skeleton of daily meal plan)
    that was previously generated for this assessment.
    
    Args:
        assessment_id: Assessment UUID
        db: Database session
        
    Returns:
        Meal structure results with:
        - meal_count: Number of meals
        - meals: List of meal names
        - timing_windows: Timing windows for each meal
        - calorie_split: Calorie allocation per meal
        - protein_split: Protein distribution per meal
        - macro_guardrails: Macro guardrails per meal
        - flags: Validation flags
        
    Raises:
        HTTPException:
            - 404 if assessment not found
            - 404 if no meal structure found (meal structure not yet generated)
    """
    # Validate assessment exists
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(assessment_id)
    
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {assessment_id} not found"
        )
    
    # Get meal structure from database
    meal_structure_repository = PlatformMealStructureRepository(db)
    meal_structure = meal_structure_repository.get_by_assessment_id(assessment_id)
    
    if not meal_structure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No meal structure found for assessment {assessment_id}. Please generate meal structure first."
        )
    
    # Get new fields if available, otherwise use legacy fields
    energy_weight = getattr(meal_structure, 'energy_weight', None) or meal_structure.calorie_split or {}
    
    return MealStructureResponse(
        meal_count=meal_structure.meal_count,
        meals=meal_structure.meals or [],
        timing_windows=meal_structure.timing_windows or {},
        energy_weight=energy_weight,
        flags=meal_structure.flags or [],
        # Legacy fields for backward compatibility
        calorie_split=getattr(meal_structure, 'calorie_split', {}) or {},
        protein_split=getattr(meal_structure, 'protein_split', {}) or {},
        macro_guardrails=getattr(meal_structure, 'macro_guardrails', {}) or {}
    )


@router.get("/exchange-categories")
async def get_exchange_categories(
    assessment_id: Optional[str] = Query(default=None, description="Optional assessment ID (ignored, kept for backward compatibility)")
):
    """
    Get list of exchange categories for UI.
    
    Returns a simple list of all available exchange categories with their
    category IDs and display names from the core food groups configuration.
    
    Args:
        assessment_id: Optional assessment ID (ignored, kept for backward compatibility)
    
    Returns:
        List of dictionaries with:
        - exchange_category_id: Exchange category identifier
        - display_name: Human-readable name
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"get_exchange_categories called with assessment_id={assessment_id}")
        from app.platform.engines.exchange_system_engine.kb_exchange_system import get_core_food_groups
        
        core_config = get_core_food_groups()
        logger.info(f"Core config loaded: {core_config is not None}")
        
        if not core_config:
            logger.warning("No core config found, returning empty list")
            return []
        
        core_groups = core_config.get("core_food_groups", [])
        logger.info(f"Found {len(core_groups)} core food groups")
        
        # Return simple list with only exchange_category_id and display_name
        categories = []
        for group in core_groups:
            category_id = group.get("exchange_category_id")
            display_name = group.get("display_name")
            
            if category_id and display_name:
                categories.append({
                    "exchange_category_id": category_id,
                    "display_name": display_name
                })
        
        logger.info(f"Returning {len(categories)} categories")
        return categories
    except Exception as e:
        logger.error(f"Error in get_exchange_categories: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get exchange categories: {str(e)}"
        )


@router.get("/{assessment_id}/exchange-allocation", response_model=ExchangeAllocationResponse)
async def get_exchange_allocation(
    assessment_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get exchange allocation for an assessment.
    
    Retrieves stored exchange allocation that was previously generated for this assessment.
    
    Args:
        assessment_id: Assessment UUID
        db: Database session
        
    Returns:
        Exchange allocation results with:
        - exchanges_per_meal: Dictionary mapping meal names to exchange counts
        - notes: Information about modifiers applied
        
    Raises:
        HTTPException:
            - 404 if assessment not found
            - 404 if no exchange allocation found (exchange allocation not yet generated)
    """
    # Validate assessment exists
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(assessment_id)
    
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {assessment_id} not found"
        )
    
    # Get exchange allocation from database
    exchange_repository = PlatformExchangeAllocationRepository(db)
    exchange_allocation = exchange_repository.get_by_assessment_id(assessment_id)
    
    if not exchange_allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No exchange allocation found for assessment {assessment_id}. Please generate exchange allocation first."
        )
    
    # Ensure notes is always a dict
    notes = {}
    if exchange_allocation.notes:
        notes = exchange_allocation.notes if isinstance(exchange_allocation.notes, dict) else {}
    
    # For GET endpoint, return stored data
    return ExchangeAllocationResponse(
        exchanges_per_meal=exchange_allocation.exchanges_per_meal or {},
        daily_exchange_allocation=exchange_allocation.daily_exchange_allocation if hasattr(exchange_allocation, 'daily_exchange_allocation') else None,
        user_mandatory_applied=None,  # Not stored in DB, only available during POST execution
        notes=notes,
    )


@router.get("/{assessment_id}/ayurveda", response_model=AyurvedaResponse)
async def get_ayurveda(
    assessment_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get Ayurveda profile for an assessment.
    
    Retrieves stored Ayurveda advisory (dosha assessment and lifestyle guidelines)
    that were previously processed for this assessment.
    
    Args:
        assessment_id: Assessment UUID
        db: Database session
        
    Returns:
        AyurvedaResponse with:
        - dosha_primary: Primary dosha type
        - dosha_secondary: Secondary dosha type
        - vikriti_notes: Vikriti assessment notes
        - lifestyle_guidelines: Lifestyle and food recommendations
        
    Raises:
        HTTPException:
            - 404 if assessment not found
            - 404 if no Ayurveda profile found (Ayurveda not yet processed)
    """
    # Validate assessment exists
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(assessment_id)
    
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {assessment_id} not found"
        )
    
    # Get Ayurveda profile from database
    ayurveda_repository = PlatformAyurvedaProfileRepository(db)
    profile = ayurveda_repository.get_by_assessment_id(assessment_id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Ayurveda profile found for assessment {assessment_id}. Please process Ayurveda first."
        )
    
    return AyurvedaResponse(
        dosha_primary=profile.dosha_primary,
        dosha_secondary=profile.dosha_secondary,
        vikriti_notes=profile.vikriti_notes or {},
        lifestyle_guidelines=profile.lifestyle_guidelines or {}
    )


@router.get("/{assessment_id}/intervention", response_model=InterventionResponse)
async def get_intervention(
    assessment_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get food intervention results for an assessment.
    
    Retrieves stored intervention results (meal plan with foods) that were
    previously generated for this assessment.
    
    Args:
        assessment_id: Assessment UUID
        db: Database session
        
    Returns:
        Intervention results with:
        - assessment_id: Assessment UUID
        - plan_id: Plan UUID
        - plan_version: Plan version number
        - meal_plan: Meal plan with category-wise food lists
        - explanations: Explanations and reasoning
        - constraints_snapshot: Snapshot of constraints used
        
    Raises:
        HTTPException:
            - 404 if assessment not found
            - 404 if no intervention found (intervention not yet processed)
    """
    # Validate assessment exists
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(assessment_id)
    
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {assessment_id} not found"
        )
    
    # Get plan (intervention result) from database
    plan_repository = PlatformDietPlanRepository(db)
    plans = plan_repository.get_by_assessment_id(assessment_id)
    
    if not plans:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No intervention found for assessment {assessment_id}. Please process intervention first."
        )
    
    # Use the latest plan
    plan_record = max(plans, key=lambda p: p.plan_version or 1)
    
    return InterventionResponse(
        assessment_id=str(plan_record.assessment_id),
        plan_id=str(plan_record.id),
        plan_version=plan_record.plan_version,
        meal_plan=plan_record.meal_plan or {},
        explanations=plan_record.explanations or {},
        constraints_snapshot=plan_record.constraints_snapshot or {}
    )


@router.get("/{assessment_id}/recipe-generation", response_model=RecipeResponse)
async def get_recipe_generation(
    assessment_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get recipe generation results for an assessment.
    
    Retrieves stored recipe generation results (7-day meal plan with recipes)
    that were previously generated for this assessment.
    
    Args:
        assessment_id: Assessment UUID
        db: Database session
        
    Returns:
        Recipe generation results with:
        - assessment_id: Assessment UUID
        - plan_id: Plan UUID
        - plan_version: Plan version number
        - seven_day_plan: 7-day meal plan with recipes and variety
        - variety_metrics: Metrics about recipe variety
        
    Raises:
        HTTPException:
            - 404 if assessment not found
            - 404 if no recipe generation found (recipe generation not yet processed)
    """
    # Validate assessment exists
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(assessment_id)
    
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {assessment_id} not found"
        )
    
    # Get plan from database
    plan_repository = PlatformDietPlanRepository(db)
    plans = plan_repository.get_by_assessment_id(assessment_id)
    
    if not plans:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No plan found for assessment {assessment_id}. Please process intervention first."
        )
    
    # Use the latest plan
    plan_record = max(plans, key=lambda p: p.plan_version or 1)
    
    # Check if recipe generation has been done (has seven_day_plan in meal_plan)
    meal_plan = plan_record.meal_plan or {}
    seven_day_plan = meal_plan.get("seven_day_plan")
    
    if not seven_day_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No recipe generation found for assessment {assessment_id}. Please process recipe generation first."
        )
    
    variety_metrics = seven_day_plan.get("variety_metrics", {})
    
    return RecipeResponse(
        assessment_id=str(plan_record.assessment_id),
        plan_id=str(plan_record.id),
        plan_version=plan_record.plan_version,
        seven_day_plan=seven_day_plan,
        variety_metrics=variety_metrics
    )


@router.get("/{assessment_id}/status")
async def get_ncp_status(
    assessment_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get NCP (Nutrition Care Process) status/progress for an assessment.
    
    Returns which steps have been completed and which step is currently active.
    This helps the UI determine what actions are available to the user.
    
    Args:
        assessment_id: Assessment UUID
        db: Database session
        
    Returns:
        Dictionary with:
        - assessment_id: Assessment UUID
        - steps: Dictionary indicating completion status of each step
        - current_step: The next step that should be executed
        
    Raises:
        HTTPException:
            - 404 if assessment not found
    """
    # Validate assessment exists
    assessment_repository = PlatformAssessmentRepository(db)
    assessment = assessment_repository.get_by_id(assessment_id)
    
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {assessment_id} not found"
        )
    
    # Check completion status of each step
    diagnosis_repository = PlatformDiagnosisRepository(db)
    mnt_repository = PlatformMNTConstraintRepository(db)
    target_repository = PlatformNutritionTargetRepository(db)
    meal_structure_repository = PlatformMealStructureRepository(db)
    ayurveda_repository = PlatformAyurvedaProfileRepository(db)
    plan_repository = PlatformDietPlanRepository(db)
    
    # Check each step
    # For diagnosis: Check if diagnosis was executed (including marker records for healthy persons)
    diagnosis_records = diagnosis_repository.get_by_assessment_id(assessment_id)
    has_diagnosis = len(diagnosis_records) > 0  # True if executed, even if no diagnoses found
    
    has_mnt = len(mnt_repository.get_by_assessment_id(assessment_id)) > 0
    has_targets = target_repository.get_by_assessment_id(assessment_id) is not None
    has_meal_structure = meal_structure_repository.get_by_assessment_id(assessment_id) is not None
    exchange_repository = PlatformExchangeAllocationRepository(db)
    has_exchange_allocation = exchange_repository.get_by_assessment_id(assessment_id) is not None
    has_ayurveda = ayurveda_repository.get_by_assessment_id(assessment_id) is not None
    plans = plan_repository.get_by_assessment_id(assessment_id)
    has_plan = len(plans) > 0
    
    # Check if intervention exists (plan without recipe generation)
    has_intervention = False
    has_food_allocation = False
    has_recipe_generation = False
    if has_plan:
        latest_plan = max(plans, key=lambda p: p.plan_version or 1)
        meal_plan = latest_plan.meal_plan or {}
        has_intervention = bool(meal_plan)  # Plan exists = intervention done
        has_food_allocation = bool(meal_plan.get("meal_allocation"))  # Has food allocation = Phase 1 done
        has_recipe_generation = bool(meal_plan.get("seven_day_plan"))  # Has recipes = recipe generation done
    
    # Determine current step (next step to execute)
    if has_recipe_generation:
        current_step = "recipe_generation"
    elif has_food_allocation:
        # Check if meals are approved
        approval_repo = PlatformFoodAllocationApprovalRepository(db)
        approvals = approval_repo.get_by_assessment_id(assessment_id)
        has_approved_meals = any(a.is_approved for a in approvals)
        
        if has_approved_meals:
            current_step = "recipe_generation"
        else:
            current_step = "food_allocation"  # Need to approve meals
    elif has_intervention:
        current_step = "food_allocation"
    elif has_ayurveda:
        current_step = "intervention"
    elif has_exchange_allocation:
        current_step = "ayurveda"  # Ayurveda is optional, can skip to intervention
    elif has_meal_structure:
        current_step = "exchange_allocation"
    elif has_targets:
        current_step = "meal_structure"
    elif has_mnt:
        current_step = "targets"
    elif has_diagnosis:
        current_step = "mnt"
    else:
        current_step = "diagnosis"
    
    return {
        "assessment_id": str(assessment_id),
        "steps": {
            "intake": True,  # Always true if assessment exists
            "assessment": True,  # Always true
            "diagnosis": has_diagnosis,
            "mnt": has_mnt,
            "targets": has_targets,
            "meal_structure": has_meal_structure,
            "exchange_allocation": has_exchange_allocation,
            "ayurveda": has_ayurveda,
            "intervention": has_intervention,
            "food_allocation": has_food_allocation,
            "recipe_generation": has_recipe_generation
        },
        "current_step": current_step
    }

