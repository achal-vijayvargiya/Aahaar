"""
Meal Allocation Engine - Phase 1.

Deterministic engine for allocating foods to meals based on:
- Exchange allocation outputs (per-meal exchange targets)
- Food ranking outputs (ranked food lists per exchange category)
- Variety constraints (same-day and cross-day)

This engine does NOT generate recipes or use LLM.
It only selects foods and allocates quantities.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from app.platform.core.context import (
    ExchangeContext,
    MealStructureContext,
    InterventionContext,
)
from app.platform.engines.recipe_engine.variety_tracker import VarietyTracker
from app.platform.engines.recipe_engine.meal_allocator import MealAllocator


class MealAllocationEngine:
    """
    Phase 1 Meal Allocation Engine.
    
    Responsibility:
    - Allocate foods to each meal based on exchange targets
    - Use ranked food lists from Food Engine
    - Enforce variety rules (same-day and cross-day)
    - Generate deterministic meal plans
    
    Does NOT:
    - Generate recipes
    - Use LLM
    - Create cooking instructions
    - Combine foods into dishes
    
    Inputs:
    - Meal Structure Output: List of meals per day
    - Exchange Allocation Output: Per-meal exchange targets
    - Food Engine Output: Ranked list of foods per exchange category
    
    Outputs:
    - Meal plan with allocated foods per meal
    - Nutrition totals per meal
    - Variety tracking information
    """
    
    def __init__(self):
        """Initialize Meal Allocation Engine."""
        self.variety_tracker = VarietyTracker()
        self.meal_allocator = MealAllocator(variety_tracker=self.variety_tracker)
    
    def allocate_meal_plan(
        self,
        exchange_context: ExchangeContext,
        meal_structure: MealStructureContext,
        food_engine_output: Dict[str, Any],
        num_days: int = 7,
        start_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Allocate foods to meals for multiple days.
        
        Args:
            exchange_context: Exchange context with per-meal exchange targets
            meal_structure: Meal structure context with meal list
            food_engine_output: Food Engine output with ranked food lists
            num_days: Number of days to generate (default: 7)
            start_date: Optional start date (defaults to today)
            
        Returns:
            Dictionary with meal plan:
            {
                "plan_duration_days": 7,
                "start_date": "2025-01-15",
                "days": {
                    "day_1": {
                        "day_number": 1,
                        "date": "2025-01-15",
                        "day_name": "Monday",
                        "meals": {
                            "breakfast": {
                                "meal_name": "breakfast",
                                "allocated_foods": [...],
                                "total_nutrition": {...},
                                "exchanges_used": {...},
                                "validation": {...}
                            },
                            ...
                        },
                        "daily_totals": {...}
                    },
                    ...
                },
                "variety_metrics": {...},
                "nutrition_summary": {...}
            }
        """
        if start_date is None:
            start_date = datetime.now()
        
        # Reset variety tracker for fresh start
        self.variety_tracker.reset()
        
        # Extract inputs
        exchanges_per_meal = exchange_context.exchanges_per_meal
        ranked_foods = food_engine_output.get("category_wise_foods", {})
        meal_names = meal_structure.meals
        
        # Generate plan for each day
        days = {}
        for day_num in range(1, num_days + 1):
            day_date = start_date + timedelta(days=day_num - 1)
            
            day_plan = self._allocate_day(
                day=day_num,
                day_date=day_date,
                meal_names=meal_names,
                exchanges_per_meal=exchanges_per_meal,
                ranked_foods=ranked_foods
            )
            
            days[f"day_{day_num}"] = day_plan
        
        # Calculate metrics
        variety_metrics = self._calculate_variety_metrics(days)
        nutrition_summary = self._calculate_nutrition_summary(days)
        
        return {
            "plan_duration_days": num_days,
            "start_date": start_date.isoformat(),
            "days": days,
            "variety_metrics": variety_metrics,
            "nutrition_summary": nutrition_summary
        }
    
    def _allocate_day(
        self,
        day: int,
        day_date: datetime,
        meal_names: List[str],
        exchanges_per_meal: Dict[str, Dict[str, float]],
        ranked_foods: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Allocate foods to all meals for a single day.
        
        Args:
            day: Day number (1-7)
            day_date: Date for this day
            meal_names: List of meal names
            exchanges_per_meal: Exchange targets per meal
            ranked_foods: Ranked food lists per exchange category
            
        Returns:
            Day plan dictionary
        """
        day_meals = {}
        daily_totals = {
            "calories": 0.0,
            "protein_g": 0.0,
            "carbs_g": 0.0,
            "fat_g": 0.0,
        }
        
        # Track foods used today (for Rule A: Same-Day Variety)
        foods_used_today = set()
        
        # Allocate foods for each meal
        for meal_name in meal_names:
            exchange_targets = exchanges_per_meal.get(meal_name, {})
            
            if not exchange_targets:
                # No exchanges for this meal - skip
                continue
            
            # Allocate foods to this meal
            meal_result = self.meal_allocator.allocate_foods_to_meal(
                meal_name=meal_name,
                exchange_targets=exchange_targets,
                ranked_foods=ranked_foods,
                day=day,
                foods_used_today=foods_used_today
            )
            
            day_meals[meal_name] = meal_result
            
            # Accumulate daily totals
            total_nutrition = meal_result.get("total_nutrition", {})
            daily_totals["calories"] += total_nutrition.get("calories", 0) or 0.0
            daily_totals["protein_g"] += total_nutrition.get("protein_g", 0) or 0.0
            daily_totals["carbs_g"] += total_nutrition.get("carbs_g", 0) or 0.0
            daily_totals["fat_g"] += total_nutrition.get("fat_g", 0) or 0.0
        
        return {
            "day_number": day,
            "date": day_date.strftime("%Y-%m-%d"),
            "day_name": day_date.strftime("%A"),
            "meals": day_meals,
            "daily_totals": {k: round(v, 1) for k, v in daily_totals.items()}
        }
    
    def _calculate_variety_metrics(
        self,
        days: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """
        Calculate variety metrics for the meal plan.
        
        Args:
            days: Dictionary of day plans
            
        Returns:
            Variety metrics dictionary
        """
        food_repetition = {}  # {meal_name: {food_id: count}}
        unique_foods_per_meal = {}  # {meal_name: set of food_ids}
        same_day_violations = []  # List of Rule A violations
        cross_day_violations = []  # List of Rule B violations
        
        for day_key, day_data in days.items():
            day_num = day_data.get("day_number", 0)
            meals = day_data.get("meals", {})
            
            # Track foods used per day (for Rule A check)
            daily_foods = set()
            
            for meal_name, meal_data in meals.items():
                if meal_name not in food_repetition:
                    food_repetition[meal_name] = {}
                    unique_foods_per_meal[meal_name] = set()
                
                allocated_foods = meal_data.get("allocated_foods", [])
                meal_food_ids = set()
                
                for food in allocated_foods:
                    food_id = food.get("food_id")
                    if food_id:
                        # Check Rule A: Same-day variety
                        if food_id in daily_foods:
                            same_day_violations.append({
                                "day": day_num,
                                "food_id": food_id,
                                "meal": meal_name,
                                "rule": "Rule A: Same-Day Variety"
                            })
                        
                        daily_foods.add(food_id)
                        meal_food_ids.add(food_id)
                        food_repetition[meal_name][food_id] = \
                            food_repetition[meal_name].get(food_id, 0) + 1
                        unique_foods_per_meal[meal_name].add(food_id)
                
                # Check Rule B: Cross-day combination variety
                if day_num > 1:
                    previous_day_key = f"day_{day_num - 1}"
                    if previous_day_key in days:
                        previous_day_meals = days[previous_day_key].get("meals", {})
                        if meal_name in previous_day_meals:
                            previous_foods = {
                                f.get("food_id")
                                for f in previous_day_meals[meal_name].get("allocated_foods", [])
                            }
                            previous_foods.discard(None)
                            
                            if meal_food_ids == previous_foods:
                                cross_day_violations.append({
                                    "day": day_num,
                                    "previous_day": day_num - 1,
                                    "meal": meal_name,
                                    "food_ids": sorted(meal_food_ids),
                                    "rule": "Rule B: Cross-Day Combination Variety"
                                })
        
        # Calculate variety score
        total_unique_foods = sum(len(foods) for foods in unique_foods_per_meal.values())
        total_meals = len(days) * len(unique_foods_per_meal) if unique_foods_per_meal else 1
        
        # Score based on unique foods vs total meal slots
        variety_score = min(1.0, total_unique_foods / (total_meals * 0.7)) if total_meals > 0 else 0.0
        
        return {
            "food_repetition": {
                meal: {food_id: count for food_id, count in foods.items()}
                for meal, foods in food_repetition.items()
            },
            "variety_score": round(variety_score, 2),
            "unique_foods_per_meal": {
                meal: len(foods) for meal, foods in unique_foods_per_meal.items()
            },
            "total_unique_foods": total_unique_foods,
            "rule_violations": {
                "same_day_variety": same_day_violations,
                "cross_day_combination": cross_day_violations
            },
            "all_rules_satisfied": len(same_day_violations) == 0 and len(cross_day_violations) == 0
        }
    
    def _calculate_nutrition_summary(
        self,
        days: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """
        Calculate nutrition summary across all days.
        
        Args:
            days: Dictionary of day plans
            
        Returns:
            Nutrition summary dictionary
        """
        daily_calories = []
        daily_protein = []
        daily_carbs = []
        daily_fat = []
        
        for day_key, day_data in days.items():
            daily_totals = day_data.get("daily_totals", {})
            daily_calories.append(daily_totals.get("calories", 0) or 0.0)
            daily_protein.append(daily_totals.get("protein_g", 0) or 0.0)
            daily_carbs.append(daily_totals.get("carbs_g", 0) or 0.0)
            daily_fat.append(daily_totals.get("fat_g", 0) or 0.0)
        
        def calculate_stats(values: List[float]) -> Dict[str, float]:
            """Calculate min, max, avg, std for a list of values."""
            if not values:
                return {"min": 0, "max": 0, "avg": 0, "std": 0}
            
            avg = sum(values) / len(values)
            variance = sum((x - avg) ** 2 for x in values) / len(values)
            std = variance ** 0.5
            
            return {
                "min": round(min(values), 1),
                "max": round(max(values), 1),
                "avg": round(avg, 1),
                "std": round(std, 1)
            }
        
        # Check if all days are valid
        all_days_valid = True
        for day_key, day_data in days.items():
            meals = day_data.get("meals", {})
            for meal_name, meal_data in meals.items():
                validation = meal_data.get("validation", {})
                if not validation.get("is_valid", False):
                    all_days_valid = False
                    break
            if not all_days_valid:
                break
        
        return {
            "average_daily": {
                "calories": round(sum(daily_calories) / len(daily_calories), 1) if daily_calories else 0,
                "protein_g": round(sum(daily_protein) / len(daily_protein), 1) if daily_protein else 0,
                "carbs_g": round(sum(daily_carbs) / len(daily_carbs), 1) if daily_carbs else 0,
                "fat_g": round(sum(daily_fat) / len(daily_fat), 1) if daily_fat else 0,
            },
            "daily_variation": {
                "calories": calculate_stats(daily_calories),
                "protein_g": calculate_stats(daily_protein),
                "carbs_g": calculate_stats(daily_carbs),
                "fat_g": calculate_stats(daily_fat),
            },
            "all_days_valid": all_days_valid
        }
