"""
Recipe Engine Package.

Phase 1: Meal Allocation Engine - Deterministic meal allocation based on exchange allocations
and ranked food lists. Does NOT generate recipes or use LLM.

Phase 2: Recipe Generation Engine - Generates Indian-style recipes and cooking instructions
using LLM via OpenRouter. Takes finalized meals and produces client-ready recipes.
"""
from app.platform.engines.recipe_engine.meal_allocation_engine import MealAllocationEngine
from app.platform.engines.recipe_engine.variety_tracker import VarietyTracker
from app.platform.engines.recipe_engine.meal_allocator import MealAllocator
from app.platform.engines.recipe_engine.recipe_generation_engine import RecipeGenerationEngine

__all__ = [
    "MealAllocationEngine",
    "VarietyTracker",
    "MealAllocator",
    "RecipeGenerationEngine"
]
