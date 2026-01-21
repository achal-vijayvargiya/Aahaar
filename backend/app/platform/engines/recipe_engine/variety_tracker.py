"""
Variety Tracker for Meal Allocation Engine (Phase 1).

Enforces two mandatory variety rules:
- Rule A: Same-Day Variety - No food item may repeat across meals on the same day
- Rule B: Cross-Day Combination Variety - Exact meal food combinations must not repeat on consecutive days
"""
from typing import Dict, List, Set, Tuple


class VarietyTracker:
    """
    Tracks food usage to enforce variety rules.
    
    Rule A - Same-Day Variety:
    - No food item may repeat across meals on the same day
    - Example: If wheat is used at breakfast, it cannot be used at lunch or dinner on the same day.
    
    Rule B - Cross-Day Combination Variety:
    - Exact meal food combinations must not repeat on consecutive days
    - Example: Monday lunch: Wheat + Chana + Spinach → Tuesday lunch must be different
    - A "meal combination" is defined as the set of food items used in that meal, regardless of quantity.
    """
    
    def __init__(self):
        """
        Initialize Variety Tracker.
        """
        # Track foods used per day (across all meals) - for Rule A
        # {day: set(food_ids)}
        self.daily_foods: Dict[int, Set[str]] = {}
        
        # Track meal combinations per day - for Rule B
        # {meal_name: {day: frozenset(food_ids)}}
        self.meal_combinations: Dict[str, Dict[int, frozenset]] = {}
    
    def can_use_food(self, food_id: str, meal_name: str, day: int) -> Tuple[bool, str]:
        """
        Check if a food can be used in a meal on a given day.
        
        Enforces Rule A: Same-Day Variety
        
        Args:
            food_id: Food ID to check
            meal_name: Name of meal
            day: Day number (1-7)
            
        Returns:
            Tuple of (can_use: bool, reason: str)
        """
        # Rule A: Check if food was already used on this day in any meal
        if day in self.daily_foods:
            if food_id in self.daily_foods[day]:
                return False, f"Food {food_id} already used on day {day} (Rule A: Same-Day Variety)"
        
        return True, ""
    
    def can_use_meal_combination(
        self, 
        meal_name: str, 
        day: int, 
        food_ids: Set[str]
    ) -> Tuple[bool, str]:
        """
        Check if a meal combination can be used on a given day.
        
        Enforces Rule B: Cross-Day Combination Variety
        
        Args:
            meal_name: Name of meal
            day: Day number (1-7)
            food_ids: Set of food IDs in this meal combination
            
        Returns:
            Tuple of (can_use: bool, reason: str)
        """
        if not food_ids:
            return True, ""
        
        # Create combination signature (frozenset for hashability)
        combination = frozenset(food_ids)
        
        # Rule B: Check if this exact combination was used on the previous day
        if meal_name in self.meal_combinations:
            previous_day = day - 1
            if previous_day in self.meal_combinations[meal_name]:
                previous_combination = self.meal_combinations[meal_name][previous_day]
                if combination == previous_combination:
                    return False, (
                        f"Meal combination {sorted(food_ids)} already used on day {previous_day} "
                        f"for {meal_name} (Rule B: Cross-Day Combination Variety)"
                    )
        
        return True, ""
    
    def record_food_usage(self, food_id: str, meal_name: str, day: int):
        """
        Record that a food was used in a meal on a specific day.
        
        Args:
            food_id: Food ID used
            meal_name: Name of meal
            day: Day number (1-7)
        """
        # Track for Rule A: Same-Day Variety
        if day not in self.daily_foods:
            self.daily_foods[day] = set()
        self.daily_foods[day].add(food_id)
    
    def record_meal_combination(
        self, 
        meal_name: str, 
        day: int, 
        food_ids: Set[str]
    ):
        """
        Record a meal combination for a specific day.
        
        Args:
            meal_name: Name of meal
            day: Day number (1-7)
            food_ids: Set of food IDs in this meal combination
        """
        if not food_ids:
            return
        
        # Track for Rule B: Cross-Day Combination Variety
        if meal_name not in self.meal_combinations:
            self.meal_combinations[meal_name] = {}
        
        combination = frozenset(food_ids)
        self.meal_combinations[meal_name][day] = combination
    
    def get_foods_used_today(self, day: int) -> Set[str]:
        """
        Get set of foods already used on a given day.
        
        Args:
            day: Day number (1-7)
            
        Returns:
            Set of food IDs used on this day
        """
        return self.daily_foods.get(day, set())
    
    def get_previous_day_combination(
        self, 
        meal_name: str, 
        day: int
    ) -> Set[str]:
        """
        Get the meal combination used on the previous day.
        
        Args:
            meal_name: Name of meal
            day: Day number (1-7)
            
        Returns:
            Set of food IDs from previous day's combination, or empty set if none
        """
        if meal_name not in self.meal_combinations:
            return set()
        
        previous_day = day - 1
        if previous_day in self.meal_combinations[meal_name]:
            return set(self.meal_combinations[meal_name][previous_day])
        
        return set()
    
    def reset(self):
        """
        Reset all tracking data.
        """
        self.daily_foods = {}
        self.meal_combinations = {}
