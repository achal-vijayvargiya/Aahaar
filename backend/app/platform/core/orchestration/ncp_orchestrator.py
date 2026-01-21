"""
Platform NCP Orchestrator.
Controls Nutrition Care Process pipeline execution.
"""
from typing import Optional, Dict, Any
from uuid import UUID
import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.platform.core.context import (
    AssessmentContext,
    DiagnosisContext,
    MNTContext,
    TargetContext,
    MealStructureContext,
    ExchangeContext,
    AyurvedaContext,
    InterventionContext,
    RecipeContext,
)
from app.platform.core.state_machine import ClientStateMachine, ClientState
from app.platform.core.contracts import (
    DiagnosisEngineInput,
    DiagnosisEngineOutput,
    MNTEngineInput,
    MNTEngineOutput,
    TargetEngineInput,
    TargetEngineOutput,
    MealStructureEngineInput,
    MealStructureEngineOutput,
    ExchangeSystemEngineInput,
    ExchangeSystemEngineOutput,
    AyurvedaEngineInput,
    AyurvedaEngineOutput,
    FoodEngineInput,
    FoodEngineOutput,
)
from app.platform.core.contracts.validator import ContractValidationError
from app.platform.core.contracts.engine_validator import validate_engine_input, validate_engine_output
from app.platform.data.repositories.platform_assessment_repository import PlatformAssessmentRepository
from app.platform.data.repositories.platform_diagnosis_repository import PlatformDiagnosisRepository
from app.platform.data.repositories.platform_mnt_constraint_repository import PlatformMNTConstraintRepository
from app.platform.data.repositories.platform_nutrition_target_repository import PlatformNutritionTargetRepository
from app.platform.data.repositories.platform_meal_structure_repository import PlatformMealStructureRepository
from app.platform.data.repositories.platform_exchange_allocation_repository import PlatformExchangeAllocationRepository
from app.platform.data.repositories.platform_ayurveda_profile_repository import PlatformAyurvedaProfileRepository
from app.platform.data.repositories.platform_diet_plan_repository import PlatformDietPlanRepository
from app.platform.engines.diagnosis_engine.diagnosis_engine import DiagnosisEngine
from app.platform.engines.mnt_engine.mnt_engine import MNTEngine
from app.platform.engines.target_engine.target_engine import TargetEngine
from app.platform.engines.meal_structure_engine.meal_structure_engine import MealStructureEngine
from app.platform.engines.exchange_system_engine.exchange_system_engine import ExchangeSystemEngine
from app.platform.engines.ayurveda_engine.ayurveda_engine import AyurvedaEngine
from app.platform.engines.food_engine.food_engine import FoodEngine
from app.platform.engines.recipe_engine.meal_allocation_engine import MealAllocationEngine
from app.platform.engines.recipe_engine.recipe_generation_engine import RecipeGenerationEngine

logger = logging.getLogger(__name__)


class NCPOrchestrator:
    """
    NCP Pipeline Orchestrator.
    
    Executes the Nutrition Care Process pipeline in strict order:
    Assessment → Diagnosis → MNT → Targets → Meal Structure → Exchange System → Ayurveda (advisory) → Food/Plan → Recipe Generation.
    """
    
    def __init__(self, db: Session, client_id: UUID, enable_ayurveda: bool = True):
        self.db = db
        self.client_id = client_id
        self.enable_ayurveda = enable_ayurveda
        self.state_machine = ClientStateMachine(client_id=self.client_id, initial_state=ClientState.NEW_CLIENT)

        # Repositories
        self.assessment_repo = PlatformAssessmentRepository(db)
        self.diagnosis_repo = PlatformDiagnosisRepository(db)
        self.mnt_repo = PlatformMNTConstraintRepository(db)
        self.target_repo = PlatformNutritionTargetRepository(db)
        self.meal_structure_repo = PlatformMealStructureRepository(db)
        self.exchange_repo = PlatformExchangeAllocationRepository(db)
        self.ayurveda_repo = PlatformAyurvedaProfileRepository(db)
        self.plan_repo = PlatformDietPlanRepository(db)

        # Engines
        self.diagnosis_engine = DiagnosisEngine()
        self.mnt_engine = MNTEngine()
        self.target_engine = TargetEngine()
        self.meal_structure_engine = MealStructureEngine()
        self.exchange_engine = ExchangeSystemEngine()
        self.ayurveda_engine = AyurvedaEngine()
        self.food_engine = FoodEngine()
        # Phase 1: Meal Allocation Engine (deterministic food allocation)
        self.meal_allocation_engine = MealAllocationEngine()
        # Phase 2: Recipe Generation Engine (LLM-based recipe generation)
        self.recipe_generation_engine = RecipeGenerationEngine()

        # Cached assessment snapshot for downstream
        self._assessment_snapshot: Dict[str, Any] = {}

    # --- Stage execution helpers -------------------------------------------------
    def execute_assessment_stage(self, assessment_id: UUID) -> AssessmentContext:
        assessment = self.assessment_repo.get_by_id(assessment_id)
        if assessment is None:
            raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found")
        
        # NEW: Validate and normalize assessment snapshot (Bug 1.1 & 1.2)
        snapshot = assessment.assessment_snapshot or {}
        validated_snapshot = self._validate_and_normalize_assessment_snapshot(snapshot)
        
        self._assessment_snapshot = validated_snapshot
        return AssessmentContext(
            assessment_id=assessment.id,
            intake_id=assessment.intake_id,
            client_id=assessment.client_id,
            assessment_snapshot=validated_snapshot,
            assessment_status=assessment.assessment_status,
        )
    
    def _validate_and_normalize_assessment_snapshot(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize assessment snapshot (Bug 1.1 & 1.2).
        
        Ensures required fields are present and adds default values where appropriate.
        Specifically ensures reproductive_context is properly structured for diagnosis eligibility checks.
        
        Args:
            snapshot: Raw assessment snapshot from database
            
        Returns:
            Validated and normalized assessment snapshot
        """
        if not isinstance(snapshot, dict):
            raise ValueError("Assessment snapshot must be a dictionary")
        
        # Ensure client_context exists
        client_context = snapshot.get("client_context", {})
        if not isinstance(client_context, dict):
            client_context = {}
        snapshot["client_context"] = client_context
        
        # NEW: Add reproductive_context validation and normalization (Bug 1.1)
        gender = client_context.get("gender", "").lower() if isinstance(client_context.get("gender"), str) else ""
        reproductive_context = snapshot.get("reproductive_context", {})
        
        # Ensure reproductive_context is a dict
        if not isinstance(reproductive_context, dict):
            reproductive_context = {}
        
        # For females, ensure pregnancy_status is set (default: not_pregnant)
        if gender in ["female", "f"]:
            pregnancy_status = reproductive_context.get("pregnancy_status")
            
            # If pregnancy_status is not set, default to not_pregnant
            if pregnancy_status is None:
                reproductive_context["pregnancy_status"] = "not_pregnant"
            elif pregnancy_status == "pregnant":
                # If pregnant, gestational_weeks should be provided
                gestational_weeks = reproductive_context.get("gestational_weeks")
                if gestational_weeks is None:
                    logger.warning(
                        "Pregnancy status is 'pregnant' but gestational_weeks is missing. "
                        "This may cause issues with gestational diabetes diagnosis."
                    )
                    # Don't fail, but log warning - UI should collect this
        
        # Update snapshot with normalized reproductive_context
        snapshot["reproductive_context"] = reproductive_context
        
        # NEW: Validate required fields for diagnosis eligibility (Bug 1.2)
        # Ensure age is present (required for eligibility checks)
        age = client_context.get("age")
        if age is None:
            logger.warning(
                "Age is missing from client_context. This may prevent proper eligibility "
                "validation for age-restricted conditions."
            )
        
        # Ensure gender is present (required for gender-based eligibility checks)
        if not gender or gender not in ["male", "m", "female", "f", "other"]:
            logger.warning(
                "Gender is missing or invalid in client_context. This may prevent proper "
                "eligibility validation for gender-restricted conditions."
            )
        
        return snapshot

    def execute_diagnosis_stage(self, assessment_context: AssessmentContext) -> DiagnosisContext:
        # State enforcement
        self.state_machine.transition_to(ClientState.INTAKE_COMPLETED)

        # Validate input contract
        try:
            input_data = {
                "assessment_id": assessment_context.assessment_id,
                "assessment_snapshot": assessment_context.assessment_snapshot
            }
            validate_engine_input("DiagnosisEngine", input_data, DiagnosisEngineInput)
        except ContractValidationError as e:
            logger.error(f"Diagnosis engine input validation failed: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid input for diagnosis engine: {str(e)}")

        diagnosis_context = self.diagnosis_engine.process_assessment(assessment_context)

        # Validate output contract
        try:
            output_data = {
                "assessment_id": diagnosis_context.assessment_id,
                "medical_conditions": diagnosis_context.medical_conditions,
                "nutrition_diagnoses": diagnosis_context.nutrition_diagnoses
            }
            validate_engine_output("DiagnosisEngine", output_data, DiagnosisEngineOutput)
        except ContractValidationError as e:
            logger.error(f"Diagnosis engine output validation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Invalid output from diagnosis engine: {str(e)}")

        # Persist diagnoses
        for diag in diagnosis_context.medical_conditions:
            self.diagnosis_repo.create({
                "assessment_id": assessment_context.assessment_id,
                "diagnosis_type": "medical",
                "diagnosis_id": diag["diagnosis_id"],
                "severity_score": diag.get("severity_score"),
                "evidence": diag.get("evidence"),
            })
        for diag in diagnosis_context.nutrition_diagnoses:
            self.diagnosis_repo.create({
                "assessment_id": assessment_context.assessment_id,
                "diagnosis_type": "nutrition",
                "diagnosis_id": diag["diagnosis_id"],
                "severity_score": diag.get("severity_score"),
                "evidence": diag.get("evidence"),
            })

        self.state_machine.transition_to(ClientState.DIAGNOSED)
        return diagnosis_context

    def execute_mnt_stage(self, diagnosis_context: DiagnosisContext) -> MNTContext:
        if self.state_machine.get_current_state() != ClientState.DIAGNOSED:
            raise HTTPException(status_code=400, detail="Cannot run MNT before diagnosis.")

        # Validate input contract
        try:
            input_data = {
                "assessment_id": diagnosis_context.assessment_id,
                "medical_conditions": diagnosis_context.medical_conditions,
                "nutrition_diagnoses": diagnosis_context.nutrition_diagnoses
            }
            validate_engine_input("MNTEngine", input_data, MNTEngineInput)
        except ContractValidationError as e:
            logger.error(f"MNT engine input validation failed: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid input for MNT engine: {str(e)}")

        mnt_context = self.mnt_engine.process_diagnoses(diagnosis_context)

        # Validate output contract
        try:
            output_data = {
                "assessment_id": mnt_context.assessment_id,
                "macro_constraints": mnt_context.macro_constraints,
                "micro_constraints": mnt_context.micro_constraints,
                "food_exclusions": mnt_context.food_exclusions,
                "rule_ids_used": mnt_context.rule_ids_used
            }
            validate_engine_output("MNTEngine", output_data, MNTEngineOutput)
        except ContractValidationError as e:
            logger.error(f"MNT engine output validation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Invalid output from MNT engine: {str(e)}")

        # Persist merged constraint (single record)
        self.mnt_repo.create({
            "assessment_id": diagnosis_context.assessment_id,
            "rule_id": ",".join(mnt_context.rule_ids_used) if mnt_context.rule_ids_used else None,
            "priority": 3,
            "macro_constraints": mnt_context.macro_constraints,
            "micro_constraints": mnt_context.micro_constraints,
            "food_exclusions": mnt_context.food_exclusions,
        })

        return mnt_context

    def execute_target_stage(self, mnt_context: MNTContext, diagnosis_context: Optional[DiagnosisContext] = None) -> TargetContext:
        # Build client_profile from assessment snapshot
        client_context = self._assessment_snapshot.get("client_context", {}) if self._assessment_snapshot else {}
        anthropometry = self._assessment_snapshot.get("clinical_data", {}).get("anthropometry", {}) if self._assessment_snapshot else {}
        goals = self._assessment_snapshot.get("goals", {}) if self._assessment_snapshot else {}
        
        client_profile = {
            "age": client_context.get("age"),
            "gender": client_context.get("gender"),
            "height_cm": client_context.get("height_cm") or anthropometry.get("height_cm"),
            "weight_kg": client_context.get("weight_kg") or anthropometry.get("weight_kg"),
            "activity_level": client_context.get("activity_level"),
            "goals": goals,  # Include goals for weight loss/gain calculations
        }

        # Validate input contract
        try:
            input_data = {
                "assessment_id": mnt_context.assessment_id,
                "client_profile": client_profile,
                "mnt_context": mnt_context
            }
            validate_engine_input("TargetEngine", input_data, TargetEngineInput)
        except ContractValidationError as e:
            logger.error(f"Target engine input validation failed: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid input for target engine: {str(e)}")

        target_context = self.target_engine.calculate_targets(
            client_profile, 
            mnt_context, 
            activity_level=client_profile.get("activity_level"),
            diagnosis_context=diagnosis_context  # Pass for adaptive calculations
        )

        # Validate output contract
        try:
            output_data = {
                "assessment_id": target_context.assessment_id,
                "calories_target": target_context.calories_target,
                "macros": target_context.macros,
                "key_micros": target_context.key_micros,
                "calculation_source": target_context.calculation_source
            }
            validate_engine_output("TargetEngine", output_data, TargetEngineOutput)
        except ContractValidationError as e:
            logger.error(f"Target engine output validation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Invalid output from target engine: {str(e)}")

        # Persist targets (upsert)
        existing = self.target_repo.get_by_assessment_id(mnt_context.assessment_id)
        payload = {
            "assessment_id": mnt_context.assessment_id,
            "calories_target": target_context.calories_target,
            "macros": target_context.macros,
            "key_micros": target_context.key_micros,
            "calculation_source": target_context.calculation_source,
        }
        if existing:
            self.target_repo.update(existing.id, payload)
        else:
            self.target_repo.create(payload)

        return target_context

    def execute_meal_structure_stage(
        self,
        target_context: TargetContext,
        client_preferences: Optional[Dict[str, Any]] = None
    ) -> MealStructureContext:
        """
        Execute meal structure stage.
        
        Generates structural skeleton of daily meal plan (no food items).
        """
        # Generate meal structure using MealStructureEngine
        meal_structure_context = self.meal_structure_engine.generate_structure(
            target_context=target_context,
            assessment_snapshot=self._assessment_snapshot,
            client_preferences=client_preferences
        )
        
        # Store meal structure in database
        existing = self.meal_structure_repo.get_by_assessment_id(target_context.assessment_id)
        structure_data = {
            "assessment_id": target_context.assessment_id,
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
            self.meal_structure_repo.update_by_assessment_id(target_context.assessment_id, structure_data)
        else:
            self.meal_structure_repo.create(structure_data)
        
        return meal_structure_context

    def execute_exchange_stage(
        self,
        meal_structure: MealStructureContext,
        target_context: TargetContext,
        mnt_context: MNTContext,
        ayurveda_context: Optional[AyurvedaContext] = None,
        client_preferences: Optional[Dict[str, Any]] = None
    ) -> ExchangeContext:
        """
        Execute exchange allocation stage.
        
        Translates meal-level calorie and protein targets into exchange units.
        Calculates per-meal targets from daily totals × energy_weight.
        
        Now supports user-mandated exchanges via client_preferences.
        """
        # Extract user-mandated exchanges from client_preferences
        # Support both per-meal format (new) and daily format (legacy)
        user_mandatory_exchanges = None
        user_mandatory_exchanges_per_meal = None
        
        if client_preferences:
            # Check for per-meal format first (preferred)
            if "mandatory_exchanges_per_meal" in client_preferences:
                user_mandatory_exchanges_per_meal = client_preferences.get("mandatory_exchanges_per_meal")
                # Validate structure: should be dict of meal_name -> [category_id, ...]
                if not isinstance(user_mandatory_exchanges_per_meal, dict):
                    logger.warning("Invalid mandatory_exchanges_per_meal format in client_preferences, ignoring")
                    user_mandatory_exchanges_per_meal = None
            
            # Legacy daily format support (for backward compatibility)
            if "mandatory_exchanges" in client_preferences and user_mandatory_exchanges_per_meal is None:
                user_mandatory_exchanges = client_preferences.get("mandatory_exchanges")
                # Validate structure: should be dict of category_id -> min_daily_exchanges
                if not isinstance(user_mandatory_exchanges, dict):
                    logger.warning("Invalid mandatory_exchanges format in client_preferences, ignoring")
                    user_mandatory_exchanges = None
        
        # Generate exchanges using ExchangeSystemEngine
        exchange_result = self.exchange_engine.generate_exchanges(
            meal_structure=meal_structure,
            target_context=target_context,
            mnt_context=mnt_context,
            ayurveda_context=ayurveda_context,
            user_mandatory_exchanges=user_mandatory_exchanges,  # Legacy format
            user_mandatory_exchanges_per_meal=user_mandatory_exchanges_per_meal,  # Per-meal format
        )
        
        # Calculate per-meal targets from daily totals × energy_weight
        per_meal_targets = {}
        daily_calories = target_context.calories_target or 0
        macros = target_context.macros or {}
        
        def get_macro_g(macro_dict):
            return macro_dict.get("g") or macro_dict.get("max_g") or macro_dict.get("min_g") or 0
        
        daily_protein = get_macro_g(macros.get("proteins", {}))
        daily_carbs = get_macro_g(macros.get("carbohydrates", {}))
        daily_fat = get_macro_g(macros.get("fats", {}))
        
        for meal_name in meal_structure.meals:
            energy_weight = meal_structure.energy_weight.get(meal_name, 0)
            
            per_meal_targets[meal_name] = {
                "calories": round(daily_calories * energy_weight, 1),
                "protein_g": round(daily_protein * energy_weight, 1),
                "carbs_g": round(daily_carbs * energy_weight, 1) if daily_carbs > 0 else None,
                "fat_g": round(daily_fat * energy_weight, 1) if daily_fat > 0 else None,
            }
        
        # Create ExchangeContext with exchange data
        # The new implementation returns per_meal_allocation instead of exchanges_per_meal
        per_meal_allocation = exchange_result.get("per_meal_allocation") or exchange_result.get("exchanges_per_meal") or {}
        daily_exchange_allocation = exchange_result.get("daily_exchange_allocation")
        per_meal_nutrition = exchange_result.get("per_meal_nutrition")  # Nutrition totals per meal
        daily_nutrition = exchange_result.get("daily_nutrition")  # Daily nutrition totals
        
        # Log for debugging
        logger.info(f"Exchange engine result keys: {list(exchange_result.keys())}")
        logger.info(f"daily_exchange_allocation from engine: {daily_exchange_allocation}")
        
        exchange_context = ExchangeContext(
            assessment_id=meal_structure.assessment_id,
            exchanges_per_meal=per_meal_allocation,  # Use per_meal_allocation for backward compatibility
            per_meal_targets=per_meal_targets,
            notes=exchange_result.get("notes"),  # Extract notes from engine result
            daily_exchange_allocation=daily_exchange_allocation,  # Extract daily allocation
            user_mandatory_applied=exchange_result.get("user_mandatory_applied"),  # Extract user mandatory info
            exchange_distribution_table=daily_exchange_allocation,  # Keep for backward compatibility
        )
        
        # Attach nutrition data as attributes (not part of ExchangeContext dataclass yet, but accessible)
        exchange_context.per_meal_nutrition = per_meal_nutrition
        exchange_context.daily_nutrition = daily_nutrition
        
        # Store exchange allocation in database
        existing = self.exchange_repo.get_by_assessment_id(meal_structure.assessment_id)
        allocation_data = {
            "assessment_id": meal_structure.assessment_id,
            "exchanges_per_meal": per_meal_allocation,  # Store per_meal_allocation as exchanges_per_meal for backward compatibility
            "daily_exchange_allocation": daily_exchange_allocation,  # Store daily exchange totals
            "notes": exchange_result.get("notes"),  # Store notes from engine
        }
        
        if existing:
            self.exchange_repo.update_by_assessment_id(meal_structure.assessment_id, allocation_data)
        else:
            self.exchange_repo.create(allocation_data)
        
        return exchange_context

    def execute_ayurveda_stage(self, target_context: TargetContext, mnt_context: MNTContext) -> AyurvedaContext:
        if not self.enable_ayurveda:
            return AyurvedaContext(assessment_id=target_context.assessment_id)

        client_context = self._assessment_snapshot.get("client_context", {}) if self._assessment_snapshot else {}
        anthropometry = self._assessment_snapshot.get("clinical_data", {}).get("anthropometry", {}) if self._assessment_snapshot else {}
        # Extract ayurveda_data - it may contain ayurveda_assessment in the new format
        ayurveda_data = self._assessment_snapshot.get("ayurveda_data", {}) if self._assessment_snapshot else {}
        # Build intake_data with ayurveda_assessment if available
        intake_data = {}
        if ayurveda_data.get("ayurveda_assessment"):
            intake_data["ayurveda_assessment"] = ayurveda_data["ayurveda_assessment"]
        elif self._assessment_snapshot.get("intake_data"):
            intake_data = self._assessment_snapshot.get("intake_data", {})
        
        client_profile = {
            "age": client_context.get("age"),
            "gender": client_context.get("gender"),
            "height_cm": client_context.get("height_cm") or anthropometry.get("height_cm"),
            "weight_kg": client_context.get("weight_kg") or anthropometry.get("weight_kg"),
            "activity_level": client_context.get("activity_level"),
            "intake_data": intake_data,
        }

        ayu_context = self.ayurveda_engine.process_ayurveda_assessment(
            client_profile=client_profile,
            mnt_context=mnt_context,
            target_context=target_context
        )

        existing = self.ayurveda_repo.get_by_assessment_id(target_context.assessment_id)
        payload = {
            "assessment_id": target_context.assessment_id,
            "dosha_primary": ayu_context.dosha_primary,
            "dosha_secondary": ayu_context.dosha_secondary,
            "vikriti_notes": ayu_context.vikriti_notes,
            "lifestyle_guidelines": ayu_context.lifestyle_guidelines,
        }
        if existing:
            self.ayurveda_repo.update(existing.id, payload)
        else:
            self.ayurveda_repo.create(payload)

        return ayu_context

    def execute_intervention_stage(
        self,
        mnt_context: MNTContext,
        target_context: TargetContext,
        exchange_context: ExchangeContext,
        ayurveda_context: AyurvedaContext,
        diagnosis_context: Optional[DiagnosisContext] = None,
        client_preferences: Optional[Dict[str, Any]] = None
    ) -> InterventionContext:
        intervention = self.food_engine.generate_meal_plan(
            mnt_context=mnt_context,
            target_context=target_context,
            exchange_context=exchange_context,
            ayurveda_context=ayurveda_context,
            diagnosis_context=diagnosis_context,
            client_preferences=client_preferences,
            db=self.db
        )

        # Persist plan with version increment
        existing = self.plan_repo.get_by_assessment_id(mnt_context.assessment_id)
        version = 1
        if existing:
            version = max([p.plan_version or 1 for p in existing]) + 1

        plan_record = self.plan_repo.create({
            "client_id": self.client_id,
            "assessment_id": mnt_context.assessment_id,
            "plan_version": version,
            "status": "active",
            "meal_plan": intervention.meal_plan,
            "explanations": intervention.explanations,
            "constraints_snapshot": intervention.constraints_snapshot,
        })

        # Update context with plan info
        if intervention.explanations is None:
            intervention.explanations = {}
        intervention.explanations["plan_created_at"] = str(plan_record.created_at)
        intervention.plan_id = plan_record.id
        intervention.plan_version = plan_record.plan_version
        intervention.client_id = self.client_id
        intervention.assessment_id = mnt_context.assessment_id
        return intervention

    def execute_recipe_stage(
        self,
        intervention_context: InterventionContext,
        exchange_context: ExchangeContext,
        meal_structure_context: MealStructureContext,
        mnt_context: MNTContext,
        ayurveda_context: AyurvedaContext,
        client_preferences: Optional[Dict[str, Any]] = None
    ) -> RecipeContext:
        """
        Execute recipe generation stage (Step 10).
        
        Two-phase process:
        1. Phase 1 (MealAllocationEngine): Allocate foods to meals based on exchange targets
        2. Phase 2 (RecipeGenerationEngine): Generate recipes and cooking instructions using LLM
        
        Uses FoodEngine output (category_wise_foods) and exchange allocations to create
        finalized meals with recipes.
        """
        # Get meal plan from intervention context (FoodEngine output)
        # FoodEngine output contains: category_wise_foods (ranked food lists per exchange category)
        food_engine_output = intervention_context.meal_plan or {}
        
        # Phase 1: Allocate foods to meals (deterministic)
        # This creates meal plans with allocated foods and quantities
        logger.info("Phase 1: Allocating foods to meals...")
        meal_allocation_result = self.meal_allocation_engine.allocate_meal_plan(
            exchange_context=exchange_context,
            meal_structure=meal_structure_context,
            food_engine_output=food_engine_output,
            num_days=7,
            start_date=None  # Will default to today
        )
        
        # Phase 2: Generate recipes from allocated meals (LLM-based)
        # This adds recipe names, cooking steps, and serving instructions
        logger.info("Phase 2: Generating recipes with LLM...")
        final_result = self.recipe_generation_engine.generate_recipes_for_meal_plan(
            meal_plan=meal_allocation_result,
            mnt_context=mnt_context,
            ayurveda_context=ayurveda_context,
            num_days=7
        )
        
        # Merge variety_metrics from Phase 1 into final result if not present
        if "variety_metrics" not in final_result and "variety_metrics" in meal_allocation_result:
            final_result["variety_metrics"] = meal_allocation_result["variety_metrics"]
        
        # Merge nutrition_summary from Phase 1 if not present
        if "nutrition_summary" not in final_result and "nutrition_summary" in meal_allocation_result:
            final_result["nutrition_summary"] = meal_allocation_result["nutrition_summary"]
        
        # Create RecipeContext with final result (includes recipes)
        recipe_context = RecipeContext(
            assessment_id=intervention_context.assessment_id,
            client_id=intervention_context.client_id,
            plan_id=intervention_context.plan_id,
            plan_version=intervention_context.plan_version,
            meals_with_recipes=final_result,  # Full 7-day plan with recipes
            total_daily_nutrition=final_result.get("nutrition_summary", {}).get("average_daily") or final_result.get("summary", {}).get("average_daily"),
            meal_plan_structure=food_engine_output,  # Keep original FoodEngine structure
        )
        
        # Update the plan record with final recipe data
        if intervention_context.plan_id:
            plan_record = self.plan_repo.get_by_id(intervention_context.plan_id)
            if plan_record:
                # Update meal_plan to include final result with recipes
                updated_meal_plan = {
                    **food_engine_output,
                    "seven_day_plan": final_result,
                }
                
                update_data = {
                    "meal_plan": updated_meal_plan,
                }
                
                # Add recipe generation info to explanations
                if plan_record.explanations:
                    explanations = plan_record.explanations.copy()
                else:
                    explanations = {}
                
                summary = final_result.get("summary", {})
                explanations["recipe_generation"] = {
                    "recipes_generated": True,
                    "plan_duration_days": 7,
                    "start_date": final_result.get("start_date"),
                    "total_meals": summary.get("total_meals", 0),
                    "successful_recipes": summary.get("successful_recipes", 0),
                    "failed_recipes": summary.get("failed_recipes", 0),
                    "validation_failures": summary.get("validation_failures", 0),
                }
                
                update_data["explanations"] = explanations
                self.plan_repo.update(plan_record.id, update_data)
        
        return recipe_context

    # --- Pipeline ---------------------------------------------------------------
    def execute_full_pipeline(
        self,
        assessment_id: UUID,
        client_preferences: Optional[Dict[str, Any]] = None,
        enable_ayurveda: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Execute full pipeline from assessment through plan generation.
        """
        if enable_ayurveda is not None:
            self.enable_ayurveda = enable_ayurveda

        assessment_context = self.execute_assessment_stage(assessment_id)
        diagnosis_context = self.execute_diagnosis_stage(assessment_context)
        mnt_context = self.execute_mnt_stage(diagnosis_context)
        target_context = self.execute_target_stage(mnt_context, diagnosis_context)
        meal_structure_context = self.execute_meal_structure_stage(target_context, client_preferences)
        ayu_context = self.execute_ayurveda_stage(target_context, mnt_context)
        exchange_context = self.execute_exchange_stage(
            meal_structure_context, 
            target_context, 
            mnt_context, 
            ayu_context,
            client_preferences  # Pass client_preferences for user-mandated exchanges
        )
        intervention_context = self.execute_intervention_stage(
            mnt_context, target_context, exchange_context, ayu_context, diagnosis_context, client_preferences
        )
        recipe_context = self.execute_recipe_stage(
            intervention_context, exchange_context, meal_structure_context, mnt_context, ayu_context, client_preferences
        )

        self.state_machine.transition_to(ClientState.PLAN_GENERATED)

        return {
            "assessment": assessment_context,
            "diagnosis": diagnosis_context,
            "mnt": mnt_context,
            "target": target_context,
            "meal_structure": meal_structure_context,
            "exchange": exchange_context,
            "ayurveda": ayu_context,
            "intervention": intervention_context,
            "recipe": recipe_context,
        }

