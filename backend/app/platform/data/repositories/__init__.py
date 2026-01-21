"""
Platform data repositories.
All repository classes for the platform data layer.
"""

from .platform_client_repository import PlatformClientRepository
from .platform_user_repository import PlatformUserRepository
from .platform_intake_repository import PlatformIntakeRepository
from .platform_assessment_repository import PlatformAssessmentRepository
from .platform_diagnosis_repository import PlatformDiagnosisRepository
from .platform_mnt_constraint_repository import PlatformMNTConstraintRepository
from .platform_nutrition_target_repository import PlatformNutritionTargetRepository
from .platform_meal_structure_repository import PlatformMealStructureRepository
from .platform_exchange_allocation_repository import PlatformExchangeAllocationRepository
from .platform_ayurveda_profile_repository import PlatformAyurvedaProfileRepository
from .platform_diet_plan_repository import PlatformDietPlanRepository
from .platform_monitoring_record_repository import PlatformMonitoringRecordRepository
from .platform_decision_log_repository import PlatformDecisionLogRepository
from .kb_medical_condition_repository import KBMedicalConditionRepository
from .kb_nutrition_diagnosis_repository import KBNutritionDiagnosisRepository
from .kb_mnt_rule_repository import KBMNTRuleRepository
from .kb_ayurveda_profile_repository import KBAyurvedaProfileRepository
from .kb_food_repository import KBFoodRepository
from .kb_lab_threshold_repository import KBLabThresholdRepository
from .kb_medical_modifier_rule_repository import KBMedicalModifierRuleRepository
from .kb_food_condition_compatibility_repository import KBFoodConditionCompatibilityRepository

__all__ = [
    "PlatformClientRepository",
    "PlatformUserRepository",
    "PlatformIntakeRepository",
    "PlatformAssessmentRepository",
    "PlatformDiagnosisRepository",
    "PlatformMNTConstraintRepository",
    "PlatformNutritionTargetRepository",
    "PlatformMealStructureRepository",
    "PlatformExchangeAllocationRepository",
    "PlatformAyurvedaProfileRepository",
    "PlatformDietPlanRepository",
    "PlatformMonitoringRecordRepository",
    "PlatformDecisionLogRepository",
    "KBMedicalConditionRepository",
    "KBNutritionDiagnosisRepository",
    "KBMNTRuleRepository",
    "KBAyurvedaProfileRepository",
    "KBFoodRepository",
    "KBLabThresholdRepository",
    "KBMedicalModifierRuleRepository",
    "KBFoodConditionCompatibilityRepository",
]
