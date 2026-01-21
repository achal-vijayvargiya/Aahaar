"""
Food Ranking System - Usage Examples

This file demonstrates various ways to configure and use the food ranking system.
"""

from app.platform.engines.food_engine.food_ranker import RankingTierConfig
from app.platform.engines.food_engine.food_engine import FoodEngine
from app.platform.core.context import MNTContext, TargetContext, ExchangeContext


# Example 1: Default Configuration (All Tiers Enabled)
def example_default_ranking():
    """Use default ranking with all tiers enabled."""
    engine = FoodEngine()
    
    # No ranking_config needed - uses defaults
    intervention_context = engine.generate_food_lists(
        mnt_context=mnt_context,
        target_context=target_context,
        exchange_context=exchange_context,
        ayurveda_context=ayurveda_context,
        diagnosis_context=diagnosis_context,
        client_preferences=client_preferences,
        db=db
    )
    
    # Foods are ranked and sorted
    cereal_foods = intervention_context.meal_plan["category_wise_foods"]["cereal"]
    top_food = cereal_foods[0]  # Best ranked food
    print(f"Top food: {top_food['display_name']} (Score: {top_food['ranking']['total_score']})")


# Example 2: Medical Safety Only
def example_medical_only():
    """Rank only by medical safety."""
    ranking_config = RankingTierConfig(
        enable_medical_safety=True,
        medical_safety_weight=1.0,  # 100% weight
        
        enable_nutrition_alignment=False,
        enable_ayurveda_alignment=False,
        enable_variety=False,
        enable_preferences=False,
        enable_practical=False,
    )
    
    engine = FoodEngine()
    intervention_context = engine.generate_food_lists(
        mnt_context=mnt_context,
        target_context=target_context,
        exchange_context=exchange_context,
        ayurveda_context=ayurveda_context,
        diagnosis_context=diagnosis_context,
        client_preferences=client_preferences,
        db=db,
        ranking_config=ranking_config
    )


# Example 3: Custom Weight Distribution
def example_custom_weights():
    """Custom weight distribution prioritizing nutrition."""
    ranking_config = RankingTierConfig(
        enable_medical_safety=True,
        medical_safety_weight=0.30,  # 30%
        
        enable_nutrition_alignment=True,
        nutrition_alignment_weight=0.50,  # 50% (higher priority)
        
        enable_ayurveda_alignment=True,
        ayurveda_alignment_weight=0.15,  # 15%
        
        enable_variety=True,
        variety_weight=0.05,  # 5%
        
        enable_preferences=False,  # Disabled
        enable_practical=False,   # Disabled
    )
    
    engine = FoodEngine()
    intervention_context = engine.generate_food_lists(
        mnt_context=mnt_context,
        target_context=target_context,
        exchange_context=exchange_context,
        ayurveda_context=ayurveda_context,
        diagnosis_context=diagnosis_context,
        client_preferences=client_preferences,
        db=db,
        ranking_config=ranking_config
    )


# Example 4: With Rotation History (Variety)
def example_with_variety():
    """Rank with variety tracking to avoid repetition."""
    ranking_config = RankingTierConfig(
        enable_medical_safety=True,
        enable_nutrition_alignment=True,
        enable_ayurveda_alignment=True,
        enable_variety=True,  # Enable variety tier
        enable_preferences=True,
        enable_practical=True,
    )
    
    # Track recently used foods
    rotation_history = [
        "A001",  # Used in last meal
        "B005",  # Used 2 meals ago
        "C012",  # Used 3 meals ago
    ]
    
    engine = FoodEngine()
    intervention_context = engine.generate_food_lists(
        mnt_context=mnt_context,
        target_context=target_context,
        exchange_context=exchange_context,
        ayurveda_context=ayurveda_context,
        diagnosis_context=diagnosis_context,
        client_preferences=client_preferences,
        db=db,
        ranking_config=ranking_config,
        rotation_history=rotation_history  # Pass rotation history
    )


# Example 5: Disable All Ranking
def example_no_ranking():
    """Disable ranking completely - just use basic filtering."""
    ranking_config = RankingTierConfig(
        enable_medical_safety=False,
        enable_nutrition_alignment=False,
        enable_ayurveda_alignment=False,
        enable_variety=False,
        enable_preferences=False,
        enable_practical=False,
    )
    
    engine = FoodEngine()
    intervention_context = engine.generate_food_lists(
        mnt_context=mnt_context,
        target_context=target_context,
        exchange_context=exchange_context,
        ayurveda_context=ayurveda_context,
        diagnosis_context=diagnosis_context,
        client_preferences=client_preferences,
        db=db,
        ranking_config=ranking_config  # All tiers disabled
    )
    
    # Or pass None to use basic sorting only
    intervention_context = engine.generate_food_lists(
        mnt_context=mnt_context,
        target_context=target_context,
        exchange_context=exchange_context,
        ayurveda_context=ayurveda_context,
        diagnosis_context=diagnosis_context,
        client_preferences=client_preferences,
        db=db,
        ranking_config=None  # No ranking
    )


# Example 6: Access Ranking Information
def example_access_ranking():
    """Access and use ranking information."""
    engine = FoodEngine()
    intervention_context = engine.generate_food_lists(
        mnt_context=mnt_context,
        target_context=target_context,
        exchange_context=exchange_context,
        ayurveda_context=ayurveda_context,
        diagnosis_context=diagnosis_context,
        client_preferences=client_preferences,
        db=db
    )
    
    # Get ranked foods
    cereal_foods = intervention_context.meal_plan["category_wise_foods"]["cereal"]
    
    for food in cereal_foods[:5]:  # Top 5 foods
        ranking = food.get("ranking", {})
        print(f"\nFood: {food['display_name']}")
        print(f"  Rank: {ranking.get('rank')}")
        print(f"  Total Score: {ranking.get('total_score')}")
        print(f"  Tier Scores: {ranking.get('tier_scores')}")
        print(f"  Factors: {ranking.get('ranking_factors')}")


# Example 7: Dynamic Configuration Based on User Profile
def example_dynamic_config(user_profile: dict):
    """Configure ranking based on user profile."""
    # Determine which tiers to enable based on user profile
    has_medical_conditions = bool(user_profile.get("medical_conditions"))
    has_ayurveda = bool(user_profile.get("ayurveda_profile"))
    has_preferences = bool(user_profile.get("food_preferences"))
    
    ranking_config = RankingTierConfig(
        enable_medical_safety=has_medical_conditions,
        enable_nutrition_alignment=True,  # Always enable
        enable_ayurveda_alignment=has_ayurveda,
        enable_variety=True,  # Always enable for variety
        enable_preferences=has_preferences,
        enable_practical=True,  # Always enable
    )
    
    # Adjust weights based on priorities
    if user_profile.get("priority") == "medical":
        ranking_config.medical_safety_weight = 0.60
        ranking_config.nutrition_alignment_weight = 0.25
    elif user_profile.get("priority") == "nutrition":
        ranking_config.medical_safety_weight = 0.30
        ranking_config.nutrition_alignment_weight = 0.50
    
    engine = FoodEngine()
    intervention_context = engine.generate_food_lists(
        mnt_context=mnt_context,
        target_context=target_context,
        exchange_context=exchange_context,
        ayurveda_context=ayurveda_context,
        diagnosis_context=diagnosis_context,
        client_preferences=client_preferences,
        db=db,
        ranking_config=ranking_config
    )
    
    return intervention_context
