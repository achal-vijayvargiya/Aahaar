"""
Exchange System Engine.

Whole-day-first exchange allocation engine for Indian foods.
Translates daily nutrition targets into food exchange units distributed across meals.

Flow:
1. Calculate Daily Exchange Obligations (ALL GROUPS for whole day)
2. Energy-Weighted Exchange Distribution (distribute to meals using energy_weight)
3. Mandatory Presence Constraints (ensure food groups present)
4. Nutrition Validation (validate and adjust if needed)

Uses knowledge base (KB) files:
- core_food_groups_kb.json: Single source of truth for food groups and nutrition
- exchange_allocation_rules_kb.json: Allocation rules (protein-first, calorie fulfillment)
- mandatory_presence_constraints_kb.json: Constraints for food group presence
- nutrition_validation_tolerances_kb.json: Validation tolerances and adjustment rules
- exchange_limits_kb.json: Meal-specific exchange limits
"""
from typing import Dict, List, Any, Optional, Tuple

from app.platform.core.context import (
    MealStructureContext,
    MNTContext,
    AyurvedaContext,
    TargetContext,
)
from .exchange_constants import calculate_nutrition_from_exchanges
from .kb_exchange_system import (
    get_exchange_nutrition as kb_get_exchange_nutrition,
    get_exchange_amount as kb_get_exchange_amount,
    get_allocation_rule,
    get_medical_modifier_for_condition,
    get_ayurveda_modifier_for_dosha,
    get_exchange_limits_for_meal,
    get_mandatory_presence_constraints,
    get_nutrition_validation_tolerances,
    get_food_group_display_order,
    get_core_food_groups,
    get_exchange_category,

)


class ExchangeSystemEngine:
    """
    Exchange System Engine - Whole-Day-First Approach.
    
    Responsibility:
    - Calculate daily exchange obligations for all food groups
    - Distribute exchanges to meals using energy_weight
    - Apply mandatory presence constraints
    - Validate and adjust nutrition against targets
    
    Inputs:
    - Meal structure (energy_weight per meal)
    - Target context (daily nutrition totals)
    - MNT context (medical constraints)
    - Ayurveda context (optional soft constraints)
    
    Outputs:
    - Exchanges per meal
    - Per-meal nutrition targets
    - Daily exchange summary
    - Exchange distribution table
    - Nutrient distribution per meal
    """
    
    def __init__(self):
        """Initialize exchange system engine."""
        pass
    
    @staticmethod
    def get_exchange_category_recommendations(
        mnt_context: Optional[MNTContext] = None,
        medical_conditions: Optional[List[str]] = None,
        dietary_preferences: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        
        # Get core food groups
        core_config = get_core_food_groups()
        if not core_config:
            return []
        
        core_groups = core_config.get("core_food_groups", [])
        
        # Extract constraints
        food_exclusions = set(mnt_context.food_exclusions or []) if mnt_context else set()
        dietary_prefs_set = set(dietary_preferences or [])
        medical_conditions_set = set(medical_conditions or [])
        
        is_vegetarian = "vegetarian" in dietary_prefs_set or "vegan" in dietary_prefs_set
        is_vegan = "vegan" in dietary_prefs_set
        
        # Get medical modifiers
        medical_modifiers = {}
        for condition in medical_conditions_set:
            modifier = get_medical_modifier_for_condition(condition)
            if modifier:
                medical_modifiers[condition] = modifier
        
        # Get Ayurveda modifiers if available
        ayurveda_modifiers = {}
        
        # Get mandatory presence constraints
        constraints_rule = get_mandatory_presence_constraints()
        default_minimums = {}
        if constraints_rule:
            daily_constraints = constraints_rule.get("daily_constraints", {})
            for category_id, constraint in daily_constraints.items():
                # Map legacy vegetable_a to vegetable_non_starchy
                if category_id == "vegetable_a":
                    category_id = "vegetable_non_starchy"
                default_minimums[category_id] = constraint.get("min_exchanges", 0)
        
        recommendations = []
        
        for group in core_groups:
            category_id = group.get("exchange_category_id")
            if not category_id:
                continue
            
            # Check if category is excluded
            category_excluded = False
            category_lower = category_id.lower()
            exclusion_lower = [ex.lower() for ex in food_exclusions if isinstance(ex, str)]
            
            # Map category names for exclusion checking
            if category_lower in exclusion_lower or any(cat in ex for ex in exclusion_lower for cat in [category_lower, "dairy", "milk"] if category_id == "milk"):
                category_excluded = True
            
            # Check dietary preferences
            if category_id == "milk" and is_vegan:
                category_excluded = True
            if category_id == "egg_whites" and is_vegetarian:
                category_excluded = True
            
            # Get benefits and nutrients from group
            benefits = group.get("primary_benefits", {})
            if not isinstance(benefits, dict):
                benefits = {}
            
            # Determine recommendation status
            is_recommended = False
            recommendation_reason = ""
            
            # Check medical modifiers
            for condition, modifier in medical_modifiers.items():
                if modifier:
                    recommendations_list = modifier.get("recommendations", {}).get("categories", {})
                    if category_id in recommendations_list:
                        rec_info = recommendations_list[category_id]
                        if rec_info.get("is_recommended", False):
                            is_recommended = True
                            recommendation_reason = f"Recommended for {condition}"
                        elif rec_info.get("is_restricted", False):
                            category_excluded = True
                            recommendation_reason = f"Restricted for {condition}"
            
            # Check Ayurveda modifiers
            for dosha, modifier in ayurveda_modifiers.items():
                if modifier:
                    recommendations_list = modifier.get("recommendations", {}).get("categories", {})
                    if category_id in recommendations_list:
                        rec_info = recommendations_list[category_id]
                        if rec_info.get("is_recommended", False):
                            is_recommended = True
                            recommendation_reason = f"Recommended for {dosha} dosha (Ayurveda)"
            
            recommendations.append({
                "exchange_category_id": category_id,
                "display_name": group.get("display_name", category_id),
                "description": group.get("description", ""),
                "primary_benefits": benefits["primary_benefits"],
                "nutrients": benefits["nutrients"],
                "health_benefits": benefits["health_benefits"],
                "is_recommended": is_recommended,
                "recommendation_reason": recommendation_reason,
                "is_excluded": category_excluded,
                "suggested_min_daily": default_minimums.get(category_id, 0.0),
                "display_order": group.get("display_order", 999),
                "nutrition_per_exchange": group.get("nutrition_per_exchange", {})
            })
        
        # Sort by display order
        recommendations.sort(key=lambda x: x.get("display_order", 999))
        
        return recommendations
    
    def generate_exchanges(
        self,
        meal_structure: MealStructureContext,
        target_context: TargetContext,
        mnt_context: MNTContext,
        ayurveda_context: Optional[AyurvedaContext] = None,
        user_mandatory_exchanges: Optional[Dict[str, float]] = None,
        user_mandatory_exchanges_per_meal: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate exchange allocation using per-meal-first approach.
        
        Flow:
        1. Calculate per-meal nutrition targets from daily totals × energy_weight
        2. For each meal, calculate exchanges to meet meal's energy and protein targets
        3. Use mandatory exchanges per meal (if provided) to fill the meal's targets
        4. Calculate how many exchanges of each mandatory category are needed
        
        Args:
            meal_structure: Meal structure with energy_weight
            target_context: Target context with daily nutrition totals
            mnt_context: MNT context with medical constraints (not used in simplified flow)
            ayurveda_context: Optional Ayurveda context (not used in simplified flow)
            user_mandatory_exchanges: User-provided mandatory exchanges in daily format (category_id -> count)
                Legacy format - not used in per-meal approach. Kept for backward compatibility.
            user_mandatory_exchanges_per_meal: User-provided mandatory exchanges per meal (meal_name -> [category_id, ...])
                Used to fill each meal's energy and protein targets.
            
        Returns:
            Dictionary containing:
            - daily_exchange_allocation: Dict[exchange_type, count] - Total exchanges per category (sum of per-meal)
            - per_meal_allocation: Dict[meal_name, Dict[exchange_type, count]] - Exchanges per meal
        """
        # Step 1: Calculate per-meal nutrition targets from daily totals × energy_weight
        per_meal_targets = self._calculate_per_meal_targets(meal_structure, target_context)
        
        # Step 2: Calculate exchanges for each meal independently
        per_meal_allocation = {}
        
        for meal_name in meal_structure.meals:
            meal_target = per_meal_targets[meal_name]
            meal_target_calories = meal_target["calories"]
            meal_target_protein = meal_target["protein_g"]
            
            # Get mandatory exchange categories for this meal (if provided)
            mandatory_categories = []
            if user_mandatory_exchanges_per_meal and meal_name in user_mandatory_exchanges_per_meal:
                mandatory_categories = user_mandatory_exchanges_per_meal[meal_name]
            
            # Calculate exchanges for this meal to meet its targets
            meal_exchanges = self._calculate_exchanges_for_meal(
                target_calories=meal_target_calories,
                target_protein=meal_target_protein,
                mandatory_exchange_categories=mandatory_categories,
            )
            
            per_meal_allocation[meal_name] = meal_exchanges
        
        # Step 3: Calculate daily totals from per-meal allocations
        daily_exchanges = {}
        for meal_name in meal_structure.meals:
            for category_id, count in per_meal_allocation[meal_name].items():
                daily_exchanges[category_id] = daily_exchanges.get(category_id, 0) + count
        
        # Step 4: Calculate nutrition totals per meal
        per_meal_nutrition = {}
        for meal_name in meal_structure.meals:
            meal_exchanges = per_meal_allocation[meal_name]
            meal_calories = 0.0
            meal_protein = 0.0
            
            for category_id, count in meal_exchanges.items():
                nutrition = kb_get_exchange_nutrition(category_id)
                if nutrition:
                    meal_calories += count * nutrition.get("calories", 0)
                    meal_protein += count * nutrition.get("protein_g", 0)
            
            per_meal_nutrition[meal_name] = {
                "total_calories": round(meal_calories, 1),
                "total_protein_g": round(meal_protein, 1),
            }
        
        # Step 5: Calculate daily nutrition totals from daily_exchange_allocation
        daily_total_calories = 0.0
        daily_total_protein = 0.0
        
        for category_id, count in daily_exchanges.items():
            nutrition = kb_get_exchange_nutrition(category_id)
            if nutrition:
                daily_total_calories += count * nutrition.get("calories", 0)
                daily_total_protein += count * nutrition.get("protein_g", 0)
        
        daily_nutrition = {
            "total_calories": round(daily_total_calories, 1),
            "total_protein_g": round(daily_total_protein, 1),
        }
        
        # Build return response
        result = {
            "daily_exchange_allocation": daily_exchanges,
            "per_meal_allocation": per_meal_allocation,
            "per_meal_nutrition": per_meal_nutrition,  # Total energy and protein per meal
            "daily_nutrition": daily_nutrition,  # Total energy and protein from daily_exchange_allocation
        }
        
        return result
    
    def _calculate_per_meal_targets(
        self,
        meal_structure: MealStructureContext,
        target_context: TargetContext
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate per-meal nutrition targets from daily totals × energy_weight.
        
        Args:
            meal_structure: Meal structure with energy_weight
            target_context: Target context with daily totals
            
        Returns:
            Dictionary of meal names to nutrition targets
        """
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
        
        return per_meal_targets
    
    def _calculate_exchanges_for_meal(
        self,
        target_calories: float,
        target_protein: float,
        mandatory_exchange_categories: List[str],
    ) -> Dict[str, float]:
        """
        Calculate exchanges for a single meal using two-phase dietitian approach.
        
        Phase 1: Allocate protein sources first to meet protein target
        Phase 2: Allocate remaining calories using calorie-rich categories
        
        This approach mimics how a dietitian would allocate:
        1. First, ensure protein requirements are met
        2. Then, fill remaining calories
        
        Strategy:
        1. Allocate minimum exchanges (0.5) to mandatory categories first
        2. Calculate remaining protein/calories needed after mandatory allocation
        3. Use ALL available categories to fill remaining targets
        4. This respects user selections while ensuring targets are met
        
        Args:
            target_calories: Target calories for this meal
            target_protein: Target protein (grams) for this meal
            mandatory_exchange_categories: List of exchange category IDs that must be included (minimum 0.5 exchange each)
            
        Returns:
            Dictionary of category_id -> exchange count for this meal
        """
        # Use ONLY mandatory exchange categories from UI (no other categories)
        if not mandatory_exchange_categories:
            return {}
        
        category_nutrition = {}
        core_config = get_core_food_groups()
        if not core_config:
            return {}
        
        core_groups = core_config.get("core_food_groups", [])
        
        # Build a map of all categories for quick lookup
        all_categories_map = {}
        for group in core_groups:
            category_id = group.get("exchange_category_id")
            if category_id:
                nutrition = group.get("nutrition_per_exchange", {})
                if nutrition:
                    all_categories_map[category_id] = {
                        "calories": float(nutrition.get("calories", 0)),
                        "protein_g": float(nutrition.get("protein_g", 0)),
                    }
        
        # Only include mandatory categories in category_nutrition
        mandatory_category_set = set(mandatory_exchange_categories)
        for cat_id in mandatory_exchange_categories:
            if cat_id in all_categories_map:
                category_nutrition[cat_id] = all_categories_map[cat_id]
        
        if not category_nutrition:
            return {}
        
        # Initialize meal_exchanges (start with 0.5 minimum for all mandatory categories)
        meal_exchanges = {}
        for cat_id in mandatory_exchange_categories:
            if cat_id in category_nutrition:
                meal_exchanges[cat_id] = 0.5  # Start with minimum 0.5 exchange
        
        # Calculate initial nutrition from minimum exchanges
        def calculate_nutrition(exchanges: Dict[str, float]) -> Tuple[float, float]:
            calories = 0.0
            protein = 0.0
            for cat_id, count in exchanges.items():
                if cat_id in category_nutrition:
                    calories += count * category_nutrition[cat_id]["calories"]
                    protein += count * category_nutrition[cat_id]["protein_g"]
            return calories, protein
        
        # Calculate remaining targets after minimum allocation
        initial_calories, initial_protein = calculate_nutrition(meal_exchanges)
        remaining_protein_target = max(0, target_protein - initial_protein)
        remaining_calories_target = max(0, target_calories - initial_calories)
        
        
        # Separate categories into protein-rich vs calorie-rich
        # Protein-rich: ≥0.05 g protein per kcal (5g per 100 kcal)
        protein_categories = []  # (cat_id, protein_g, calories)
        calorie_categories = []  # (cat_id, calories, protein_g)
        
        # Use ONLY mandatory categories to fill remaining targets
        for cat_id in category_nutrition:
            cat_cal = category_nutrition[cat_id]["calories"]
            cat_prot = category_nutrition[cat_id]["protein_g"]
            if cat_cal > 0:
                ratio = cat_prot / cat_cal
                if ratio >= 0.05:  # At least 5g protein per 100 kcal
                    protein_categories.append((cat_id, cat_prot, cat_cal))
                else:
                    calorie_categories.append((cat_id, cat_cal, cat_prot))
        
        # Phase 1: Allocate protein sources to meet REMAINING protein target
        # Dietitian approach: fill protein first using protein-rich categories
        # Must ensure remaining protein target is FULLY met before moving to calories
        remaining_protein = remaining_protein_target
        TOLERANCE_PROTEIN = 2.0
        
        if protein_categories and remaining_protein > TOLERANCE_PROTEIN:
            # Sort by protein content (highest first) - use best protein sources first
            protein_categories.sort(key=lambda x: x[1], reverse=True)
            
            # Allocate protein sources to meet protein target
            # Strategy: distribute protein across all protein categories proportionally
            # If only one protein category, use it fully. If multiple, distribute.
            
            if len(protein_categories) == 1:
                # Single protein category - use it to meet remaining protein target
                cat_id, cat_prot, cat_cal = protein_categories[0]
                # If this category is already mandatory, add to existing exchanges, otherwise allocate new
                existing_exchanges = meal_exchanges.get(cat_id, 0)
                exchanges_needed = remaining_protein / cat_prot if cat_prot > 0 else 0
                exchanges_needed = round(exchanges_needed * 2) / 2.0
                exchanges_needed = max(0.5, exchanges_needed)
                meal_exchanges[cat_id] = existing_exchanges + exchanges_needed
                remaining_protein -= exchanges_needed * cat_prot
            else:
                # Multiple protein categories - allocate to MEET remaining protein target
                # Strategy: Use best protein sources first until target is met
                # Distribute proportionally across top 2-3 protein sources
                protein_categories.sort(key=lambda x: x[1], reverse=True)  # Sort by protein (highest first)
                
                # Use top 3 protein sources (or all if fewer)
                top_protein_sources = protein_categories[:min(3, len(protein_categories))]
                
                # Calculate total protein capacity from top sources
                total_top_protein_capacity = sum(cat_prot for _, cat_prot, _ in top_protein_sources)
                
                # Distribute remaining protein target proportionally across top sources
                for cat_id, cat_prot, cat_cal in top_protein_sources:
                    if total_top_protein_capacity > 0:
                        # Each source gets proportional share based on protein content
                        protein_share = (cat_prot / total_top_protein_capacity) * remaining_protein
                    else:
                        protein_share = remaining_protein / len(top_protein_sources)
                    
                    # Calculate exchanges needed
                    exchanges_needed = protein_share / cat_prot if cat_prot > 0 else 0
                    exchanges_needed = round(exchanges_needed * 2) / 2.0  # Round to 0.5
                    exchanges_needed = max(0.5, exchanges_needed)  # Minimum 0.5
                    
                    # If this category is already mandatory, add to existing exchanges
                    existing_exchanges = meal_exchanges.get(cat_id, 0)
                    meal_exchanges[cat_id] = existing_exchanges + exchanges_needed
                    remaining_protein -= exchanges_needed * cat_prot
                
                # If still need more protein, use the best source to fill remainder
                if remaining_protein > TOLERANCE_PROTEIN:
                    cat_id, cat_prot, cat_cal = protein_categories[0]
                    exchanges_to_add = remaining_protein / cat_prot if cat_prot > 0 else 0
                    exchanges_to_add = round(exchanges_to_add * 2) / 2.0
                    if exchanges_to_add > 0:
                        meal_exchanges[cat_id] = meal_exchanges.get(cat_id, 0) + exchanges_to_add
                        remaining_protein -= exchanges_to_add * cat_prot
        
        # Phase 2: Allocate REMAINING calories using calorie-rich categories
        current_calories, current_protein = calculate_nutrition(meal_exchanges)
        # Calculate remaining calories needed after Phase 1 allocations
        remaining_calories = remaining_calories_target - (current_calories - initial_calories)
        TOLERANCE_KCAL = 10.0
        
        # If we still need calories, use calorie-rich categories
        if remaining_calories > TOLERANCE_KCAL:
            # Sort calorie categories by calories (highest first)
            if calorie_categories:
                calorie_categories.sort(key=lambda x: x[1], reverse=True)
                
                # Allocate to fill remaining calories
                for cat_id, cat_cal, cat_prot in calorie_categories:
                    if remaining_calories <= TOLERANCE_KCAL:
                        break
                    
                    # Calculate exchanges needed for this category
                    exchanges_needed = remaining_calories / cat_cal if cat_cal > 0 else 0
                    
                    # Round to nearest 0.5
                    exchanges_needed = round(exchanges_needed * 2) / 2.0
                    
                    # Ensure minimum 0.5 if category is mandatory
                    exchanges_needed = max(0.5, exchanges_needed)
                    
                    meal_exchanges[cat_id] = meal_exchanges.get(cat_id, 0) + exchanges_needed
                    remaining_calories -= exchanges_needed * cat_cal
            
            # If we still need calories and have protein categories available, add more protein sources
            # (Protein sources also provide calories)
            if remaining_calories > TOLERANCE_KCAL and protein_categories:
                # Use protein categories with highest calories per exchange
                protein_by_calories = sorted(protein_categories, key=lambda x: x[2], reverse=True)
                for cat_id, cat_prot, cat_cal in protein_by_calories:
                    if remaining_calories <= TOLERANCE_KCAL:
                        break
                    # Add exchanges to fill remaining calories
                    exchanges_needed = remaining_calories / cat_cal if cat_cal > 0 else 0
                    exchanges_needed = round(exchanges_needed * 2) / 2.0
                    exchanges_needed = max(0.5, exchanges_needed)
                    meal_exchanges[cat_id] = meal_exchanges.get(cat_id, 0) + exchanges_needed
                    remaining_calories -= exchanges_needed * cat_cal
        
        # Round final values to 2 decimal places
        final_exchanges = {}
        for cat_id, count in meal_exchanges.items():
            if count > 0:
                final_exchanges[cat_id] = round(count, 2)
        
        return final_exchanges