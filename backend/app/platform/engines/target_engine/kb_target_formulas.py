"""
Knowledge Base Target Formulas for Target Engine.

Loads BMR/TDEE formulas, activity multipliers, macro distribution rules, and micro targets from JSON knowledge base files.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional


# Cache for loaded KB data
_BMR_FORMULAS_CACHE: Optional[List[Dict[str, Any]]] = None
_ACTIVITY_MULTIPLIERS_CACHE: Optional[Dict[str, Dict[str, Any]]] = None
_MACRO_DISTRIBUTION_CACHE: Optional[Dict[str, Dict[str, Any]]] = None
_MICRO_TARGETS_CACHE: Optional[Dict[str, Dict[str, Any]]] = None


def _load_bmr_formulas() -> List[Dict[str, Any]]:
    """
    Load BMR/TDEE formulas from JSON knowledge base file.
    
    Returns:
        List of BMR formula definitions
    """
    global _BMR_FORMULAS_CACHE
    
    if _BMR_FORMULAS_CACHE is not None:
        return _BMR_FORMULAS_CACHE
    
    kb_path = Path(__file__).parent.parent.parent / "knowledge_base" / "target_formulas" / "bmr_tdee_formulas_kb.json"
    
    try:
        with open(kb_path, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
        
        # Filter only active formulas
        active_formulas = [f for f in kb_data if f.get("status") == "active"]
        _BMR_FORMULAS_CACHE = active_formulas
        
        return active_formulas
    except FileNotFoundError:
        raise FileNotFoundError(
            f"BMR/TDEE formulas KB file not found at: {kb_path}\n"
            "Please ensure the knowledge base file exists."
        )
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in BMR/TDEE formulas KB: {e}")


def _load_activity_multipliers() -> Dict[str, Dict[str, Any]]:
    """
    Load activity multipliers from JSON knowledge base file.
    
    Returns:
        Dictionary of activity multipliers keyed by multiplier_id
    """
    global _ACTIVITY_MULTIPLIERS_CACHE
    
    if _ACTIVITY_MULTIPLIERS_CACHE is not None:
        return _ACTIVITY_MULTIPLIERS_CACHE
    
    kb_path = Path(__file__).parent.parent.parent / "knowledge_base" / "target_formulas" / "activity_multipliers_kb.json"
    
    try:
        with open(kb_path, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
        
        # Convert list to dictionary keyed by multiplier_id
        # Filter only active multipliers
        multipliers_dict = {}
        for multiplier in kb_data:
            if multiplier.get("status") == "active":
                multiplier_id = multiplier.get("multiplier_id")
                if multiplier_id:
                    multipliers_dict[multiplier_id] = multiplier
        
        _ACTIVITY_MULTIPLIERS_CACHE = multipliers_dict
        
        return multipliers_dict
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Activity multipliers KB file not found at: {kb_path}\n"
            "Please ensure the knowledge base file exists."
        )
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in activity multipliers KB: {e}")


def _load_macro_distribution() -> Dict[str, Dict[str, Any]]:
    """
    Load macro distribution rules from JSON knowledge base file.
    
    Returns:
        Dictionary of macro distribution rules keyed by rule_id
    """
    global _MACRO_DISTRIBUTION_CACHE
    
    if _MACRO_DISTRIBUTION_CACHE is not None:
        return _MACRO_DISTRIBUTION_CACHE
    
    kb_path = Path(__file__).parent.parent.parent / "knowledge_base" / "target_formulas" / "macro_distribution_rules_kb.json"
    
    try:
        with open(kb_path, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
        
        # Convert list to dictionary keyed by rule_id
        # Filter only active rules
        rules_dict = {}
        for rule in kb_data:
            if rule.get("status") == "active":
                rule_id = rule.get("rule_id")
                if rule_id:
                    rules_dict[rule_id] = rule
        
        _MACRO_DISTRIBUTION_CACHE = rules_dict
        
        return rules_dict
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Macro distribution rules KB file not found at: {kb_path}\n"
            "Please ensure the knowledge base file exists."
        )
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in macro distribution rules KB: {e}")


def _load_micro_targets() -> Dict[str, Dict[str, Any]]:
    """
    Load micro target standards from JSON knowledge base file.
    
    Returns:
        Dictionary of micro targets keyed by nutrient_id
    """
    global _MICRO_TARGETS_CACHE
    
    if _MICRO_TARGETS_CACHE is not None:
        return _MICRO_TARGETS_CACHE
    
    kb_path = Path(__file__).parent.parent.parent / "knowledge_base" / "target_formulas" / "micro_target_standards_kb.json"
    
    try:
        with open(kb_path, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
        
        # Convert list to dictionary keyed by nutrient_id
        # Filter only active nutrients
        targets_dict = {}
        for nutrient in kb_data:
            if nutrient.get("status") == "active":
                nutrient_id = nutrient.get("nutrient_id")
                if nutrient_id:
                    targets_dict[nutrient_id] = nutrient
        
        _MICRO_TARGETS_CACHE = targets_dict
        
        return targets_dict
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Micro target standards KB file not found at: {kb_path}\n"
            "Please ensure the knowledge base file exists."
        )
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in micro target standards KB: {e}")


def get_default_bmr_formula() -> Optional[Dict[str, Any]]:
    """
    Get the default BMR formula (marked with is_default: true).
    
    Returns:
        Default BMR formula dictionary or None if not found
    """
    formulas = _load_bmr_formulas()
    for formula in formulas:
        if formula.get("is_default", False):
            return formula
    
    # Fallback to first active formula if no default
    return formulas[0] if formulas else None


def get_bmr_formula(formula_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get BMR formula by ID, or return default if not specified.
    
    Args:
        formula_id: Formula identifier (optional)
        
    Returns:
        BMR formula dictionary or None if not found
    """
    formulas = _load_bmr_formulas()
    
    if formula_id:
        for formula in formulas:
            if formula.get("formula_id") == formula_id:
                return formula
        return None
    
    # Return default if no formula_id specified
    return get_default_bmr_formula()


def get_activity_multiplier(activity_level: Optional[str]) -> Optional[float]:
    """
    Get activity multiplier value for a given activity level.
    
    Args:
        activity_level: Activity level string (e.g., "sedentary", "moderately_active")
        
    Returns:
        Activity multiplier value or None if not found
    """
    multipliers = _load_activity_multipliers()
    
    if activity_level is None:
        # Find default multiplier
        for mult in multipliers.values():
            if mult.get("is_default", False):
                return mult.get("multiplier_value")
        # Return None if no default found
        return None
    
    multiplier_data = multipliers.get(activity_level)
    if multiplier_data:
        return multiplier_data.get("multiplier_value")
    
    # Return None if not found
    return None


def get_default_macro_distribution() -> Optional[Dict[str, Any]]:
    """
    Get the default macro distribution rule (marked with is_default: true).
    
    Returns:
        Default macro distribution rule dictionary or None if not found
    """
    rules = _load_macro_distribution()
    for rule in rules.values():
        if rule.get("is_default", False):
            return rule
    
    # Fallback to first active rule if no default
    return list(rules.values())[0] if rules else None


def get_macro_distribution_rule(rule_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get macro distribution rule by ID, or return default if not specified.
    
    Args:
        rule_id: Rule identifier (optional)
        
    Returns:
        Macro distribution rule dictionary or None if not found
    """
    rules = _load_macro_distribution()
    
    if rule_id:
        return rules.get(rule_id)
    
    # Return default if no rule_id specified
    return get_default_macro_distribution()


def get_micro_target(nutrient_id: str, gender: Optional[str] = None, age: Optional[int] = None, conditions: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """
    Get micro target for a specific nutrient with age/gender/condition adjustments.
    
    Args:
        nutrient_id: Nutrient identifier (e.g., "fiber_g", "sodium_mg")
        gender: Gender string (optional, for gender-specific targets)
        age: Age in years (optional, for age-specific adjustments)
        conditions: List of medical conditions (optional, for condition-specific adjustments)
        
    Returns:
        Dictionary with min/max values for the nutrient, or None if not found
    """
    targets = _load_micro_targets()
    nutrient_data = targets.get(nutrient_id)
    
    if not nutrient_data:
        return None
    
    # Start with default targets
    default_targets = nutrient_data.get("default_targets", {})
    result = {}
    
    # Determine base target based on gender and age
    gender_lower = (gender or "").lower()
    
    if gender_lower in ["male", "m"]:
        if age and age >= 51:
            base_key = "adult_male_51_plus"
        else:
            base_key = "adult_male"
    elif gender_lower in ["female", "f"]:
        if age and age >= 51:
            base_key = "adult_female_51_plus"
        elif age and age >= 19:
            base_key = "adult_female_19_50"
        else:
            base_key = "adult_female"
    else:
        base_key = "general" if "general" in default_targets else "adult"
    
    # Get base target
    base_target = default_targets.get(base_key, {})
    if base_target:
        result.update(base_target)
    
    # Apply age adjustments
    age_adjustments = nutrient_data.get("age_adjustments", {})
    if age:
        if age >= 50 and "over_50" in age_adjustments:
            adj = age_adjustments["over_50"]
            for key, value in adj.items():
                if key in ["min", "max"]:
                    result[key] = value
        if age >= 70 and "over_70" in age_adjustments:
            adj = age_adjustments["over_70"]
            for key, value in adj.items():
                if key in ["min", "max"]:
                    result[key] = value
        if gender_lower in ["female", "f"] and age >= 50 and "female_over_50" in age_adjustments:
            adj = age_adjustments["female_over_50"]
            for key, value in adj.items():
                if key in ["min", "max"]:
                    result[key] = value
    
    # Apply condition adjustments
    condition_adjustments = nutrient_data.get("condition_adjustments", {})
    if conditions:
        for condition in conditions:
            if condition in condition_adjustments:
                adj = condition_adjustments[condition]
                for key, value in adj.items():
                    if key in ["min", "max"]:
                        # Take more restrictive (higher min, lower max)
                        if key == "min":
                            result[key] = max(result.get(key, value), value)
                        elif key == "max":
                            result[key] = min(result.get(key, value), value) if result.get(key) else value
    
    return result if result else None


def get_all_active_nutrient_ids() -> List[str]:
    """
    Get list of all active nutrient IDs from micro targets KB.
    
    Returns:
        List of nutrient IDs (e.g., ["fiber_g", "sodium_mg", ...])
    """
    targets = _load_micro_targets()
    return list(targets.keys())


def get_default_calorie_fallback() -> float:
    """
    Get default calorie fallback value from KB or return standard default.
    
    Returns:
        Default calorie value (typically 2000)
    """
    # For now, return standard default. Can be moved to KB later if needed.
    # This is a safety fallback when BMR/TDEE cannot be calculated.
    return 2000.0

