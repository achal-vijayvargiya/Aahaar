"""
Knowledge Base Meal Structure Rules for Meal Structure Engine.

Loads meal count rules, timing rules, calorie/protein allocation, macro guardrails, and validation thresholds from JSON knowledge base files.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional


# Cache for loaded KB data
_MEAL_COUNT_RULES_CACHE: Optional[List[Dict[str, Any]]] = None
_MEAL_TIMING_RULES_CACHE: Optional[Dict[str, Dict[str, Any]]] = None
_CALORIE_ALLOCATION_CACHE: Optional[Dict[str, Dict[str, Any]]] = None
_PROTEIN_DISTRIBUTION_CACHE: Optional[Dict[str, Dict[str, Any]]] = None
_MACRO_GUARDRAILS_CACHE: Optional[Dict[str, Dict[str, Any]]] = None
_VALIDATION_THRESHOLDS_CACHE: Optional[Dict[str, Dict[str, Any]]] = None


def _load_meal_count_rules() -> List[Dict[str, Any]]:
    """Load meal count rules from JSON KB file."""
    global _MEAL_COUNT_RULES_CACHE
    
    if _MEAL_COUNT_RULES_CACHE is not None:
        return _MEAL_COUNT_RULES_CACHE
    
    kb_path = Path(__file__).parent.parent.parent / "knowledge_base" / "meal_structure" / "meal_count_rules_kb.json"
    
    try:
        with open(kb_path, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
        
        active_rules = [r for r in kb_data if r.get("status") == "active"]
        _MEAL_COUNT_RULES_CACHE = active_rules
        return active_rules
    except FileNotFoundError:
        raise FileNotFoundError(f"Meal count rules KB file not found at: {kb_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in meal count rules KB: {e}")


def _load_meal_timing_rules() -> Dict[str, Dict[str, Any]]:
    """Load meal timing rules from JSON KB file."""
    global _MEAL_TIMING_RULES_CACHE
    
    if _MEAL_TIMING_RULES_CACHE is not None:
        return _MEAL_TIMING_RULES_CACHE
    
    kb_path = Path(__file__).parent.parent.parent / "knowledge_base" / "meal_structure" / "meal_timing_rules_kb.json"
    
    try:
        with open(kb_path, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
        
        rules_dict = {}
        for rule in kb_data:
            if rule.get("status") == "active":
                meal_type = rule.get("meal_type")
                if meal_type:
                    rules_dict[meal_type] = rule
        
        _MEAL_TIMING_RULES_CACHE = rules_dict
        return rules_dict
    except FileNotFoundError:
        raise FileNotFoundError(f"Meal timing rules KB file not found at: {kb_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in meal timing rules KB: {e}")


def _load_calorie_allocation() -> Dict[str, Dict[str, Any]]:
    """Load calorie allocation rules from JSON KB file."""
    global _CALORIE_ALLOCATION_CACHE
    
    if _CALORIE_ALLOCATION_CACHE is not None:
        return _CALORIE_ALLOCATION_CACHE
    
    kb_path = Path(__file__).parent.parent.parent / "knowledge_base" / "meal_structure" / "calorie_allocation_rules_kb.json"
    
    try:
        with open(kb_path, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
        
        rules_dict = {}
        for rule in kb_data:
            if rule.get("status") == "active":
                rule_id = rule.get("rule_id")
                if rule_id:
                    rules_dict[rule_id] = rule
        
        _CALORIE_ALLOCATION_CACHE = rules_dict
        return rules_dict
    except FileNotFoundError:
        raise FileNotFoundError(f"Calorie allocation rules KB file not found at: {kb_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in calorie allocation rules KB: {e}")


def _load_protein_distribution() -> Dict[str, Dict[str, Any]]:
    """Load protein distribution rules from JSON KB file."""
    global _PROTEIN_DISTRIBUTION_CACHE
    
    if _PROTEIN_DISTRIBUTION_CACHE is not None:
        return _PROTEIN_DISTRIBUTION_CACHE
    
    kb_path = Path(__file__).parent.parent.parent / "knowledge_base" / "meal_structure" / "protein_distribution_rules_kb.json"
    
    try:
        with open(kb_path, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
        
        rules_dict = {}
        for rule in kb_data:
            if rule.get("status") == "active":
                rule_id = rule.get("rule_id")
                if rule_id:
                    rules_dict[rule_id] = rule
        
        _PROTEIN_DISTRIBUTION_CACHE = rules_dict
        return rules_dict
    except FileNotFoundError:
        raise FileNotFoundError(f"Protein distribution rules KB file not found at: {kb_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in protein distribution rules KB: {e}")


def _load_macro_guardrails() -> Dict[str, Dict[str, Any]]:
    """Load macro guardrails from JSON KB file."""
    global _MACRO_GUARDRAILS_CACHE
    
    if _MACRO_GUARDRAILS_CACHE is not None:
        return _MACRO_GUARDRAILS_CACHE
    
    kb_path = Path(__file__).parent.parent.parent / "knowledge_base" / "meal_structure" / "macro_guardrails_kb.json"
    
    try:
        with open(kb_path, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
        
        rules_dict = {}
        for rule in kb_data:
            if rule.get("status") == "active":
                meal_type = rule.get("meal_type")
                if meal_type:
                    rules_dict[meal_type] = rule
        
        _MACRO_GUARDRAILS_CACHE = rules_dict
        return rules_dict
    except FileNotFoundError:
        raise FileNotFoundError(f"Macro guardrails KB file not found at: {kb_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in macro guardrails KB: {e}")


def _load_validation_thresholds() -> Dict[str, Dict[str, Any]]:
    """Load validation thresholds from JSON KB file."""
    global _VALIDATION_THRESHOLDS_CACHE
    
    if _VALIDATION_THRESHOLDS_CACHE is not None:
        return _VALIDATION_THRESHOLDS_CACHE
    
    kb_path = Path(__file__).parent.parent.parent / "knowledge_base" / "meal_structure" / "validation_thresholds_kb.json"
    
    try:
        with open(kb_path, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
        
        rules_dict = {}
        for rule in kb_data:
            if rule.get("status") == "active":
                rule_id = rule.get("validation_rule_id")
                if rule_id:
                    rules_dict[rule_id] = rule
        
        _VALIDATION_THRESHOLDS_CACHE = rules_dict
        return rules_dict
    except FileNotFoundError:
        raise FileNotFoundError(f"Validation thresholds KB file not found at: {kb_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in validation thresholds KB: {e}")


# --- Public API Functions ---

def get_meal_count_by_calories(calories_target: float) -> int:
    """Get meal count based on calorie target."""
    rules = _load_meal_count_rules()
    
    # Find default calorie-based rule
    calorie_rule = None
    for rule in rules:
        if rule.get("rule_type") == "calorie_based" and rule.get("is_default", False):
            calorie_rule = rule
            break
    
    if not calorie_rule:
        raise ValueError("Default meal count rule by calories not found in KB")
    
    calorie_ranges = calorie_rule.get("calorie_ranges", [])
    min_meals = calorie_rule.get("min_meals", 1)
    max_meals = calorie_rule.get("max_meals", 7)
    
    for range_def in calorie_ranges:
        min_cal = range_def.get("min")
        max_cal = range_def.get("max")
        meal_count = range_def.get("meal_count")
        
        if min_cal is None and max_cal is not None:
            if calories_target <= max_cal:
                return max(min_meals, min(max_meals, meal_count))
        elif min_cal is not None and max_cal is None:
            if calories_target >= min_cal:
                return max(min_meals, min(max_meals, meal_count))
        elif min_cal is not None and max_cal is not None:
            if min_cal <= calories_target <= max_cal:
                return max(min_meals, min(max_meals, meal_count))
    
    # Fallback to last range if no match
    if calorie_ranges:
        last_range = calorie_ranges[-1]
        return max(min_meals, min(max_meals, last_range.get("meal_count", 3)))
    
    raise ValueError("No matching calorie range found for meal count calculation")


def get_meal_count_by_fasting_window(fasting_window: str) -> Optional[int]:
    """Get meal count based on fasting window (e.g., '16:8')."""
    rules = _load_meal_count_rules()
    
    # Find fasting-based rule
    fasting_rule = None
    for rule in rules:
        if rule.get("rule_type") == "fasting_based":
            fasting_rule = rule
            break
    
    if not fasting_rule:
        return None
    
    try:
        parts = fasting_window.split(':')
        if len(parts) != 2:
            return None
        
        eating_hours = int(parts[1])
        fasting_rules = fasting_rule.get("fasting_window_rules", [])
        
        for rule_def in fasting_rules:
            min_hours = rule_def.get("eating_hours_min")
            max_hours = rule_def.get("eating_hours_max")
            meal_count = rule_def.get("meal_count")
            
            if min_hours is None and max_hours is not None:
                if eating_hours <= max_hours:
                    return meal_count
            elif min_hours is not None and max_hours is None:
                if eating_hours >= min_hours:
                    return meal_count
            elif min_hours is not None and max_hours is not None:
                if min_hours <= eating_hours <= max_hours:
                    return meal_count
        
        return None
    except (ValueError, IndexError):
        return None


def get_meal_timing_rule(meal_type: str) -> Optional[Dict[str, Any]]:
    """Get timing rule for a meal type."""
    rules = _load_meal_timing_rules()
    
    # Try exact match first
    if meal_type in rules:
        return rules[meal_type]
    
    # Try partial match (e.g., "snack1" -> "snack")
    for key, rule in rules.items():
        if key in meal_type.lower() or meal_type.lower() in key:
            return rule
    
    # Return default if available
    return rules.get("default")


def get_default_calorie_allocation() -> Dict[str, Any]:
    """Get default calorie allocation rule."""
    rules = _load_calorie_allocation()
    
    for rule in rules.values():
        if rule.get("is_default", False):
            return rule
    
    # Return first rule if no default
    if rules:
        return list(rules.values())[0]
    
    raise ValueError("No calorie allocation rule found in KB")


def get_calorie_allocation_by_context(
    medical_conditions: Optional[List[str]] = None,
    goals: Optional[Dict[str, Any]] = None,
    activity_level: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get calorie allocation rule based on medical conditions, goals, and activity level.
    
    Priority order:
    1. Medical conditions (diabetes, GERD, etc.)
    2. Goals (weight_loss, muscle_gain, etc.)
    3. Activity level (athletes, very_active)
    4. Default rule
    
    Args:
        medical_conditions: List of medical condition strings (e.g., ["diabetes", "gerd"])
        goals: Goals dictionary with primary_goal and secondary_goals
        activity_level: Activity level string (e.g., "very_active", "athletes")
        
    Returns:
        Calorie allocation rule dictionary
    """
    rules = _load_calorie_allocation()
    
    # Build list of conditions to match against
    match_conditions = []
    
    # Add medical conditions
    if medical_conditions:
        for condition in medical_conditions:
            if isinstance(condition, str):
                match_conditions.append(condition.lower())
            elif isinstance(condition, dict):
                # Handle diagnosis dict format
                diagnosis_id = condition.get("diagnosis_id", "")
                if diagnosis_id:
                    match_conditions.append(diagnosis_id.lower())
    
    # Add goals
    if goals:
        primary_goal = goals.get("primary_goal")
        if primary_goal:
            match_conditions.append(str(primary_goal).lower())
        
        secondary_goals = goals.get("secondary_goals", [])
        if isinstance(secondary_goals, list):
            for goal in secondary_goals:
                if goal:
                    match_conditions.append(str(goal).lower())
    
    # Add activity level
    if activity_level:
        match_conditions.append(str(activity_level).lower())
    
    # Try to find matching rule (priority: medical conditions > goals > activity)
    # Check all non-default rules for matches
    for rule in rules.values():
        if rule.get("is_default", False):
            continue  # Skip default rule
        
        applies_to = rule.get("applies_to", [])
        if not applies_to:
            continue
        
        # Check if any condition matches any applies_to item
        for condition in match_conditions:
            for applies_item in applies_to:
                applies_item_lower = str(applies_item).lower()
                # Match if exact match or substring match (handles variations like "type_2_diabetes" vs "diabetes")
                if condition == applies_item_lower or condition in applies_item_lower or applies_item_lower in condition:
                    return rule  # Found match
    
    # Fallback to default
    return get_default_calorie_allocation()


def get_default_protein_distribution() -> Dict[str, Any]:
    """Get default protein distribution rule."""
    rules = _load_protein_distribution()
    
    for rule in rules.values():
        if rule.get("is_default", False):
            return rule
    
    # Return first rule if no default
    if rules:
        return list(rules.values())[0]
    
    raise ValueError("No protein distribution rule found in KB")


def get_protein_distribution_by_context(
    medical_conditions: Optional[List[str]] = None,
    goals: Optional[Dict[str, Any]] = None,
    activity_level: Optional[str] = None,
    age: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get protein distribution rule based on medical conditions, goals, activity level, and age.
    
    Priority order:
    1. Medical conditions (elderly/age-based)
    2. Goals (weight_loss, muscle_gain, etc.)
    3. Activity level (athletes, very_active)
    4. Default rule
    
    Args:
        medical_conditions: List of medical condition strings (e.g., ["diabetes", "gerd"])
        goals: Goals dictionary with primary_goal and secondary_goals
        activity_level: Activity level string (e.g., "very_active", "athletes")
        age: Age in years (for elderly rule: age >= 65)
        
    Returns:
        Protein distribution rule dictionary
    """
    rules = _load_protein_distribution()
    
    # Build list of conditions to match against
    match_conditions = []
    
    # Add age-based condition for elderly
    if age is not None and age >= 65:
        match_conditions.append("elderly")
        match_conditions.append("age_over_65")
    
    # Add medical conditions
    if medical_conditions:
        for condition in medical_conditions:
            if isinstance(condition, str):
                match_conditions.append(condition.lower())
            elif isinstance(condition, dict):
                # Handle diagnosis dict format
                diagnosis_id = condition.get("diagnosis_id", "")
                if diagnosis_id:
                    match_conditions.append(diagnosis_id.lower())
    
    # Add goals
    if goals:
        primary_goal = goals.get("primary_goal")
        if primary_goal:
            match_conditions.append(str(primary_goal).lower())
        
        secondary_goals = goals.get("secondary_goals", [])
        if isinstance(secondary_goals, list):
            for goal in secondary_goals:
                if goal:
                    match_conditions.append(str(goal).lower())
    
    # Add activity level
    if activity_level:
        match_conditions.append(str(activity_level).lower())
    
    # Try to find matching rule (priority: age/medical conditions > goals > activity)
    # Check all non-default rules for matches
    for rule in rules.values():
        if rule.get("is_default", False):
            continue  # Skip default rule
        
        applies_to = rule.get("applies_to", [])
        if not applies_to:
            continue
        
        # Check if any condition matches any applies_to item
        for condition in match_conditions:
            for applies_item in applies_to:
                applies_item_lower = str(applies_item).lower()
                # Match if exact match or substring match (handles variations)
                if condition == applies_item_lower or condition in applies_item_lower or applies_item_lower in condition:
                    return rule  # Found match
    
    # Fallback to default
    return get_default_protein_distribution()


def get_macro_guardrails(meal_type: str) -> Optional[Dict[str, List[float]]]:
    """Get macro guardrails for a meal type."""
    rules = _load_macro_guardrails()
    
    # Try exact match first
    if meal_type in rules:
        return rules[meal_type].get("macro_guardrails")
    
    # Try partial match
    meal_lower = meal_type.lower()
    for key, rule in rules.items():
        if key in meal_lower or meal_lower in key:
            return rule.get("macro_guardrails")
    
    # Return default
    default_rule = rules.get("default")
    if default_rule:
        return default_rule.get("macro_guardrails")
    
    return None


def get_validation_threshold(rule_id: str) -> Optional[Dict[str, Any]]:
    """Get validation threshold by rule ID."""
    thresholds = _load_validation_thresholds()
    return thresholds.get(rule_id)


def get_calorie_tolerance() -> float:
    """Get calorie tolerance percentage."""
    threshold = get_validation_threshold("calorie_tolerance")
    if threshold:
        return threshold.get("tolerance_value", 5.0)
    return 5.0  # Fallback


def get_protein_sufficiency_threshold() -> float:
    """Get protein sufficiency threshold percentage."""
    threshold = get_validation_threshold("protein_sufficiency")
    if threshold:
        return threshold.get("min_sufficiency_percent", 95.0)
    return 95.0  # Fallback


def get_dinner_before_sleep_hours() -> float:
    """Get minimum hours before sleep for dinner."""
    threshold = get_validation_threshold("dinner_timing")
    if threshold:
        return threshold.get("min_hours_before_sleep", 3.0)
    return 3.0  # Fallback

