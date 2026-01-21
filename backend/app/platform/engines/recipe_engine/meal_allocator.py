"""
Meal Allocator - Phase 1.

Selects foods for each meal based on:
- Per-meal exchange targets
- Ranked food lists per exchange category
- Variety constraints (same-day and cross-day)
"""
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict


class MealAllocator:
    """
    Allocates foods to meals based on exchange targets and ranked food lists.
    
    This is a deterministic food selection engine that:
    1. Selects foods from ranked lists per exchange category
    2. Enforces variety rules (same-day and cross-day)
    3. Allocates quantities based on exchange requirements
    
    Does NOT generate recipes or use LLM.
    """
    
    def __init__(self, variety_tracker: Optional[Any] = None):
        """
        Initialize Meal Allocator.
        
        Args:
            variety_tracker: Optional VarietyTracker instance for enforcing variety rules
        """
        self.variety_tracker = variety_tracker
    
    def allocate_foods_to_meal(
        self,
        meal_name: str,
        exchange_targets: Dict[str, float],
        ranked_foods: Dict[str, List[Dict[str, Any]]],
        day: int,
        foods_used_today: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        Allocate foods to a single meal based on exchange targets.
        
        Args:
            meal_name: Name of meal (e.g., "breakfast", "lunch")
            exchange_targets: Dictionary of exchange_category -> exchange_count
                            Example: {"cereal": 2, "pulse": 1, "milk": 1}
            ranked_foods: Dictionary of exchange_category -> list of ranked food dicts
                         Foods should be pre-ranked (best first)
            day: Day number (1-7) for variety tracking
            foods_used_today: Optional set of food IDs already used today (for Rule A)
            
        Returns:
            Dictionary with allocated foods:
            {
                "meal_name": "breakfast",
                "allocated_foods": [
                    {
                        "food_id": "wheat_flour",
                        "display_name": "Wheat flour, whole",
                        "exchange_category": "cereal",
                        "exchanges": 2.0,
                        "quantity_g": 60.0,
                        "nutrition": {...}
                    },
                    ...
                ],
                "total_nutrition": {...},
                "validation": {
                    "is_valid": True,
                    "warnings": []
                }
            }
        """
        allocated_foods = []
        foods_used_in_meal: Set[str] = set()
        warnings = []
        
        # Get foods already used today (for Rule A: Same-Day Variety)
        if foods_used_today is None:
            foods_used_today = set()
            if self.variety_tracker:
                foods_used_today = self.variety_tracker.get_foods_used_today(day)
        
        # Iterate through required exchange categories
        for exchange_category, exchange_count in exchange_targets.items():
            if exchange_count <= 0:
                continue
            
            # Get ranked food list for this category
            category_foods = ranked_foods.get(exchange_category, [])
            
            if not category_foods:
                warnings.append(
                    f"No foods available for exchange category '{exchange_category}' "
                    f"(required: {exchange_count} exchanges)"
                )
                continue
            
            # Select food(s) from ranked list
            selected_food = self._select_food(
                category_foods=category_foods,
                exchange_category=exchange_category,
                exchange_count=exchange_count,
                foods_used_today=foods_used_today,
                foods_used_in_meal=foods_used_in_meal,
                meal_name=meal_name,
                day=day
            )
            
            if not selected_food:
                warnings.append(
                    f"Could not select food for '{exchange_category}' "
                    f"(required: {exchange_count} exchanges) - no available foods after variety filtering"
                )
                continue
            
            # Calculate quantity based on exchange requirement
            serving_size_per_exchange = selected_food.get(
                "serving_size_per_exchange_g", 0
            ) or 0.0
            
            if serving_size_per_exchange == 0:
                # Fallback: use common serving size if available
                serving_size_per_exchange = selected_food.get(
                    "common_serving_size_g", 100.0
                ) or 100.0
                warnings.append(
                    f"Food '{selected_food.get('food_id')}' missing serving_size_per_exchange_g, "
                    f"using fallback: {serving_size_per_exchange}g"
                )
            
            quantity_g = serving_size_per_exchange * exchange_count
            
            # Calculate nutrition for allocated quantity
            nutrition_per_100g = selected_food.get("nutrition", {})
            portion_nutrition = self._calculate_portion_nutrition(
                nutrition_per_100g=nutrition_per_100g,
                quantity_g=quantity_g
            )
            
            # Create allocated food entry
            allocated_food = {
                "food_id": selected_food["food_id"],
                "display_name": selected_food.get("display_name", selected_food["food_id"]),
                "exchange_category": exchange_category,
                "exchanges": exchange_count,
                "quantity_g": round(quantity_g, 1),
                "nutrition": portion_nutrition,
                "ranking": selected_food.get("ranking", {}),  # Preserve ranking metadata
            }
            
            allocated_foods.append(allocated_food)
            
            # Track food usage for variety
            food_id = selected_food["food_id"]
            foods_used_in_meal.add(food_id)
            foods_used_today.add(food_id)
            
            if self.variety_tracker:
                self.variety_tracker.record_food_usage(
                    food_id=food_id,
                    meal_name=meal_name,
                    day=day
                )
        
        # Check Rule B: Cross-Day Combination Variety
        if self.variety_tracker:
            can_use, reason = self.variety_tracker.can_use_meal_combination(
                meal_name=meal_name,
                day=day,
                food_ids=foods_used_in_meal
            )
            
            if not can_use:
                # Try to find alternative combination
                # This is a fallback - ideally we should prevent this during selection
                warnings.append(f"Variety constraint: {reason}")
                # Note: In a more sophisticated implementation, we could backtrack
                # and try different food selections to avoid this violation
        
        # Record meal combination for Rule B tracking
        if self.variety_tracker:
            self.variety_tracker.record_meal_combination(
                meal_name=meal_name,
                day=day,
                food_ids=foods_used_in_meal
            )
        
        # Calculate total nutrition
        total_nutrition = self._calculate_total_nutrition(allocated_foods)
        
        # Validation
        is_valid = len(allocated_foods) > 0 and len(warnings) == 0
        
        return {
            "meal_name": meal_name,
            "allocated_foods": allocated_foods,
            "total_nutrition": total_nutrition,
            "exchanges_used": exchange_targets,
            "validation": {
                "is_valid": is_valid,
                "warnings": warnings
            }
        }
    
    def _select_food(
        self,
        category_foods: List[Dict[str, Any]],
        exchange_category: str,
        exchange_count: float,
        foods_used_today: Set[str],
        foods_used_in_meal: Set[str],
        meal_name: str,
        day: int
    ) -> Optional[Dict[str, Any]]:
        """
        Select a food from ranked list, respecting variety constraints.
        
        Args:
            category_foods: List of ranked food dictionaries (best first)
            exchange_category: Exchange category name
            exchange_count: Required exchange count
            foods_used_today: Set of food IDs already used today (Rule A)
            foods_used_in_meal: Set of food IDs already used in this meal
            meal_name: Name of meal
            day: Day number
            
        Returns:
            Selected food dictionary, or None if no suitable food found
        """
        # Iterate through ranked foods (best first)
        for food in category_foods:
            food_id = food.get("food_id")
            if not food_id:
                continue
            
            # Rule A: Check if food was already used today
            if food_id in foods_used_today:
                continue
            
            # Check variety tracker if available
            if self.variety_tracker:
                can_use, reason = self.variety_tracker.can_use_food(
                    food_id=food_id,
                    meal_name=meal_name,
                    day=day
                )
                if not can_use:
                    continue
            
            # Food is available and passes variety checks
            return food
        
        # No suitable food found
        return None
    
    def _calculate_portion_nutrition(
        self,
        nutrition_per_100g: Dict[str, Any],
        quantity_g: float
    ) -> Dict[str, float]:
        """
        Calculate nutrition for a given portion size.
        
        Args:
            nutrition_per_100g: Nutrition data per 100g
            quantity_g: Portion size in grams
            
        Returns:
            Dictionary with nutrition values for the portion
        """
        # Extract macros and micros
        macros = nutrition_per_100g.get("macros", {}) or {}
        micros = nutrition_per_100g.get("micros", {}) or {}
        
        # Calculate portion nutrition
        portion_nutrition = {
            "calories": ((nutrition_per_100g.get("calories", 0) or 0.0) / 100.0) * quantity_g,
            "protein_g": ((macros.get("protein_g", 0) or 0.0) / 100.0) * quantity_g,
            "carbs_g": ((macros.get("carbs_g", 0) or 0.0) / 100.0) * quantity_g,
            "fat_g": ((macros.get("fat_g", 0) or 0.0) / 100.0) * quantity_g,
            "fiber_g": ((macros.get("fiber_g", 0) or 0.0) / 100.0) * quantity_g,
        }
        
        # Add micros if available
        if micros:
            for micro_name, micro_value in micros.items():
                if isinstance(micro_value, (int, float)):
                    portion_nutrition[f"{micro_name}_mg"] = (micro_value / 100.0) * quantity_g
        
        # Round values
        return {k: round(v, 1) for k, v in portion_nutrition.items()}
    
    def _calculate_total_nutrition(
        self,
        allocated_foods: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Calculate total nutrition across all allocated foods in a meal.
        
        Args:
            allocated_foods: List of allocated food dictionaries
            
        Returns:
            Dictionary with total nutrition values
        """
        total = defaultdict(float)
        
        for food in allocated_foods:
            nutrition = food.get("nutrition", {})
            for key, value in nutrition.items():
                if isinstance(value, (int, float)):
                    total[key] += value
        
        return {k: round(v, 1) for k, v in total.items()}
