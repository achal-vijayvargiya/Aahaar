"""
KB Food Adapter for Food Engine.
Queries kb_food_* tables with all constraints applied.
"""
from typing import Dict, Any, List, Optional, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.platform.data.models.kb_food_master import KBFoodMaster
from app.platform.data.models.kb_food_nutrition_base import KBFoodNutritionBase
from app.platform.data.models.kb_food_exchange_profile import KBFoodExchangeProfile
from app.platform.data.models.kb_food_mnt_profile import KBFoodMNTProfile
from app.platform.data.models.kb_food_condition_compatibility import KBFoodConditionCompatibility
from app.platform.core.context import MNTContext, ExchangeContext
import logging

logger = logging.getLogger(__name__)


def extract_nutrition(nutrition: Optional[KBFoodNutritionBase]) -> Dict[str, Any]:
    """Extract nutrition data from KBFoodNutritionBase model."""
    if not nutrition:
        return {}
    
    macros = nutrition.macros or {}
    micros = nutrition.micros or {}
    
    return {
        "calories": float(nutrition.calories_kcal) if nutrition.calories_kcal else 0.0,
        "carbs_g": float(macros.get("carbs_g", 0)) if macros else 0.0,
        "protein_g": float(macros.get("protein_g", 0)) if macros else 0.0,
        "fat_g": float(macros.get("fat_g", 0)) if macros else 0.0,
        "fiber_g": float(macros.get("fiber_g", 0)) if macros else 0.0,
        "sodium_mg": float(micros.get("sodium_mg", 0)) if micros else 0.0,
        "calorie_density_kcal_per_g": float(nutrition.calorie_density_kcal_per_g) if nutrition.calorie_density_kcal_per_g else 0.0,
        "protein_density_g_per_100kcal": float(nutrition.protein_density_g_per_100kcal) if nutrition.protein_density_g_per_100kcal else 0.0,
        "macros": macros,
        "micros": micros,
        "glycemic_properties": nutrition.glycemic_properties or {},
    }


def extract_mnt_profile(mnt_profile: Optional[KBFoodMNTProfile]) -> Dict[str, Any]:
    """Extract MNT profile data from KBFoodMNTProfile model."""
    if not mnt_profile:
        return {}
    
    return {
        "macro_compliance": mnt_profile.macro_compliance or {},
        "micro_compliance": mnt_profile.micro_compliance or {},
        "medical_tags": mnt_profile.medical_tags or {},
        "food_exclusion_tags": list(mnt_profile.food_exclusion_tags) if mnt_profile.food_exclusion_tags else [],
        "food_inclusion_tags": list(mnt_profile.food_inclusion_tags) if mnt_profile.food_inclusion_tags else [],
        "contraindications": list(mnt_profile.contraindications) if mnt_profile.contraindications else [],
        "preferred_conditions": list(mnt_profile.preferred_conditions) if mnt_profile.preferred_conditions else [],
    }


def extract_medical_conditions(mnt_context: MNTContext) -> List[str]:
    """Extract medical conditions from MNT context."""
    conditions = []
    food_exclusions = mnt_context.food_exclusions or []
    
    exclusion_lower = [ex.lower() if isinstance(ex, str) else str(ex).lower() for ex in food_exclusions]
    
    # Map common exclusion patterns to conditions
    if any("diabetes" in ex or "sugar" in ex for ex in exclusion_lower):
        conditions.append("diabetes")
    if any("kidney" in ex or "ckd" in ex for ex in exclusion_lower):
        conditions.append("ckd")
    if any("gerd" in ex or "reflux" in ex or "acid" in ex for ex in exclusion_lower):
        conditions.append("gerd")
    if any("hypertension" in ex or "high_blood_pressure" in ex or "bp" in ex for ex in exclusion_lower):
        conditions.append("hypertension")
    if any("obesity" in ex or "weight" in ex for ex in exclusion_lower):
        conditions.append("obesity")
    
    return conditions


def _check_tier1_hard_exclusions(
    food_id: str,
    mnt_context: MNTContext,
    medical_conditions: List[str],
    mnt_profile: Dict[str, Any],
    db: Session
) -> Tuple[bool, Optional[str]]:
    """
    Tier 1: Hard Medical Safety Checks (NEVER bypass).
    
    Returns:
        (is_excluded, reason) - True if excluded, False if safe
    """
    # 1. Direct food ID exclusions (hard exclusion)
    food_exclusions = set(mnt_context.food_exclusions or [])
    if food_id in food_exclusions:
        return (True, "direct_food_exclusion")
    
    # 2. Condition compatibility check (hard exclusion - ONLY contraindicated)
    # Note: "avoid" status is moved to Tier 2 (soft constraint) to allow variety
    if medical_conditions:
        compatible = check_condition_compatibility(db, food_id, medical_conditions, tier1_only=True)
        if not compatible:
            return (True, "condition_contraindicated")
    
    # 3. Contraindications in MNT profile (hard exclusion)
    contraindications = mnt_profile.get("contraindications", [])
    if contraindications and medical_conditions:
        # Check if any user condition is in contraindications
        contraindications_lower = [c.lower() if isinstance(c, str) else str(c).lower() for c in contraindications]
        conditions_lower = [c.lower() if isinstance(c, str) else str(c).lower() for c in medical_conditions]
        if any(cond in contraindications_lower for cond in conditions_lower):
            return (True, "mnt_profile_contraindication")
    
    # 4. NEW: Check diabetic_safe flag for diabetes conditions (Bug 8.1 - CRITICAL)
    # Foods with diabetic_safe=false should NEVER be recommended for diabetes patients
    diabetes_conditions = [c for c in medical_conditions if "diabetes" in c.lower()]
    if diabetes_conditions:
        medical_tags = mnt_profile.get("medical_tags", {})
        diabetic_safe = medical_tags.get("diabetic_safe")
        
        # If diabetic_safe is explicitly False, exclude (this is a hard safety check)
        if diabetic_safe is False:
            return (True, "diabetic_safe_false")
        
        # Also check glycemic classification from medical_tags
        # If glycemic_classification is high_gi and diabetic_safe is explicitly False, exclude
        # Note: If diabetic_safe is None (unknown), allow it (will be lower priority in Tier 2)
        glycemic_classification = medical_tags.get("glycemic_classification")
        if isinstance(glycemic_classification, str) and glycemic_classification.lower() == "high_gi":
            # High-GI foods are unsafe for diabetes ONLY if explicitly marked unsafe (False)
            # If diabetic_safe is None, allow it (will be deprioritized in Tier 2)
            if diabetic_safe is False:  # Only exclude if explicitly False
                return (True, "high_gi_and_diabetic_safe_false")
        
        # Check prediabetic_safe for prediabetes condition
        if "prediabetes" in [c.lower() for c in diabetes_conditions]:
            prediabetic_safe = medical_tags.get("prediabetic_safe")
            if prediabetic_safe is False:
                return (True, "prediabetic_safe_false")
    
    return (False, None)


def _check_tier2_soft_constraints(
    food: Any,
    nutrition: Dict[str, Any],
    mnt_profile: Dict[str, Any],
    mnt_context: MNTContext,
    medical_conditions: List[str],
    relax_constraints: bool = False,
    db: Optional[Session] = None
) -> Tuple[bool, Optional[str]]:
    """
    Tier 2: Soft Constraints (can be relaxed if needed).
    
    NOTE: Macro/micro constraint filtering (carb %, sodium) has been moved to Recipe Engine
    for portion-based optimization. This function now only checks:
    - Food exclusion tags (if medically unsafe)
    - Condition "avoid" status (can relax for variety)
    - Extreme value safety checks (foods too dangerous even with portion control)
    
    Args:
        relax_constraints: If True, relaxes constraints for variety
    
    Returns:
        (is_excluded, reason) - True if excluded, False if safe
    """
    macro_constraints = mnt_context.macro_constraints or {}
    micro_constraints = mnt_context.micro_constraints or {}
    food_exclusions = set(mnt_context.food_exclusions or [])
    
    calories = nutrition.get("calories", 0) or 0.0
    carbs_g = nutrition.get("carbs_g", 0) or 0.0
    sodium_mg = nutrition.get("sodium_mg", 0) or 0.0
    # Convert Decimal to float if needed (database models return Decimal)
    serving_size_per_exchange_g = float(food.exchange_profile.serving_size_per_exchange_g) if food.exchange_profile.serving_size_per_exchange_g else 0.0
    
    # 1. Food exclusion tags check (can relax if medical_tags show safe)
    exclusion_tags = mnt_profile.get("food_exclusion_tags", [])
    if exclusion_tags and not relax_constraints:
        exclusion_lower = [ex.lower() if isinstance(ex, str) else str(ex).lower() for ex in food_exclusions]
        tag_lower = [tag.lower() if isinstance(tag, str) else str(tag).lower() for tag in exclusion_tags]
        
        # Only exclude if tag matches AND medical_tags show unsafe
        if any(tag in exclusion_lower for tag in tag_lower):
            medical_tags = mnt_profile.get("medical_tags", {})
            
            # Check if food is actually safe for user's conditions despite exclusion tag
            is_medically_safe = False
            if medical_conditions:
                # Map conditions to medical_tags keys
                condition_to_tag = {
                    "type_2_diabetes": "diabetic_safe",
                    "diabetes": "diabetic_safe",
                    "prediabetes": "prediabetic_safe",
                    "hypertension": "hypertension_safe",
                    "obesity": "obesity_safe",
                    "ckd": "renal_safe_stage_1_2",
                }
                
                for condition in medical_conditions:
                    tag_key = condition_to_tag.get(condition.lower())
                    if tag_key and medical_tags.get(tag_key, False):
                        is_medically_safe = True
                        break
            
            # Only exclude if not medically safe
            if not is_medically_safe:
                return (True, "exclusion_tag_without_medical_safety")
    
    # 2. Condition compatibility "avoid" status (Tier 2 soft constraint)
    # Foods with "avoid" status can be included when variety is needed, but with lower priority
    if medical_conditions and not relax_constraints and db is not None:
        from app.platform.data.models.kb_food_condition_compatibility import KBFoodConditionCompatibility
        avoid_records = db.query(KBFoodConditionCompatibility).filter(
            KBFoodConditionCompatibility.food_id == food.food_id,
            KBFoodConditionCompatibility.condition_id.in_(medical_conditions),
            KBFoodConditionCompatibility.compatibility == 'avoid',
            KBFoodConditionCompatibility.status == 'active'
        ).first()
        
        if avoid_records:
            # "Avoid" foods are excluded in strict mode, but allowed when relaxed for variety
            return (True, "condition_avoid_status")
    
    # 3. EXTREME VALUE SAFETY CHECKS (NEW)
    # Only exclude foods that are too dangerous even with portion control
    # These checks ensure foods with >5x daily limits are excluded (cannot be safely portioned)
    
    # 3a. Extreme sodium check (>5x daily max per 100g - unsafe even with minimal portions)
    sodium_constraint = micro_constraints.get("sodium_mg") or {}
    if "max" in sodium_constraint:
        sodium_max_mg = sodium_constraint["max"]
        # Exclude if sodium per 100g is >5x daily max (e.g., >11500mg for 2300mg limit)
        # This ensures foods like pure salt or extremely processed foods are excluded
        if sodium_mg > sodium_max_mg * 5:
            return (True, "extremely_high_sodium_unsafe")
    
    # 3b. Extreme carb check (>95% carbs - pure sugar/starch, unsafe for portion control)
    if calories > 0:
        carb_pct = (carbs_g * 4 / calories) * 100
        # Exclude foods that are >95% carbs (essentially pure sugar/starch)
        # These cannot be safely portioned for diabetes management
        if carb_pct > 95:
            return (True, "extremely_high_carb_unsafe")
    
    # Note: Regular macro/micro constraint filtering (carb %, sodium limits) is now handled
    # by Recipe Engine using macro_compliance/micro_compliance flags for portion adjustment.
    # This allows more food variety while maintaining medical safety through portion control.
    
    return (False, None)


def get_foods_by_exchange_category(
    db: Session,
    exchange_category: str,
    mnt_context: MNTContext,
    medical_conditions: Optional[List[str]] = None,
    ayurveda_preferences: Optional[Dict[str, Any]] = None,
    min_variety_count: int = 5
) -> List[Dict[str, Any]]:
    """
    Get foods filtered by exchange category with two-tier filtering.
    
    Tier 1 (Hard): Medical safety - never bypassed
    - Direct food ID exclusions
    - Condition compatibility (contraindicated only)
    - MNT profile contraindications
    - Diabetes safety flags (diabetic_safe=False)
    
    Tier 2 (Soft): Constraint optimization - can be relaxed for variety
    - Food exclusion tags (only exclude if not medically safe)
    - Condition "avoid" status (can relax for variety)
    - Extreme value safety checks (>5x daily limits - unsafe even with portion control)
    
    NOTE: Macro/micro constraint filtering (carb %, sodium limits) has been moved to Recipe Engine
    for portion-based optimization. This allows more food variety while maintaining medical safety
    through portion control using macro_compliance/micro_compliance flags.
    
    Args:
        db: Database session
        exchange_category: Exchange category (cereal, pulse, milk, etc.)
        mnt_context: MNT context with constraints
        medical_conditions: List of medical conditions
        ayurveda_preferences: Optional Ayurveda preferences
        min_variety_count: Minimum number of foods to return per category (default: 5)
        
    Returns:
        List of food dictionaries with all relevant data, sorted by safety preference
    """
    # Base query with joins
    query = db.query(KBFoodMaster).join(
        KBFoodExchangeProfile,
        KBFoodMaster.food_id == KBFoodExchangeProfile.food_id
    ).join(
        KBFoodNutritionBase,
        KBFoodMaster.food_id == KBFoodNutritionBase.food_id
    ).outerjoin(
        KBFoodMNTProfile,
        KBFoodMaster.food_id == KBFoodMNTProfile.food_id
    ).filter(
        KBFoodMaster.status == 'active',
        KBFoodExchangeProfile.exchange_category == exchange_category
    )
    
    # Execute query - get all foods first
    foods_data = query.all()
    
    medical_conditions = medical_conditions or extract_medical_conditions(mnt_context)
    
    # Two-tier filtering
    tier1_passed = []  # Passed Tier 1 (hard exclusions)
    all_foods_scored = []  # All foods with scores for sorting
    
    for food in foods_data:
        nutrition = extract_nutrition(food.nutrition)
        mnt_profile = extract_mnt_profile(food.mnt_profile)
        
        # Tier 1: Hard medical safety (NEVER bypass)
        is_excluded, reason = _check_tier1_hard_exclusions(
            food.food_id, mnt_context, medical_conditions, mnt_profile, db
        )
        if is_excluded:
            continue  # Skip - medically unsafe
        
        tier1_passed.append((food, nutrition, mnt_profile))
    
    # If no foods pass Tier 1, return empty (safety first!)
    if not tier1_passed:
        return []
    
    # Try Tier 2 filtering without relaxation first
    filtered_foods_strict = []
    for food, nutrition, mnt_profile in tier1_passed:
        is_excluded, reason = _check_tier2_soft_constraints(
            food, nutrition, mnt_profile, mnt_context, medical_conditions, relax_constraints=False, db=db
        )
        
        if not is_excluded:
            # Build food dictionary
            food_dict = _build_food_dict(food, nutrition, mnt_profile)
            food_dict["_filtering_metadata"] = {
                "tier1_passed": True,
                "tier2_passed": True,
                "relaxed": False
            }
            filtered_foods_strict.append(food_dict)
    
    # If we have enough variety, return strict results
    if len(filtered_foods_strict) >= min_variety_count:
        return _sort_foods_by_safety_preference(filtered_foods_strict, medical_conditions, mnt_context)
    
    # Not enough variety - relax Tier 2 constraints progressively
    # Priority: Foods with medical_tags.condition_safe = true
    filtered_foods_relaxed = []
    for food, nutrition, mnt_profile in tier1_passed:
        is_excluded, reason = _check_tier2_soft_constraints(
            food, nutrition, mnt_profile, mnt_context, medical_conditions, relax_constraints=True, db=db
        )
        
        if not is_excluded:
            # Build food dictionary
            food_dict = _build_food_dict(food, nutrition, mnt_profile)
            
            # Calculate safety score for prioritization
            medical_tags = mnt_profile.get("medical_tags", {})
            safety_score = _calculate_safety_score(food_dict, medical_tags, medical_conditions)
            
            food_dict["_filtering_metadata"] = {
                "tier1_passed": True,
                "tier2_passed": True,
                "relaxed": True,
                "relaxation_reason": reason
            }
            food_dict["_safety_score"] = safety_score
            filtered_foods_relaxed.append(food_dict)
    
    # Sort by safety score (higher = safer)
    filtered_foods_relaxed.sort(key=lambda x: x.get("_safety_score", 0), reverse=True)
    
    # FINAL SAFETY GATE: Double-check Tier 1 exclusions (Bug 8.1)
    # This ensures no unsafe foods slip through even after Tier 2 relaxation
    safe_foods = []
    # Check for diabetes conditions again for final gate
    diabetes_conditions_check = [c for c in medical_conditions if "diabetes" in c.lower()] if medical_conditions else []
    
    for food_dict in filtered_foods_relaxed:
        food_id = food_dict.get("food_id")
        mnt_profile_data = food_dict.get("mnt_profile", {})
        medical_tags = mnt_profile_data.get("medical_tags", {})
        
        # Final check: diabetic_safe flag for diabetes conditions
        if diabetes_conditions_check:
            diabetic_safe = medical_tags.get("diabetic_safe")
            if diabetic_safe is False:
                # Log exclusion for debugging (this should not happen if Tier 1 worked correctly)
                continue  # Skip - diabetic_safe=false
            
            # Also check high-GI foods for diabetes (only if explicitly unsafe)
            glycemic_classification = medical_tags.get("glycemic_classification")
            if isinstance(glycemic_classification, str) and glycemic_classification.lower() == "high_gi":
                if diabetic_safe is False:  # Only skip if explicitly False
                    continue  # Skip - high-GI and explicitly unsafe
        
        safe_foods.append(food_dict)
    
    # NEW: Enhanced variety logic - if we don't have enough safe foods, include ALL Tier 1 foods
    # This ensures we have enough options while maintaining medical safety
    if len(safe_foods) < min_variety_count and tier1_passed:
        logger.warning(
            f"Only {len(safe_foods)} foods passed all filters for category '{exchange_category}'. "
            f"Including all Tier 1 safe foods to ensure variety (minimum needed: {min_variety_count})."
        )
        
        # Include all Tier 1 passed foods that weren't already included
        # This is safe because Tier 1 ensures medical safety (hard exclusions are never bypassed)
        tier1_food_ids = {f.get("food_id") for f in safe_foods}
        target_count = max(min_variety_count * 2, 10)  # Get 2x for better variety, minimum 10
        
        for food, nutrition, mnt_profile in tier1_passed:
            food_id = food.food_id
            
            # Skip if already in safe_foods
            if food_id in tier1_food_ids:
                continue
            
            # Build food dict
            food_dict_existing = _build_food_dict(food, nutrition, mnt_profile)
            
            # Calculate safety score
            medical_tags = mnt_profile.get("medical_tags", {})
            safety_score = _calculate_safety_score(food_dict_existing, medical_tags, medical_conditions)
            food_dict_existing["_safety_score"] = safety_score
            safe_foods.append(food_dict_existing)
            tier1_food_ids.add(food_id)
            
            # Stop when we have enough (but get extra for better variety)
            if len(safe_foods) >= target_count:
                break
        
        # Re-sort by safety score (safest first)
        safe_foods.sort(key=lambda x: x.get("_safety_score", 0), reverse=True)
    
    # Return up to 2x min_variety_count for better variety, but prioritize safest
    max_result_count = max(min_variety_count, min(len(safe_foods), min_variety_count * 2))
    result = safe_foods[:max_result_count]
    
    # Log final count
    if len(result) < min_variety_count:
        logger.warning(
            f"Category '{exchange_category}': Only {len(result)} foods available "
            f"(requested: {min_variety_count}). This may limit meal variety."
        )
    
    # Remove temporary metadata before returning
    for food_dict in result:
        food_dict.pop("_filtering_metadata", None)
        food_dict.pop("_safety_score", None)
    
    return result


def _build_food_dict(food: Any, nutrition: Dict[str, Any], mnt_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Build standardized food dictionary."""
    return {
        "food_id": food.food_id,
        "display_name": food.display_name,
        "aliases": list(food.aliases) if food.aliases else [],
        "category": food.category,
        "food_type": food.food_type,
        "region": food.region,
        "diet_type": list(food.diet_type) if food.diet_type else [],
        "cooking_state": food.cooking_state,
        "common_serving_unit": food.common_serving_unit,
        "common_serving_size_g": float(food.common_serving_size_g) if food.common_serving_size_g else None,
        "exchange_category": food.exchange_profile.exchange_category,
        "serving_size_per_exchange_g": float(food.exchange_profile.serving_size_per_exchange_g) if food.exchange_profile.serving_size_per_exchange_g else None,
        "exchanges_per_common_serving": float(food.exchange_profile.exchanges_per_common_serving) if food.exchange_profile.exchanges_per_common_serving else None,
        "nutrition": nutrition,
        "mnt_profile": mnt_profile,
    }


def _calculate_safety_score(
    food_dict: Dict[str, Any],
    medical_tags: Dict[str, bool],
    medical_conditions: List[str]
) -> float:
    """
    Calculate safety score for prioritization when relaxing constraints.
    Higher score = safer/more preferred.
    """
    score = 0.0
    
    # Condition to tag mapping
    condition_to_tag = {
        "type_2_diabetes": "diabetic_safe",
        "diabetes": "diabetic_safe",
        "prediabetes": "prediabetic_safe",
        "hypertension": "hypertension_safe",
        "obesity": "obesity_safe",
        "ckd": "renal_safe_stage_1_2",
        "cardiac": "cardiac_safe",
    }
    
    # Bonus for medical_tags matching conditions (high priority)
    for condition in medical_conditions:
        tag_key = condition_to_tag.get(condition.lower())
        if tag_key and medical_tags.get(tag_key, False):
            score += 100.0  # High bonus for condition-safe
    
    # Bonus for preferred conditions
    preferred = food_dict.get("mnt_profile", {}).get("preferred_conditions", [])
    for condition in medical_conditions:
        if condition.lower() in [p.lower() for p in preferred]:
            score += 50.0
    
    # Bonus for inclusion tags
    inclusion_tags = food_dict.get("mnt_profile", {}).get("food_inclusion_tags", [])
    score += len(inclusion_tags) * 10.0
    
    # Penalty for exclusion tags (but still included due to relaxation)
    exclusion_tags = food_dict.get("mnt_profile", {}).get("food_exclusion_tags", [])
    score -= len(exclusion_tags) * 5.0
    
    return score


def _sort_foods_by_safety_preference(
    foods: List[Dict[str, Any]],
    medical_conditions: List[str],
    mnt_context: MNTContext
) -> List[Dict[str, Any]]:
    """Sort foods by safety preference (safest first)."""
    scored_foods = []
    
    for food_dict in foods:
        medical_tags = food_dict.get("mnt_profile", {}).get("medical_tags", {})
        safety_score = _calculate_safety_score(food_dict, medical_tags, medical_conditions)
        scored_foods.append((food_dict, safety_score))
    
    # Sort by safety score (descending)
    scored_foods.sort(key=lambda x: x[1], reverse=True)
    
    return [food for food, _ in scored_foods]


def check_condition_compatibility(
    db: Session,
    food_id: str,
    medical_conditions: List[str],
    tier1_only: bool = True
) -> bool:
    """
    Check if food is compatible with medical conditions.
    
    Args:
        db: Database session
        food_id: Food ID to check
        medical_conditions: List of medical condition IDs
        tier1_only: If True, only exclude "contraindicated" (hard exclusion).
                    If False, also exclude "avoid" (soft exclusion for Tier 2).
        
    Returns:
        True if food is safe/compatible, False if contraindicated (or avoid if tier1_only=False)
        
    Note:
        - Tier 1 (Hard Exclusion): Only "contraindicated" foods are excluded
        - Tier 2 (Soft Constraint): "avoid" foods can be excluded but relaxed for variety
    """
    if not medical_conditions:
        return True
    
    # Query compatibility records
    compatibilities = db.query(KBFoodConditionCompatibility).filter(
        KBFoodConditionCompatibility.food_id == food_id,
        KBFoodConditionCompatibility.condition_id.in_(medical_conditions),
        KBFoodConditionCompatibility.status == 'active'
    ).all()
    
    # If no compatibility records exist, assume safe (default allow)
    if not compatibilities:
        return True
    
    # Check each condition
    for compat in compatibilities:
        compatibility_level = compat.compatibility.lower()
        
        # Tier 1: Only exclude "contraindicated" (hard medical safety)
        # "avoid" should be Tier 2 (soft constraint that can be relaxed for variety)
        if tier1_only:
            if compatibility_level == 'contraindicated':
                return False
        else:
            # Tier 2: Also exclude "avoid" (but this can be relaxed)
            if compatibility_level in ['contraindicated', 'avoid']:
                return False
        
        # Caution = allow but with restrictions (we allow it, handled in Tier 2)
        # Safe = allow
    
    return True


def get_category_wise_foods(
    db: Session,
    exchange_context: ExchangeContext,
    mnt_context: MNTContext,
    meal_name: str,
    ayurveda_preferences: Optional[Dict[str, Any]] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get foods grouped by exchange category for a specific meal.
    
    Args:
        db: Database session
        exchange_context: Exchange context with allocations per meal
        mnt_context: MNT context with constraints
        meal_name: Name of the meal (e.g., "breakfast", "lunch")
        ayurveda_preferences: Optional Ayurveda preferences
        
    Returns:
        Dictionary: {exchange_category: [food1, food2, ...], ...}
    """
    meal_exchanges = exchange_context.exchanges_per_meal.get(meal_name, {})
    category_wise_foods = {}
    
    medical_conditions = extract_medical_conditions(mnt_context)
    
    for exchange_category, exchange_count in meal_exchanges.items():
        if exchange_count > 0:
            foods = get_foods_by_exchange_category(
                db=db,
                exchange_category=exchange_category,
                mnt_context=mnt_context,
                medical_conditions=medical_conditions,
                ayurveda_preferences=ayurveda_preferences
            )
            category_wise_foods[exchange_category] = foods
    
    return category_wise_foods


def get_nutrition(food_id: str, db: Session) -> Dict[str, Any]:
    """
    Get nutrition data for a food ID from database.
    
    Args:
        food_id: Food ID
        db: Database session
        
    Returns:
        Nutrition dictionary or empty dict if not found
    """
    nutrition = db.query(KBFoodNutritionBase).filter(
        KBFoodNutritionBase.food_id == food_id
    ).first()
    
    return extract_nutrition(nutrition)


def list_food_ids(db: Session, exchange_category: Optional[str] = None) -> List[str]:
    """
    List all available food IDs from KB, optionally filtered by exchange category.
    
    Args:
        db: Database session
        exchange_category: Optional exchange category filter
        
    Returns:
        List of food IDs
    """
    query = db.query(KBFoodMaster.food_id).filter(
        KBFoodMaster.status == 'active'
    )
    
    if exchange_category:
        query = query.join(
            KBFoodExchangeProfile,
            KBFoodMaster.food_id == KBFoodExchangeProfile.food_id
        ).filter(
            KBFoodExchangeProfile.exchange_category == exchange_category
        )
    
    return [row[0] for row in query.all()]
