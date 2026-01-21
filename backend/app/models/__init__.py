"""
Legacy models compatibility layer.
Re-exports models from app.legacy.models for backward compatibility.
"""
# Re-export all models from legacy.models to maintain backward compatibility
from app.legacy.models import (
    User, Client, Appointment, NutritionKnowledge, HealthProfile, FoodItem,
    DietPlan, DietPlanMeal, DoshaQuiz, GutHealthQuiz, FoodDoshaEffect,
    FoodDiseaseRelation, FoodAllergen, FoodGoalScore, AgentChatHistory, AgentChatSession,
    DietPlanStepCache,
    # Enriched Food Models
    EnrichedFoodItem, EnrichedFoodNutrition, EnrichedFoodMicronutrient,
    EnrichedFoodAyurveda, EnrichedFoodGutImpact, EnrichedFoodDiseaseSuitability,
    EnrichedFoodAllergyProfile, EnrichedFoodInteraction, EnrichedFoodGoalSuitability,
    EnrichedFoodContraindication, EnrichedFoodDescription
)

__all__ = [
    "User", "Client", "Appointment", "NutritionKnowledge", "HealthProfile", 
    "FoodItem", "DoshaQuiz", "GutHealthQuiz", "DietPlan", "DietPlanMeal",
    "FoodDoshaEffect", "FoodDiseaseRelation", "FoodAllergen", "FoodGoalScore",
    "AgentChatHistory", "AgentChatSession", "DietPlanStepCache",
    # Enriched Food Models
    "EnrichedFoodItem", "EnrichedFoodNutrition", "EnrichedFoodMicronutrient",
    "EnrichedFoodAyurveda", "EnrichedFoodGutImpact", "EnrichedFoodDiseaseSuitability",
    "EnrichedFoodAllergyProfile", "EnrichedFoodInteraction", "EnrichedFoodGoalSuitability",
    "EnrichedFoodContraindication", "EnrichedFoodDescription"
]

