"""
Exchange System Knowledge Base Loader.

Loads exchange category definitions, allocation rules, medical/Ayurveda modifiers,
and exchange limits from JSON KB files.
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Cache for loaded KB data
_EXCHANGE_CATEGORY_CACHE: Optional[List[Dict[str, Any]]] = None
_EXCHANGE_ALLOCATION_RULES_CACHE: Optional[List[Dict[str, Any]]] = None
_MEDICAL_MODIFIER_RULES_CACHE: Optional[List[Dict[str, Any]]] = None
_AYURVEDA_MODIFIER_RULES_CACHE: Optional[List[Dict[str, Any]]] = None
_EXCHANGE_LIMITS_CACHE: Optional[List[Dict[str, Any]]] = None
_MANDATORY_PRESENCE_CONSTRAINTS_CACHE: Optional[List[Dict[str, Any]]] = None
_NUTRITION_VALIDATION_TOLERANCES_CACHE: Optional[List[Dict[str, Any]]] = None
_CORE_FOOD_GROUPS_CACHE: Optional[List[Dict[str, Any]]] = None
_EXCHANGE_EXCLUSION_CONSTRAINTS_CACHE: Optional[List[Dict[str, Any]]] = None
_EXCHANGE_ROUNDING_RULES_CACHE: Optional[List[Dict[str, Any]]] = None


def _get_kb_path(filename: str) -> Path:
    """Get path to KB JSON file."""
    return Path(__file__).parent.parent.parent / "knowledge_base" / "exchange_system" / filename


def _load_exchange_categories() -> List[Dict[str, Any]]:
    """Load exchange category definitions from KB."""
    global _EXCHANGE_CATEGORY_CACHE
    if _EXCHANGE_CATEGORY_CACHE is not None:
        return _EXCHANGE_CATEGORY_CACHE
    
    kb_path = _get_kb_path("exchange_category_definitions_kb.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Filter only active categories
    _EXCHANGE_CATEGORY_CACHE = [cat for cat in data if cat.get("status") == "active"]
    return _EXCHANGE_CATEGORY_CACHE


def _load_exchange_allocation_rules() -> List[Dict[str, Any]]:
    """Load exchange allocation rules from KB."""
    global _EXCHANGE_ALLOCATION_RULES_CACHE
    if _EXCHANGE_ALLOCATION_RULES_CACHE is not None:
        return _EXCHANGE_ALLOCATION_RULES_CACHE
    
    kb_path = _get_kb_path("exchange_allocation_rules_kb.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Filter only active rules
    _EXCHANGE_ALLOCATION_RULES_CACHE = [rule for rule in data if rule.get("status") == "active"]
    return _EXCHANGE_ALLOCATION_RULES_CACHE


def _load_medical_modifier_rules() -> List[Dict[str, Any]]:
    """Load medical modifier rules from KB."""
    global _MEDICAL_MODIFIER_RULES_CACHE
    if _MEDICAL_MODIFIER_RULES_CACHE is not None:
        return _MEDICAL_MODIFIER_RULES_CACHE
    
    kb_path = _get_kb_path("medical_modifier_rules_kb.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Filter only active rules
    _MEDICAL_MODIFIER_RULES_CACHE = [rule for rule in data if rule.get("status") == "active"]
    return _MEDICAL_MODIFIER_RULES_CACHE


def _load_ayurveda_modifier_rules() -> List[Dict[str, Any]]:
    """Load Ayurveda modifier rules from KB."""
    global _AYURVEDA_MODIFIER_RULES_CACHE
    if _AYURVEDA_MODIFIER_RULES_CACHE is not None:
        return _AYURVEDA_MODIFIER_RULES_CACHE
    
    kb_path = _get_kb_path("ayurveda_modifier_rules_kb.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Filter only active rules
    _AYURVEDA_MODIFIER_RULES_CACHE = [rule for rule in data if rule.get("status") == "active"]
    return _AYURVEDA_MODIFIER_RULES_CACHE


def _load_exchange_limits() -> List[Dict[str, Any]]:
    """Load exchange limits from KB."""
    global _EXCHANGE_LIMITS_CACHE
    if _EXCHANGE_LIMITS_CACHE is not None:
        return _EXCHANGE_LIMITS_CACHE
    
    kb_path = _get_kb_path("exchange_limits_kb.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Filter only active rules
    _EXCHANGE_LIMITS_CACHE = [rule for rule in data if rule.get("status") == "active"]
    return _EXCHANGE_LIMITS_CACHE


def get_exchange_category(category_id: str) -> Optional[Dict[str, Any]]:
    """
    Get exchange category definition by ID.
    
    Args:
        category_id: Exchange category ID (e.g., "cereal", "pulse")
        
    Returns:
        Category definition dictionary or None if not found
    """
    categories = _load_exchange_categories()
    for cat in categories:
        if cat.get("exchange_category_id") == category_id:
            return cat
    return None


def get_all_exchange_categories() -> List[Dict[str, Any]]:
    """Get all active exchange category definitions."""
    return _load_exchange_categories()


def get_exchange_nutrition(category_id: str) -> Dict[str, float]:
    """
    Get nutrition values per exchange for a category.
    
    First checks core_food_groups_kb.json, then falls back to exchange_category_definitions_kb.json.
    
    Args:
        category_id: Exchange category ID
        
    Returns:
        Dictionary with calories, protein_g, carbs_g, fat_g
    """
    # First check core_food_groups_kb.json
    config = get_core_food_groups()
    if config:
        core_groups = config.get("core_food_groups", [])
        for group in core_groups:
            if group.get("exchange_category_id") == category_id:
                nutrition = group.get("nutrition_per_exchange", {})
                if nutrition:
                    return nutrition.copy()
    
    # Fallback to exchange_category_definitions_kb.json
    category = get_exchange_category(category_id)
    if not category:
        return {}
    return category.get("nutrition_per_exchange", {}).copy()


def get_exchange_amount(category_id: str) -> float:
    """
    Get amount in grams per exchange for a category.
    
    First checks core_food_groups_kb.json, then falls back to exchange_category_definitions_kb.json.
    
    Args:
        category_id: Exchange category ID
        
    Returns:
        Amount in grams per exchange, or 0.0 if not found
    """
    # First check core_food_groups_kb.json
    config = get_core_food_groups()
    if config:
        core_groups = config.get("core_food_groups", [])
        for group in core_groups:
            if group.get("exchange_category_id") == category_id:
                amount = group.get("amount_per_exchange_g")
                if amount is not None:
                    return float(amount)
    
    # Fallback to exchange_category_definitions_kb.json
    category = get_exchange_category(category_id)
    if not category:
        return 0.0
    return category.get("amount_per_exchange_g", 0.0)


def get_allocation_rule(rule_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get exchange allocation rule by ID, or default rule.
    
    Args:
        rule_id: Rule ID (e.g., "protein_first_allocation")
        
    Returns:
        Allocation rule dictionary or None if not found
    """
    rules = _load_exchange_allocation_rules()
    
    if rule_id:
        for rule in rules:
            if rule.get("rule_id") == rule_id:
                return rule
        return None
    
    # Return default rule if no ID specified
    for rule in rules:
        if rule.get("is_default"):
            return rule
    
    # Return first rule if no default
    return rules[0] if rules else None


def get_vegetable_floor_rule() -> Optional[Dict[str, Any]]:
    """Get vegetable floor rule."""
    return get_allocation_rule("vegetable_floor_rule")


def get_medical_modifier_for_condition(condition: str) -> Optional[Dict[str, Any]]:
    """
    Get medical modifier rule for a given condition.
    
    Args:
        condition: Medical condition name (e.g., "diabetes", "ckd")
        
    Returns:
        Medical modifier rule dictionary or None if not found
    """
    rules = _load_medical_modifier_rules()
    condition_lower = condition.lower()
    
    for rule in rules:
        applies_to = rule.get("applies_to_conditions", [])
        for cond in applies_to:
            if condition_lower in cond.lower() or cond.lower() in condition_lower:
                return rule
    
    return None


def _load_mandatory_presence_constraints() -> List[Dict[str, Any]]:
    """Load mandatory presence constraints from KB."""
    global _MANDATORY_PRESENCE_CONSTRAINTS_CACHE
    if _MANDATORY_PRESENCE_CONSTRAINTS_CACHE is not None:
        return _MANDATORY_PRESENCE_CONSTRAINTS_CACHE
    
    kb_path = _get_kb_path("mandatory_presence_constraints_kb.json")
    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _MANDATORY_PRESENCE_CONSTRAINTS_CACHE = [rule for rule in data if rule.get("status") == "active"]
    except FileNotFoundError:
        _MANDATORY_PRESENCE_CONSTRAINTS_CACHE = []
    
    return _MANDATORY_PRESENCE_CONSTRAINTS_CACHE


def _load_nutrition_validation_tolerances() -> List[Dict[str, Any]]:
    """Load nutrition validation tolerances from KB."""
    global _NUTRITION_VALIDATION_TOLERANCES_CACHE
    if _NUTRITION_VALIDATION_TOLERANCES_CACHE is not None:
        return _NUTRITION_VALIDATION_TOLERANCES_CACHE
    
    kb_path = _get_kb_path("nutrition_validation_tolerances_kb.json")
    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _NUTRITION_VALIDATION_TOLERANCES_CACHE = [rule for rule in data if rule.get("status") == "active"]
    except FileNotFoundError:
        _NUTRITION_VALIDATION_TOLERANCES_CACHE = []
    
    return _NUTRITION_VALIDATION_TOLERANCES_CACHE


def get_ayurveda_modifier_for_dosha(dosha: str) -> Optional[Dict[str, Any]]:
    """
    Get Ayurveda modifier rule for a given dosha.
    
    Args:
        dosha: Dosha name (e.g., "Vata", "Pitta", "Kapha")
        
    Returns:
        Ayurveda modifier rule dictionary or None if not found
    """
    rules = _load_ayurveda_modifier_rules()
    
    for rule in rules:
        applies_to = rule.get("applies_to", [])
        if dosha in applies_to:
            return rule
    
    return None


def get_ayurveda_modifier_for_agni(agni: str) -> Optional[Dict[str, Any]]:
    """
    Get Ayurveda modifier rule for a given agni type.
    
    Args:
        agni: Agni type (e.g., "Manda")
        
    Returns:
        Ayurveda modifier rule dictionary or None if not found
    """
    rules = _load_ayurveda_modifier_rules()
    
    for rule in rules:
        if rule.get("modifier_type") == "agni" and rule.get("applies_to", []) == [agni]:
            return rule
    
    return None


def get_ayurveda_modifier_for_ama(ama: str) -> Optional[Dict[str, Any]]:
    """
    Get Ayurveda modifier rule for a given ama level.
    
    Args:
        ama: Ama level (e.g., "high")
        
    Returns:
        Ayurveda modifier rule dictionary or None if not found
    """
    rules = _load_ayurveda_modifier_rules()
    
    for rule in rules:
        if rule.get("modifier_type") == "ama" and ama in rule.get("applies_to", []):
            return rule
    
    return None


def get_exchange_limits(rule_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get exchange limits rule by ID, or default rule.
    
    Args:
        rule_id: Rule ID (e.g., "exchange_limits_per_meal")
        
    Returns:
        Exchange limits rule dictionary or None if not found
    """
    rules = _load_exchange_limits()
    
    if rule_id:
        for rule in rules:
            if rule.get("rule_id") == rule_id:
                return rule
        return None
    
    # Return default rule if no ID specified
    for rule in rules:
        if rule.get("is_default"):
            return rule
    
    # Return first rule if no default
    return rules[0] if rules else None


def get_allocation_thresholds() -> Optional[Dict[str, Any]]:
    """Get allocation thresholds (protein, calorie thresholds)."""
    rules = _load_exchange_limits()
    
    for rule in rules:
        if rule.get("rule_id") == "allocation_thresholds":
            return rule.get("thresholds", {})
    
    return None

# TODO need to check if meal_name coming hear is matches with kb keys like breakfast, lunch, dinner, snack, etc.
def get_exchange_limits_for_meal(meal_name: str) -> Optional[Dict[str, Dict[str, int]]]:
    """
    Get exchange limits (min/max) for a specific meal type.
    
    Args:
        meal_name: Name of the meal (e.g., "breakfast", "lunch", "dinner")
        
    Returns:
        Dictionary mapping category -> {"min": int, "max": int}, or None if not found
    """
    limits_rule = get_exchange_limits("exchange_limits_per_meal")
    if not limits_rule:
        return None
    
    meal_type_limits = limits_rule.get("meal_type_limits", {})
    meal_type_lower = meal_name.lower()
    
    # Try exact match first
    if meal_type_lower in meal_type_limits:
        return meal_type_limits[meal_type_lower]
    
    # Try partial match (e.g., "snack1" -> "snack")
    for meal_type, limits in meal_type_limits.items():
        if meal_type.lower() in meal_type_lower or meal_type_lower in meal_type.lower():
            return limits
    
    return None


def get_mandatory_presence_constraints() -> Optional[Dict[str, Any]]:
    """
    Get mandatory presence constraints rule.
    
    Returns:
        Mandatory presence constraints rule dictionary or None if not found
    """
    rules = _load_mandatory_presence_constraints()
    
    # Return default rule
    for rule in rules:
        if rule.get("is_default"):
            return rule
    
    # Return first rule if no default
    return rules[0] if rules else None


def get_nutrition_validation_tolerances() -> Optional[Dict[str, Any]]:
    """
    Get nutrition validation tolerances rule.
    
    Returns:
        Nutrition validation tolerances rule dictionary or None if not found
    """
    rules = _load_nutrition_validation_tolerances()
    
    # Return default rule
    for rule in rules:
        if rule.get("is_default"):
            return rule
    
    # Return first rule if no default
    return rules[0] if rules else None


def _load_core_food_groups() -> List[Dict[str, Any]]:
    """Load core food groups configuration from KB."""
    global _CORE_FOOD_GROUPS_CACHE
    if _CORE_FOOD_GROUPS_CACHE is not None:
        return _CORE_FOOD_GROUPS_CACHE
    
    kb_path = _get_kb_path("core_food_groups_kb.json")
    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _CORE_FOOD_GROUPS_CACHE = [rule for rule in data if rule.get("status") == "active"]
    except FileNotFoundError:
        _CORE_FOOD_GROUPS_CACHE = []
    
    return _CORE_FOOD_GROUPS_CACHE


def get_core_food_groups() -> Optional[Dict[str, Any]]:
    """
    Get core food groups configuration.
    
    Returns:
        Core food groups configuration dictionary or None if not found
    """
    rules = _load_core_food_groups()
    
    # Return default rule
    for rule in rules:
        if rule.get("is_default"):
            return rule
    
    # Return first rule if no default
    return rules[0] if rules else None


def _load_exchange_exclusion_constraints() -> List[Dict[str, Any]]:
    """Load exchange exclusion constraints from KB."""
    global _EXCHANGE_EXCLUSION_CONSTRAINTS_CACHE
    if _EXCHANGE_EXCLUSION_CONSTRAINTS_CACHE is not None:
        return _EXCHANGE_EXCLUSION_CONSTRAINTS_CACHE
    
    kb_path = _get_kb_path("exchange_exclusion_constraints_kb.json")
    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _EXCHANGE_EXCLUSION_CONSTRAINTS_CACHE = [rule for rule in data if rule.get("status") == "active"]
    except FileNotFoundError:
        _EXCHANGE_EXCLUSION_CONSTRAINTS_CACHE = []
    
    return _EXCHANGE_EXCLUSION_CONSTRAINTS_CACHE


def get_exchange_exclusion_constraints() -> Optional[Dict[str, Any]]:
    """
    Get exchange exclusion constraints rule.
    
    Returns:
        Exchange exclusion constraints rule dictionary or None if not found
    """
    rules = _load_exchange_exclusion_constraints()
    
    # Return default rule
    for rule in rules:
        if rule.get("is_default"):
            return rule
    
    # Return first rule if no default
    return rules[0] if rules else None


def get_exclusion_rule_for_category(category_id: str) -> Optional[Dict[str, Any]]:
    """
    Get exclusion rule for a specific exchange category.
    
    Args:
        category_id: Exchange category ID (e.g., "milk")
        
    Returns:
        Exclusion rule dictionary for the category or None if not found
    """
    constraints_rule = get_exchange_exclusion_constraints()
    if not constraints_rule:
        return None
    
    exclusion_rules = constraints_rule.get("exclusion_rules", [])
    for rule in exclusion_rules:
        if rule.get("exchange_category_id") == category_id:
            return rule
    
    return None


def get_food_group_display_order() -> List[str]:
    """
    Get ordered list of food group category IDs based on display_order from KB.
    
    Returns:
        List of category IDs in display order
    """
    config = get_core_food_groups()
    if not config:
        # Fallback: return empty list if KB not found
        return []
    
    core_groups = config.get("core_food_groups", [])
    
    # Sort by display_order
    sorted_groups = sorted(core_groups, key=lambda x: x.get("display_order", 9999))
    
    # Extract category IDs
    return [group.get("exchange_category_id") for group in sorted_groups if group.get("exchange_category_id")]


