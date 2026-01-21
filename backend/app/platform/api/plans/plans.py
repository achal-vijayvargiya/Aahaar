"""
Platform Plans API Routes.
Diet plan generation and retrieval endpoints.
"""
from typing import Optional, Dict, Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from sqlalchemy.orm import Session

from app.database import get_db
from app.platform.data.repositories.platform_assessment_repository import PlatformAssessmentRepository
from app.platform.data.repositories.platform_client_repository import PlatformClientRepository
from app.platform.data.repositories.platform_diet_plan_repository import PlatformDietPlanRepository
from app.platform.data.repositories.platform_mnt_constraint_repository import PlatformMNTConstraintRepository
from app.platform.data.repositories.platform_nutrition_target_repository import PlatformNutritionTargetRepository
from app.platform.data.repositories.platform_ayurveda_profile_repository import PlatformAyurvedaProfileRepository
from app.platform.core.orchestration.ncp_orchestrator import NCPOrchestrator
from app.platform.core.context import InterventionContext, MNTContext, TargetContext, AyurvedaContext

router = APIRouter(prefix="/plans", tags=["Platform Plans"])


# Request/Response Models (Placeholders)
class PlanGenerateRequest(BaseModel):
    """Plan generation request model."""
    client_id: UUID
    assessment_id: UUID
    client_preferences: Optional[Dict[str, Any]] = None
    enable_ayurveda: Optional[bool] = True


class PlanResponse(BaseModel):
    """Plan response model."""
    id: UUID
    client_id: UUID
    assessment_id: UUID
    plan_version: Optional[int]
    status: Optional[str]  # active | archived | draft
    meal_plan: Optional[Dict[str, Any]]
    explanations: Optional[Dict[str, Any]]
    constraints_snapshot: Optional[Dict[str, Any]]
    created_at: str


class PlanUpdateRequest(BaseModel):
    """Plan update request model."""
    status: Optional[str]  # active | archived | draft
    meal_plan: Optional[Dict[str, Any]]
    explanations: Optional[Dict[str, Any]]


@router.post("/generate", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def generate_plan(
    plan_request: PlanGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    Generate diet plan for a client.
    
    Args:
        plan_request: Plan generation request with client and assessment IDs
        
    Returns:
        Generated diet plan
        
    Note:
        Delegates to orchestration layer which executes full NCP pipeline:
        Intake → Assessment → Diagnosis → MNT → Target → Ayurveda → Intervention
        This endpoint triggers the full plan generation process.
    """
    client_repo = PlatformClientRepository(db)
    client = client_repo.get_by_id(plan_request.client_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {plan_request.client_id} not found"
        )

    assessment_repo = PlatformAssessmentRepository(db)
    assessment = assessment_repo.get_by_id(plan_request.assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment {plan_request.assessment_id} not found"
        )

    orchestrator = NCPOrchestrator(db=db, client_id=plan_request.client_id, enable_ayurveda=bool(plan_request.enable_ayurveda))
    pipeline = orchestrator.execute_full_pipeline(
        assessment_id=plan_request.assessment_id,
        client_preferences=plan_request.client_preferences,
        enable_ayurveda=plan_request.enable_ayurveda
    )

    intervention: InterventionContext = pipeline["intervention"]

    plan_repo = PlatformDietPlanRepository(db)
    plan_record = plan_repo.get_by_id(intervention.plan_id) if intervention.plan_id else None
    if plan_record is None:
        plans = plan_repo.get_by_assessment_id(plan_request.assessment_id)
        if plans:
            plan_record = sorted(plans, key=lambda p: p.plan_version or 1, reverse=True)[0]
    if plan_record is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Plan generation failed to persist plan record")

    return PlanResponse(
        id=plan_record.id,
        client_id=plan_record.client_id,
        assessment_id=plan_record.assessment_id,
        plan_version=plan_record.plan_version,
        status=plan_record.status,
        meal_plan=plan_record.meal_plan,
        explanations=plan_record.explanations,
        constraints_snapshot=plan_record.constraints_snapshot,
        created_at=str(plan_record.created_at),
    )


@router.post("/generate-intervention", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def generate_intervention_only(
    plan_request: PlanGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    Generate diet plan by running only the intervention stage.
    
    This endpoint loads existing MNT constraints, nutrition targets, and Ayurveda profile
    from previous NCP steps and runs only the intervention stage to generate the plan.
    This is useful when all previous steps have already been completed.
    
    Args:
        plan_request: Plan generation request with client and assessment IDs
        
    Returns:
        Generated diet plan
        
    Raises:
        HTTPException:
            - 404 if client, assessment, MNT, or targets not found
            - 400 if required data is missing
            
    Note:
        This endpoint requires:
        - MNT constraints must exist (from MNT step)
        - Nutrition targets must exist (from Targets step)
        - Ayurveda profile is optional (if not processed, empty context is used)
    """
    # Validate client exists
    client_repo = PlatformClientRepository(db)
    client = client_repo.get_by_id(plan_request.client_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {plan_request.client_id} not found"
        )

    # Validate assessment exists
    assessment_repo = PlatformAssessmentRepository(db)
    assessment = assessment_repo.get_by_id(plan_request.assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment {plan_request.assessment_id} not found"
        )

    # Load existing MNT constraints (required)
    mnt_repo = PlatformMNTConstraintRepository(db)
    mnt_constraints = mnt_repo.get_by_assessment_id(plan_request.assessment_id)
    if not mnt_constraints:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No MNT constraints found for assessment {plan_request.assessment_id}. Please run MNT step first."
        )
    mnt_record = mnt_constraints[0]  # Use the first (merged) constraint
    
    # Build MNTContext from existing data
    rule_ids_used = []
    if mnt_record.rule_id:
        rule_ids_used = [r.strip() for r in mnt_record.rule_id.split(",") if r.strip()]
    mnt_context = MNTContext(
        assessment_id=plan_request.assessment_id,
        macro_constraints=mnt_record.macro_constraints or {},
        micro_constraints=mnt_record.micro_constraints or {},
        food_exclusions=mnt_record.food_exclusions or [],
        rule_ids_used=rule_ids_used
    )

    # Load existing nutrition targets (required)
    target_repo = PlatformNutritionTargetRepository(db)
    target = target_repo.get_by_assessment_id(plan_request.assessment_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No nutrition targets found for assessment {plan_request.assessment_id}. Please run Targets step first."
        )
    
    # Build TargetContext from existing data
    target_context = TargetContext(
        assessment_id=plan_request.assessment_id,
        calories_target=float(target.calories_target) if target.calories_target is not None else None,
        macros=target.macros if target else None,
        key_micros=target.key_micros if target else None,
        calculation_source=target.calculation_source if target else None
    )

    # Load existing Ayurveda profile (optional)
    ayurveda_repo = PlatformAyurvedaProfileRepository(db)
    ayurveda_profile = ayurveda_repo.get_by_assessment_id(plan_request.assessment_id)
    
    # Build AyurvedaContext from existing data (or empty if not processed)
    ayurveda_context = AyurvedaContext(
        assessment_id=plan_request.assessment_id,
        dosha_primary=ayurveda_profile.dosha_primary if ayurveda_profile else None,
        dosha_secondary=ayurveda_profile.dosha_secondary if ayurveda_profile else None,
        vikriti_notes=ayurveda_profile.vikriti_notes if ayurveda_profile else None,
        lifestyle_guidelines=ayurveda_profile.lifestyle_guidelines if ayurveda_profile else None
    )

    # Create orchestrator and execute only intervention stage
    orchestrator = NCPOrchestrator(
        db=db,
        client_id=plan_request.client_id,
        enable_ayurveda=bool(plan_request.enable_ayurveda) if plan_request.enable_ayurveda is not None else True
    )
    
    # Load assessment snapshot for orchestrator (needed for some internal operations)
    orchestrator._assessment_snapshot = assessment.assessment_snapshot or {}
    
    # Execute only intervention stage
    intervention = orchestrator.execute_intervention_stage(
        mnt_context=mnt_context,
        target_context=target_context,
        ayurveda_context=ayurveda_context,
        client_preferences=plan_request.client_preferences
    )

    # Get the created plan record
    plan_repo = PlatformDietPlanRepository(db)
    plan_record = plan_repo.get_by_id(intervention.plan_id) if intervention.plan_id else None
    if plan_record is None:
        # Fallback: get latest plan for this assessment
        plans = plan_repo.get_by_assessment_id(plan_request.assessment_id)
        if plans:
            plan_record = sorted(plans, key=lambda p: p.plan_version or 1, reverse=True)[0]
    
    if plan_record is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Plan generation failed to persist plan record"
        )

    return PlanResponse(
        id=plan_record.id,
        client_id=plan_record.client_id,
        assessment_id=plan_record.assessment_id,
        plan_version=plan_record.plan_version,
        status=plan_record.status,
        meal_plan=plan_record.meal_plan,
        explanations=plan_record.explanations,
        constraints_snapshot=plan_record.constraints_snapshot,
        created_at=str(plan_record.created_at),
    )


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get diet plan by ID.
    
    Args:
        plan_id: Plan UUID
        
    Returns:
        Diet plan information
        
    Raises:
        HTTPException: If plan not found
        
    Note:
        Delegates to plan service. No business logic here.
    """
    plan_repo = PlatformDietPlanRepository(db)
    plan = plan_repo.get_by_id(plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return PlanResponse(
        id=plan.id,
        client_id=plan.client_id,
        assessment_id=plan.assessment_id,
        plan_version=plan.plan_version,
        status=plan.status,
        meal_plan=plan.meal_plan,
        explanations=plan.explanations,
        constraints_snapshot=plan.constraints_snapshot,
        created_at=str(plan.created_at),
    )


@router.get("/client/{client_id}", response_model=List[PlanResponse])
async def get_client_plans(
    client_id: UUID,
    status_filter: Optional[str] = Query(None, description="Filter by status: active | archived | draft"),
    db: Session = Depends(get_db)
):
    """
    Get all diet plans for a client.
    
    Args:
        client_id: Client UUID
        status_filter: Optional status filter
        
    Returns:
        List of diet plans
        
    Note:
        Delegates to plan service. No business logic here.
    """
    client_repo = PlatformClientRepository(db)
    if client_repo.get_by_id(client_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    plan_repo = PlatformDietPlanRepository(db)
    plans = plan_repo.get_by_client_id(client_id)
    if status_filter:
        plans = [p for p in plans if p.status == status_filter]

    return [
        PlanResponse(
            id=p.id,
            client_id=p.client_id,
            assessment_id=p.assessment_id,
            plan_version=p.plan_version,
            status=p.status,
            meal_plan=p.meal_plan,
            explanations=p.explanations,
            constraints_snapshot=p.constraints_snapshot,
            created_at=str(p.created_at),
        )
        for p in plans
    ]


@router.get("/client/{client_id}/active", response_model=Optional[PlanResponse])
async def get_active_plan(
    client_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get active diet plan for a client.
    
    Args:
        client_id: Client UUID
        
    Returns:
        Active diet plan or None
        
    Note:
        Delegates to plan service. No business logic here.
    """
    client_repo = PlatformClientRepository(db)
    if client_repo.get_by_id(client_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    plan_repo = PlatformDietPlanRepository(db)
    plans = plan_repo.get_by_client_id(client_id)
    active_plans = [p for p in plans if p.status == "active"]
    if not active_plans:
        return None
    # pick latest by version
    plan = sorted(active_plans, key=lambda p: p.plan_version or 1, reverse=True)[0]
    return PlanResponse(
        id=plan.id,
        client_id=plan.client_id,
        assessment_id=plan.assessment_id,
        plan_version=plan.plan_version,
        status=plan.status,
        meal_plan=plan.meal_plan,
        explanations=plan.explanations,
        constraints_snapshot=plan.constraints_snapshot,
        created_at=str(plan.created_at),
    )


@router.put("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: UUID,
    plan_data: PlanUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update diet plan.
    
    Args:
        plan_id: Plan UUID
        plan_data: Plan update data
        
    Returns:
        Updated diet plan information
        
    Raises:
        HTTPException: If plan not found
        
    Note:
        Delegates to plan service. No business logic here.
    """
    plan_repo = PlatformDietPlanRepository(db)
    existing = plan_repo.get_by_id(plan_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    update_payload = {}
    if plan_data.status is not None:
        update_payload["status"] = plan_data.status
    if plan_data.meal_plan is not None:
        update_payload["meal_plan"] = plan_data.meal_plan
    if plan_data.explanations is not None:
        update_payload["explanations"] = plan_data.explanations

    updated = plan_repo.update(plan_id, update_payload)
    return PlanResponse(
        id=updated.id,
        client_id=updated.client_id,
        assessment_id=updated.assessment_id,
        plan_version=updated.plan_version,
        status=updated.status,
        meal_plan=updated.meal_plan,
        explanations=updated.explanations,
        constraints_snapshot=updated.constraints_snapshot,
        created_at=str(updated.created_at),
    )


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete diet plan.
    
    Args:
        plan_id: Plan UUID
        
    Raises:
        HTTPException: If plan not found
        
    Note:
        Delegates to plan service. No business logic here.
    """
    plan_repo = PlatformDietPlanRepository(db)
    deleted = plan_repo.delete(plan_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return


@router.post("/{plan_id}/archive", response_model=PlanResponse)
async def archive_plan(
    plan_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Archive a diet plan.
    
    Args:
        plan_id: Plan UUID
        
    Returns:
        Archived plan information
        
    Raises:
        HTTPException: If plan not found
        
    Note:
        Delegates to plan service. No business logic here.
    """
    plan_repo = PlatformDietPlanRepository(db)
    existing = plan_repo.get_by_id(plan_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    updated = plan_repo.update(plan_id, {"status": "archived"})
    return PlanResponse(
        id=updated.id,
        client_id=updated.client_id,
        assessment_id=updated.assessment_id,
        plan_version=updated.plan_version,
        status=updated.status,
        meal_plan=updated.meal_plan,
        explanations=updated.explanations,
        constraints_snapshot=updated.constraints_snapshot,
        created_at=str(updated.created_at),
    )

