"""
Food Engine.
Creates category-wise food lists per meal based on exchange allocations.

Responsibility:
- Filter foods based on medical exclusions
- Apply MNT constraints
- Apply Ayurveda preferences (advisory)
- Create lists of food items per exchange category per meal
- Map foods to exchange allocations from ExchangeSystemEngine

Inputs:
- Exchange context (mandatory) - exchange allocations per meal
- MNT constraints (mandatory)
- Nutrition targets (for reference)
- Ayurveda preferences (advisory)
- Client preferences

Outputs:
- Category-wise food lists per meal
- Exchange allocations per meal
- All foods mapped to their exchange categories

Note: This engine does NOT create recipes. It only provides filtered food lists
organized by exchange category. Recipe generation is handled by a separate Recipe Engine.
"""
from typing import Dict, List, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.platform.core.context import (
    MNTContext,
    TargetContext,
    AyurvedaContext,
    InterventionContext,
    ExchangeContext,
    DiagnosisContext,
)
from app.platform.engines.food_engine.kb_food_adapter import (
    get_category_wise_foods,
    get_foods_by_exchange_category,
    extract_medical_conditions,
)
from app.platform.engines.food_engine.food_ranker import (
    FoodRanker,
    RankingTierConfig,
)
from app.platform.engines.food_engine.food_deduplicator import FoodDeduplicator

# Import database models for simple query
from app.platform.data.models.kb_food_master import KBFoodMaster
from app.platform.data.models.kb_food_exchange_profile import KBFoodExchangeProfile
from app.platform.data.models.kb_food_mnt_profile import KBFoodMNTProfile
from app.platform.data.models.kb_food_condition_compatibility import KBFoodConditionCompatibility
from app.platform.data.models.kb_food_nutrition_base import KBFoodNutritionBase


class FoodEngine:
    """
    Food Engine.
    
    Responsibility:
    - Filter foods based on medical exclusions
    - Apply MNT constraints
    - Apply Ayurveda preferences (advisory)
    - Create category-wise food lists per meal
    - Map foods to exchange allocations
    
    Inputs:
    - Exchange context (mandatory) - exchange allocations per meal
    - MNT constraints (mandatory)
    - Nutrition targets (for reference)
    - Ayurveda preferences (advisory)
    - Client preferences
    
    Outputs:
    - Category-wise food lists per meal (max 15 foods per category)
    - Exchange allocations per meal
    - All constraint information
    
    Rules:
    - No hallucination allowed (only foods from knowledge base)
    - Must respect all MNT constraints
    - Must use exchange allocations from ExchangeSystemEngine
    - Foods grouped by exchange category
    - Ayurveda preferences are advisory only
    - All foods must reference knowledge base food IDs
    - Does NOT select specific foods or calculate portions (that's for Recipe Engine)
    - Maximum 15 foods per exchange category (top ranked)
    """
    
    # Maximum foods to return per exchange category
    MAX_FOODS_PER_CATEGORY = 15
    
    def __init__(self):
        """Initialize food engine."""
        pass
    
    def get_foods_by_category_simple(
        self,
        db: Session,
        exchange_category: str,
        food_exclusions: List[str],
        medical_conditions: Optional[List[str]] = None,
        micro_constraints: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Simple function to retrieve foods by category, filtering based on food_exclusions 
        and condition compatibility.
        
        This is a simplified version that filters by:
        1. Food exclusions (food_exclusion_tags) with Medical Safety Override
           - Only excludes if exclusion tag matches AND food is not medically safe
           - Allows foods that are medically safe despite having exclusion tags
        2. Condition compatibility (only allows "safe" compatibility, excludes contraindicated)
        3. MNT Profile Contraindications (checks contraindications array)
        4. Extreme Value Safety Checks (excludes foods too dangerous even with portion control)
        
        Args:
            db: Database session
            exchange_category: Exchange category (e.g., "cereal", "pulse", "milk", etc.)
            food_exclusions: List of food exclusion tags (e.g., ["canned_foods", "fried_foods", ...])
            medical_conditions: Optional list of medical condition IDs (e.g., ["diabetes", "hypertension"])
                                If provided, only foods with "safe" compatibility are included.
            micro_constraints: Optional micro constraints dict (e.g., {"sodium_mg": {"max": 2300}})
                              Used for extreme value safety checks.
            
        Returns:
            List of food dictionaries with basic information, filtered by constraints
            
        Note:
            - Filters based on food_exclusion_tags matching food_exclusions
            - If medical_conditions provided: excludes contraindicated foods, only includes "safe" foods
            - Foods without compatibility records are assumed safe (default allow)
            - Checks MNT profile contraindications array
            - Extreme value checks: excludes foods with >5x daily sodium max or >95% carbs
            - NOTE: diabetic_safe flag is NOT checked here - diabetes is handled through condition_compatibility
                    like all other medical conditions. The diabetic_safe flag is for Recipe Engine prioritization.
        """
        if not db:
            raise ValueError("Database session is required")
        
        if not exchange_category:
            raise ValueError("Exchange category is required")
        
        # Normalize food_exclusions to lowercase for case-insensitive matching
        food_exclusions_normalized = set()
        if food_exclusions:
            food_exclusions_normalized = {ex.lower() if isinstance(ex, str) else str(ex).lower() 
                                         for ex in food_exclusions}
        
        # Normalize medical conditions to lowercase
        medical_conditions_normalized = []
        if medical_conditions:
            medical_conditions_normalized = [c.lower() if isinstance(c, str) else str(c).lower() 
                                            for c in medical_conditions]
        
        # Query foods by exchange category
        # Join with MNT profile and nutrition to access food_exclusion_tags and nutrition data
        query = db.query(KBFoodMaster).join(
            KBFoodExchangeProfile,
            KBFoodMaster.food_id == KBFoodExchangeProfile.food_id
        ).outerjoin(
            KBFoodMNTProfile,
            KBFoodMaster.food_id == KBFoodMNTProfile.food_id
        ).outerjoin(
            KBFoodNutritionBase,
            KBFoodMaster.food_id == KBFoodNutritionBase.food_id
        ).filter(
            KBFoodMaster.status == 'active',
            KBFoodExchangeProfile.exchange_category == exchange_category
        )
        
        # Execute query
        foods = query.all()
        
        # Filter foods based on constraints
        filtered_foods = []
        
        for food in foods:
            # 1. Check food_exclusion_tags with Medical Safety Override
            food_exclusion_tags = []
            if food.mnt_profile and food.mnt_profile.food_exclusion_tags:
                food_exclusion_tags = [tag.lower() if isinstance(tag, str) else str(tag).lower()
                                      for tag in food.mnt_profile.food_exclusion_tags]
            
            should_exclude = False
            exclusion_reason = None
            
            # Check if any exclusion tag matches
            if food_exclusions_normalized and food_exclusion_tags:
                if any(tag in food_exclusions_normalized for tag in food_exclusion_tags):
                    # Smart check: Only exclude if food is NOT medically safe for user's conditions
                    # If medical_tags show food is safe for user's condition, allow it despite exclusion tag
                    is_medically_safe = False
                    
                    if medical_conditions_normalized and food.mnt_profile and food.mnt_profile.medical_tags:
                        medical_tags = food.mnt_profile.medical_tags or {}
                        
                        # Map conditions to medical_tags keys
                        condition_to_tag = {
                            "type_2_diabetes": "diabetic_safe",
                            "diabetes": "diabetic_safe",
                            "prediabetes": "prediabetic_safe",
                            "hypertension": "hypertension_safe",
                            "obesity": "obesity_safe",
                            "ckd": "renal_safe_stage_1_2",
                            "cardiovascular_disease": "cardiac_safe",
                            "cardiac": "cardiac_safe",
                        }
                        
                        # Check if food is safe for any of the user's conditions
                        for condition in medical_conditions_normalized:
                            tag_key = condition_to_tag.get(condition.lower())
                            if tag_key and medical_tags.get(tag_key, False):
                                is_medically_safe = True
                                break
                    
                    # Only exclude if NOT medically safe
                    if not is_medically_safe:
                        should_exclude = True
                        exclusion_reason = "food_exclusion_tag_without_medical_safety"
                    # If medically safe, allow the food despite exclusion tag
            
            # 2. Check condition compatibility (only if medical_conditions provided)
            if not should_exclude and medical_conditions_normalized:
                # Query compatibility records for this food and conditions
                compatibilities = db.query(KBFoodConditionCompatibility).filter(
                    KBFoodConditionCompatibility.food_id == food.food_id,
                    KBFoodConditionCompatibility.condition_id.in_(medical_conditions_normalized),
                    KBFoodConditionCompatibility.status == 'active'
                ).all()
                
                # If compatibility records exist, check them
                if compatibilities:
                    # Check each compatibility record
                    # If ANY record is not "safe", exclude the food
                    for compat in compatibilities:
                        compatibility_level = compat.compatibility.lower() if compat.compatibility else ""
                        
                        # Exclude contraindicated foods (hard exclusion)
                        if compatibility_level == 'contraindicated':
                            should_exclude = True
                            exclusion_reason = f"condition_contraindicated_{compat.condition_id}"
                            break
                        
                        # Only allow "safe" compatibility (exclude "avoid", "caution", etc.)
                        if compatibility_level != 'safe':
                            should_exclude = True
                            exclusion_reason = f"condition_not_safe_{compat.condition_id}_{compatibility_level}"
                            break
                # If no compatibility records exist for any condition, assume safe (default allow)
            
            # 3. Check MNT Profile Contraindications (only if medical_conditions provided)
            if not should_exclude and medical_conditions_normalized and food.mnt_profile:
                contraindications = food.mnt_profile.contraindications or []
                if contraindications:
                    # Normalize contraindications and conditions to lowercase for comparison
                    contraindications_lower = [
                        c.lower() if isinstance(c, str) else str(c).lower() 
                        for c in contraindications
                    ]
                    # Check if any user condition matches contraindications
                    if any(cond in contraindications_lower for cond in medical_conditions_normalized):
                        should_exclude = True
                        exclusion_reason = "mnt_profile_contraindication"
            
            # 4. Extreme Value Safety Checks (only exclude foods too dangerous even with portion control)
            if not should_exclude and food.nutrition and micro_constraints:
                # Extract nutrition data
                macros = food.nutrition.macros or {}
                micros = food.nutrition.micros or {}
                calories = float(food.nutrition.calories_kcal) if food.nutrition.calories_kcal else 0.0
                carbs_g = float(macros.get("carbs_g", 0)) if macros else 0.0
                sodium_mg = float(micros.get("sodium_mg", 0)) if micros else 0.0
                
                # 4a. Extreme sodium check (>5x daily max per 100g - unsafe even with minimal portions)
                sodium_constraint = micro_constraints.get("sodium_mg") or {}
                if "max" in sodium_constraint:
                    sodium_max_mg = sodium_constraint["max"]
                    # Exclude if sodium per 100g is >5x daily max (e.g., >11500mg for 2300mg limit)
                    # This ensures foods like pure salt or extremely processed foods are excluded
                    if sodium_mg > sodium_max_mg * 5:
                        should_exclude = True
                        exclusion_reason = f"extremely_high_sodium_unsafe_{sodium_mg}mg_per_100g"
                
                # 4b. Extreme carb check (>95% carbs - pure sugar/starch, unsafe for portion control)
                if not should_exclude and calories > 0:
                    carb_pct = (carbs_g * 4 / calories) * 100
                    # Exclude foods that are >95% carbs (essentially pure sugar/starch)
                    # These cannot be safely portioned for diabetes management
                    if carb_pct > 95:
                        should_exclude = True
                        exclusion_reason = f"extremely_high_carb_unsafe_{carb_pct:.1f}%_carbs"
            
            # Include food only if it should NOT be excluded
            if not should_exclude:
                # Build simple food dictionary
                food_dict = {
                    "food_id": food.food_id,
                    "display_name": food.display_name,
                    "category": food.category,
                    "exchange_category": food.exchange_profile.exchange_category,
                    "food_exclusion_tags": food_exclusion_tags,  # Include for debugging
                }
                
                # Add exchange profile info if available
                if food.exchange_profile:
                    food_dict["serving_size_per_exchange_g"] = (
                        float(food.exchange_profile.serving_size_per_exchange_g) 
                        if food.exchange_profile.serving_size_per_exchange_g else None
                    )
                
                # Add nutrition data for ranking
                if food.nutrition:
                    macros = food.nutrition.macros or {}
                    micros = food.nutrition.micros or {}
                    food_dict["nutrition"] = {
                        "calories": float(food.nutrition.calories_kcal) if food.nutrition.calories_kcal else None,
                        "macros": {
                            "protein_g": float(macros.get("protein_g", 0)) if macros else 0.0,
                            "carbs_g": float(macros.get("carbs_g", 0)) if macros else 0.0,
                            "fat_g": float(macros.get("fat_g", 0)) if macros else 0.0,
                            "fiber_g": float(macros.get("fiber_g", 0)) if macros else 0.0,
                        },
                        "micros": micros,
                        "calorie_density_kcal_per_g": float(food.nutrition.calorie_density_kcal_per_g) if food.nutrition.calorie_density_kcal_per_g else None,
                        "protein_density_g_per_100kcal": float(food.nutrition.protein_density_g_per_100kcal) if food.nutrition.protein_density_g_per_100kcal else None,
                    }
                
                # Add MNT profile data for ranking
                if food.mnt_profile:
                    food_dict["mnt_profile"] = {
                        "macro_compliance": food.mnt_profile.macro_compliance or {},
                        "micro_compliance": food.mnt_profile.micro_compliance or {},
                        "medical_tags": food.mnt_profile.medical_tags or {},
                        "food_exclusion_tags": list(food.mnt_profile.food_exclusion_tags) if food.mnt_profile.food_exclusion_tags else [],
                        "food_inclusion_tags": list(food.mnt_profile.food_inclusion_tags) if food.mnt_profile.food_inclusion_tags else [],
                        "contraindications": list(food.mnt_profile.contraindications) if food.mnt_profile.contraindications else [],
                        "preferred_conditions": list(food.mnt_profile.preferred_conditions) if food.mnt_profile.preferred_conditions else [],
                    }
                
                # Add compatibility and MNT profile info if checked
                if medical_conditions_normalized:
                    food_dict["compatibility_checked"] = True
                    # Query again to get compatibility levels for reporting
                    compat_records = db.query(KBFoodConditionCompatibility).filter(
                        KBFoodConditionCompatibility.food_id == food.food_id,
                        KBFoodConditionCompatibility.condition_id.in_(medical_conditions_normalized),
                        KBFoodConditionCompatibility.status == 'active'
                    ).all()
                    if compat_records:
                        food_dict["compatibility_levels"] = {
                            rec.condition_id: rec.compatibility 
                            for rec in compat_records
                        }
                    else:
                        food_dict["compatibility_levels"] = {}  # No records = assumed safe
                    
                    # Add MNT profile info for debugging (if not already added above)
                    if food.mnt_profile and "mnt_profile_info" not in food_dict:
                        food_dict["mnt_profile_info"] = {
                            "contraindications": list(food.mnt_profile.contraindications) if food.mnt_profile.contraindications else [],
                        }
                else:
                    food_dict["compatibility_checked"] = False
                
                # Add additional metadata for ranking
                food_dict["food_type"] = food.food_type
                food_dict["cooking_state"] = food.cooking_state
                
                filtered_foods.append(food_dict)
            # Debug: Log excluded foods (optional - can be removed later)
            # else:
            #     print(f"Excluded {food.food_id}: {exclusion_reason}")
        
        return filtered_foods
    
    def get_foods_by_category_simple_dict(
        self,
        db: Session,
        exchange_categories: List[str],
        food_exclusions: List[str],
        medical_conditions: Optional[List[str]] = None,
        micro_constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve foods by multiple categories, filtering based on food_exclusions 
        and condition compatibility.
        
        This is a convenience function that calls get_foods_by_category_simple for each category.
        
        Args:
            db: Database session
            exchange_categories: List of exchange categories (e.g., ["cereal", "pulse", "milk"])
            food_exclusions: List of food exclusion tags (e.g., ["canned_foods", "fried_foods", ...])
            medical_conditions: Optional list of medical condition IDs (e.g., ["diabetes", "hypertension"])
            
        Returns:
            Dictionary: {exchange_category: [food1, food2, ...], ...}
            
        Example:
            >>> engine = FoodEngine()
            >>> result = engine.get_foods_by_category_simple_dict(
            ...     db=db,
            ...     exchange_categories=["cereal", "pulse"],
            ...     food_exclusions=["canned_foods", "fried_foods"],
            ...     medical_conditions=["diabetes"]
            ... )
            >>> print(result["cereal"])  # List of cereal foods (safe for diabetes, excluding canned/fried)
            >>> print(result["pulse"])   # List of pulse foods (safe for diabetes, excluding canned/fried)
        """
        if not exchange_categories:
            return {}
        
        result = {}
        for category in exchange_categories:
            result[category] = self.get_foods_by_category_simple(
                db=db,
                exchange_category=category,
                food_exclusions=food_exclusions,
                medical_conditions=medical_conditions,
                micro_constraints=micro_constraints
            )
        
        return result
    
    def generate_food_lists(
        self,
        mnt_context: MNTContext,
        target_context: TargetContext,
        exchange_context: ExchangeContext,
        ayurveda_context: Optional[AyurvedaContext] = None,
        diagnosis_context: Optional[DiagnosisContext] = None,
        client_preferences: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None,
        ranking_config: Optional[RankingTierConfig] = None,
        rotation_history: Optional[List[str]] = None
    ) -> InterventionContext:
        """
        Generate category-wise food lists per meal based on exchange allocations.
        
        Args:
            mnt_context: MNT context with constraints and exclusions
            target_context: Target context with nutrition targets (for reference)
            exchange_context: Exchange context with allocations per meal
            ayurveda_context: Optional Ayurveda context with preferences
            diagnosis_context: Optional diagnosis context with medical conditions
            client_preferences: Optional client food preferences
            db: Database session for querying KB food tables
            ranking_config: Optional ranking tier configuration. If None, uses default config.
            rotation_history: Optional list of recently used food IDs for variety tracking
            
        Returns:
            InterventionContext with category-wise food lists only.
            Simplified output: only meal_plan.category_wise_foods, assessment_id, plan_id, plan_version.
            Removed: explanations, constraints_snapshot, meals, exchange_allocations.
            
        Note:
            This method:
            1. Gets category-wise foods for each meal based on exchange allocations
            2. Applies medical exclusions
            3. Applies MNT constraints
            4. Applies Ayurveda preferences (advisory)
            5. Ranks foods using multi-tier ranking system (if enabled)
            6. Returns filtered and ranked food lists organized by exchange category
            All foods must be from knowledge base - no hallucination.
            Food selection and recipe creation is handled by Recipe Engine.
        """
        if db is None:
            raise ValueError("Database session is required for food engine.")
        
        # Extract Ayurveda preferences
        ayurveda_preferences = None
        if ayurveda_context:
            ayurveda_preferences = self._extract_ayurveda_preferences(ayurveda_context)
        
        # Apply client preferences filtering
        excluded_food_ids = set()
        if client_preferences:
            excluded_food_ids = set(client_preferences.get("dislikes", []))
        
        # OPTIMIZATION: Generate category-wise foods ONCE at plan level (not per meal)
        # Since filtering criteria (MNT, medical conditions, Ayurveda) are the same for all meals,
        # we only need to generate the food lists once and share them across all meals.
        
        # Collect all unique exchange categories across all meals
        all_exchange_categories = set()
        for meal_exchanges in exchange_context.exchanges_per_meal.values():
            all_exchange_categories.update(meal_exchanges.keys())
        
        # Generate category-wise foods once for all categories using SIMPLIFIED approach
        plan_level_category_wise_foods = {}
        
        # Extract medical conditions - prefer from diagnosis_context if available
        if diagnosis_context and diagnosis_context.medical_conditions:
            # Extract diagnosis IDs from diagnosis context
            medical_conditions = [
                cond.get("diagnosis_id") 
                for cond in diagnosis_context.medical_conditions 
                if cond.get("diagnosis_id")
            ]
        else:
            # Fallback: extract from MNT context (less accurate)
            medical_conditions = self._extract_medical_conditions_from_mnt(mnt_context)
        
        # Use simplified food filtering function
        foods_by_category = self.get_foods_by_category_simple_dict(
            db=db,
            exchange_categories=list(all_exchange_categories),
            food_exclusions=mnt_context.food_exclusions or [],
            medical_conditions=medical_conditions,
            micro_constraints=mnt_context.micro_constraints
        )
        
        # Initialize food ranker
        # Default: enable ranking with all tiers
        # If ranking_config is provided, use it (even if all tiers disabled)
        tier_config = ranking_config if ranking_config is not None else RankingTierConfig()
        ranker = FoodRanker(tier_config=tier_config)
        
        # Initialize deduplicator (once, before the loop)
        deduplicator = FoodDeduplicator(
            enable_scientific_name_matching=True,
            enable_base_name_matching=True
        )
        
        # Apply client preferences (remove disliked foods), deduplicate, rank foods, and limit to max 15 per category
        for exchange_category in all_exchange_categories:
            if exchange_category:  # Skip empty categories
                foods = foods_by_category.get(exchange_category, [])
                
                # Step 1: Apply client preferences (remove disliked foods)
                if excluded_food_ids:
                    foods = [
                        food for food in foods 
                        if food.get("food_id") not in excluded_food_ids
                    ]
                
                # Step 2: Deduplicate food variations (before ranking)
                # This removes duplicate variations so we only rank unique foods
                foods = deduplicator.deduplicate_foods(foods, keep_best_ranked=False)
                # Note: keep_best_ranked=False because we'll rank after deduplication
                
                # Step 3: Rank foods if ranker is available
                if ranker:
                    # Get meal targets for this category's meal (simplified - use first meal with this category)
                    meal_targets = None
                    meal_name = None
                    for meal, exchanges in exchange_context.exchanges_per_meal.items():
                        if exchange_category in exchanges:
                            meal_targets = exchange_context.per_meal_targets.get(meal)
                            meal_name = meal
                            break
                    
                    # Rank foods (now on deduplicated list)
                    foods = ranker.rank_foods(
                        foods=foods,
                        medical_conditions=medical_conditions,
                        mnt_context=mnt_context,
                        target_context=target_context,
                        ayurveda_context=ayurveda_context,
                        diagnosis_context=diagnosis_context,
                        client_preferences=client_preferences,
                        meal_targets=meal_targets,
                        rotation_history=rotation_history,
                        meal_name=meal_name
                    )
                else:
                    # Fallback: Apply basic Ayurveda sorting if ranking disabled
                    if ayurveda_preferences:
                        prefer_ids = set(ayurveda_preferences.get("prefer", []))
                        avoid_ids = set(ayurveda_preferences.get("avoid", []))
                        
                        # Sort: prefer foods first, then avoid foods last
                        foods = sorted(
                            foods,
                            key=lambda f: (
                                0 if f.get("food_id") in prefer_ids else 1,  # Prefer first
                                1 if f.get("food_id") in avoid_ids else 0,   # Avoid last
                            )
                        )
                
                # Step 4: Limit to max 15 foods per category (top ranked)
                # If less than 15, return all
                if len(foods) > self.MAX_FOODS_PER_CATEGORY:
                    foods = foods[:self.MAX_FOODS_PER_CATEGORY]
                
                plan_level_category_wise_foods[exchange_category] = foods
        
        # Build simplified meal plan structure - only category_wise_foods
        # Removed: meals (already in exchange allocation system)
        # Removed: exchange_allocations (not needed here)
        meal_plan = {
            "category_wise_foods": plan_level_category_wise_foods,
        }
        
        return InterventionContext(
            client_id=getattr(mnt_context, "client_id", UUID(int=0)),
            assessment_id=mnt_context.assessment_id,
            plan_id=None,  # Will be set by orchestrator if needed
            plan_version=None,  # Will be set by orchestrator if needed
            meal_plan=meal_plan,
            explanations=None,  # Removed - already in respective engine's output
            constraints_snapshot=None,  # Removed - already in respective engine's output
        )
    
    def generate_meal_plan(
        self,
        mnt_context: MNTContext,
        target_context: TargetContext,
        exchange_context: ExchangeContext,
        ayurveda_context: Optional[AyurvedaContext] = None,
        diagnosis_context: Optional[DiagnosisContext] = None,
        client_preferences: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None,
        ranking_config: Optional[RankingTierConfig] = None,
        rotation_history: Optional[List[str]] = None
    ) -> InterventionContext:
        """
        Generate meal plan (alias for generate_food_lists for backward compatibility).
        
        This method is kept for compatibility but delegates to generate_food_lists.
        """
        return self.generate_food_lists(
            mnt_context=mnt_context,
            target_context=target_context,
            exchange_context=exchange_context,
            ayurveda_context=ayurveda_context,
            diagnosis_context=diagnosis_context,
            client_preferences=client_preferences,
            db=db,
            ranking_config=ranking_config,
            rotation_history=rotation_history
        )
    
    def _extract_medical_conditions_from_mnt(self, mnt_context: MNTContext) -> List[str]:
        """
        Extract medical conditions from MNT context.
        
        This is a fallback method. Ideally, medical conditions should come from
        DiagnosisContext, but since FoodEngine doesn't receive it, we extract
        from food_exclusions patterns as a workaround.
        
        TODO: Consider storing medical_conditions in MNTContext or passing DiagnosisContext to FoodEngine.
        """
        # Try to extract from food_exclusions patterns (current approach)
        conditions = extract_medical_conditions(mnt_context)
        
        # If no conditions found, return empty list (filtering will be less strict)
        return conditions
    
    def _extract_ayurveda_preferences(
        self,
        ayurveda_context: AyurvedaContext
    ) -> Dict[str, Any]:
        """Extract Ayurveda preferences from context."""
        if not ayurveda_context:
            return {}
        
        notes = getattr(ayurveda_context, "vikriti_notes", {}) or {}
        food_prefs = notes.get("food_preferences") or []
        
        prefer = [p["food_id"] for p in food_prefs if p.get("preference_type") == "prefer"]
        avoid = [p["food_id"] for p in food_prefs if p.get("preference_type") == "avoid"]
        
        return {
            "prefer": prefer,
            "avoid": avoid,
            "dosha_primary": getattr(ayurveda_context, "dosha_primary", None),
            "dosha_secondary": getattr(ayurveda_context, "dosha_secondary", None),
        }
