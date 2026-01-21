"""
Engine Data Contracts.

Defines explicit input/output schemas for each engine in the NCP flow.
Ensures type safety and validation at engine boundaries.
"""
from typing import Optional, Dict, Any, List
from uuid import UUID
from dataclasses import dataclass

from app.platform.core.context import (
    AssessmentContext,
    DiagnosisContext,
    MNTContext,
    TargetContext,
    MealStructureContext,
    ExchangeContext,
    AyurvedaContext,
    InterventionContext,
)


# ============================================================================
# Diagnosis Engine Contracts
# ============================================================================

@dataclass
class DiagnosisEngineInput:
    """Required input for DiagnosisEngine."""
    assessment_id: UUID
    assessment_snapshot: Optional[Dict[str, Any]]
    # Required fields from snapshot:
    # - clinical_data.labs (optional)
    # - clinical_data.anthropometry (optional)
    # - clinical_data.medical_history (optional)


@dataclass
class DiagnosisEngineOutput:
    """Output from DiagnosisEngine."""
    assessment_id: UUID
    medical_conditions: List[Dict[str, Any]]  # Each with: diagnosis_id, severity_score, evidence
    nutrition_diagnoses: List[Dict[str, Any]]  # Each with: diagnosis_id, severity_score, evidence
    
    def to_context(self) -> DiagnosisContext:
        """Convert to DiagnosisContext."""
        return DiagnosisContext(
            assessment_id=self.assessment_id,
            medical_conditions=self.medical_conditions,
            nutrition_diagnoses=self.nutrition_diagnoses
        )


# ============================================================================
# MNT Engine Contracts
# ============================================================================

@dataclass
class MNTEngineInput:
    """Required input for MNTEngine."""
    assessment_id: UUID
    medical_conditions: List[Dict[str, Any]]  # From DiagnosisEngine
    nutrition_diagnoses: List[Dict[str, Any]]  # From DiagnosisEngine


@dataclass
class MNTEngineOutput:
    """Output from MNTEngine."""
    assessment_id: UUID
    macro_constraints: Optional[Dict[str, Any]]
    micro_constraints: Optional[Dict[str, Any]]
    food_exclusions: Optional[List[str]]
    rule_ids_used: List[str]
    
    def to_context(self) -> MNTContext:
        """Convert to MNTContext."""
        return MNTContext(
            assessment_id=self.assessment_id,
            macro_constraints=self.macro_constraints,
            micro_constraints=self.micro_constraints,
            food_exclusions=self.food_exclusions,
            rule_ids_used=self.rule_ids_used
        )


# ============================================================================
# Target Engine Contracts
# ============================================================================

@dataclass
class TargetEngineInput:
    """Required input for TargetEngine."""
    assessment_id: UUID
    client_profile: Dict[str, Any]  # age, gender, height_cm, weight_kg, activity_level
    mnt_context: MNTContext  # From MNTEngine


@dataclass
class TargetEngineOutput:
    """Output from TargetEngine."""
    assessment_id: UUID
    calories_target: float
    macros: Dict[str, Any]  # {protein_g, carbs_g, fat_g, ...}
    key_micros: Optional[Dict[str, Any]]
    calculation_source: Optional[str]
    
    def to_context(self) -> TargetContext:
        """Convert to TargetContext."""
        return TargetContext(
            assessment_id=self.assessment_id,
            calories_target=self.calories_target,
            macros=self.macros,
            key_micros=self.key_micros,
            calculation_source=self.calculation_source
        )


# ============================================================================
# Meal Structure Engine Contracts
# ============================================================================

@dataclass
class MealStructureEngineInput:
    """Required input for MealStructureEngine."""
    assessment_id: UUID
    target_context: TargetContext  # From TargetEngine
    assessment_snapshot: Optional[Dict[str, Any]]  # For client context, behavioral preferences
    client_preferences: Optional[Dict[str, Any]] = None


@dataclass
class MealStructureEngineOutput:
    """Output from MealStructureEngine."""
    assessment_id: UUID
    meal_count: int
    meals: List[str]
    timing_windows: Dict[str, List[str]]
    energy_weight: Dict[str, float]  # Relative allocation weights (sum = 1.0)
    flags: List[str]
    
    def to_context(self) -> MealStructureContext:
        """Convert to MealStructureContext."""
        return MealStructureContext(
            assessment_id=self.assessment_id,
            meal_count=self.meal_count,
            meals=self.meals,
            timing_windows=self.timing_windows,
            energy_weight=self.energy_weight,
            flags=self.flags
        )


# ============================================================================
# Exchange System Engine Contracts
# ============================================================================

@dataclass
class ExchangeSystemEngineInput:
    """Required input for ExchangeSystemEngine."""
    assessment_id: UUID
    meal_structure: MealStructureContext  # From MealStructureEngine
    mnt_context: MNTContext  # From MNTEngine
    ayurveda_context: Optional[AyurvedaContext] = None  # From AyurvedaEngine


@dataclass
class ExchangeSystemEngineOutput:
    """Output from ExchangeSystemEngine."""
    assessment_id: UUID
    exchanges_per_meal: Dict[str, Dict[str, int]]  # {meal_name: {exchange_type: count}}
    notes: Optional[Dict[str, Any]]  # {medical_modifiers_applied, ayurveda_modifiers_applied}
    
    def to_context(self) -> ExchangeContext:
        """Convert to ExchangeContext."""
        return ExchangeContext(
            assessment_id=self.assessment_id,
            exchanges_per_meal=self.exchanges_per_meal,
            notes=self.notes
        )


# ============================================================================
# Ayurveda Engine Contracts
# ============================================================================

@dataclass
class AyurvedaEngineInput:
    """Required input for AyurvedaEngine."""
    assessment_id: UUID
    client_profile: Dict[str, Any]
    mnt_context: MNTContext  # From MNTEngine
    target_context: TargetContext  # From TargetEngine
    intake_data: Optional[Dict[str, Any]] = None


@dataclass
class AyurvedaEngineOutput:
    """Output from AyurvedaEngine."""
    assessment_id: UUID
    dosha_primary: Optional[str]
    dosha_secondary: Optional[str]
    vikriti_notes: Optional[Dict[str, Any]]
    lifestyle_guidelines: Optional[Dict[str, Any]]
    
    def to_context(self) -> AyurvedaContext:
        """Convert to AyurvedaContext."""
        return AyurvedaContext(
            assessment_id=self.assessment_id,
            dosha_primary=self.dosha_primary,
            dosha_secondary=self.dosha_secondary,
            vikriti_notes=self.vikriti_notes,
            lifestyle_guidelines=self.lifestyle_guidelines
        )


# ============================================================================
# Food Engine Contracts
# ============================================================================

@dataclass
class FoodEngineInput:
    """Required input for FoodEngine."""
    assessment_id: UUID
    mnt_context: MNTContext  # From MNTEngine
    target_context: TargetContext  # From TargetEngine
    exchange_context: ExchangeContext  # From ExchangeSystemEngine
    ayurveda_context: AyurvedaContext  # From AyurvedaEngine
    client_preferences: Optional[Dict[str, Any]] = None


@dataclass
class FoodEngineOutput:
    """Output from FoodEngine."""
    assessment_id: UUID
    client_id: UUID
    meal_plan: Optional[Dict[str, Any]]
    explanations: Optional[Dict[str, Any]]
    constraints_snapshot: Optional[Dict[str, Any]]
    
    def to_context(self) -> InterventionContext:
        """Convert to InterventionContext."""
        return InterventionContext(
            client_id=self.client_id,
            assessment_id=self.assessment_id,
            meal_plan=self.meal_plan,
            explanations=self.explanations,
            constraints_snapshot=self.constraints_snapshot
        )


# Export all contracts
__all__ = [
    "DiagnosisEngineInput",
    "DiagnosisEngineOutput",
    "MNTEngineInput",
    "MNTEngineOutput",
    "TargetEngineInput",
    "TargetEngineOutput",
    "MealStructureEngineInput",
    "MealStructureEngineOutput",
    "ExchangeSystemEngineInput",
    "ExchangeSystemEngineOutput",
    "AyurvedaEngineInput",
    "AyurvedaEngineOutput",
    "FoodEngineInput",
    "FoodEngineOutput",
]






