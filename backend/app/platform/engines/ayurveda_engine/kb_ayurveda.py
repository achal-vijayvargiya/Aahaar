"""
Ayurveda Knowledge Base Loader.

Loads Prakriti/Vikriti scoring rules, Agni/Ama assessment rules,
dosha food qualities, meal timing, cooking methods, portion guidance,
and Ayurveda profiles from JSON KB files.
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Cache for loaded KB data
_PRAKRITI_SCORING_CACHE: Optional[List[Dict[str, Any]]] = None
_VIKRITI_SCORING_CACHE: Optional[List[Dict[str, Any]]] = None
_AGNI_CLASSIFICATION_CACHE: Optional[List[Dict[str, Any]]] = None
_AMA_INDICATORS_CACHE: Optional[List[Dict[str, Any]]] = None
_DOSHA_FOOD_QUALITIES_CACHE: Optional[List[Dict[str, Any]]] = None
_AGNI_MEAL_TIMING_CACHE: Optional[List[Dict[str, Any]]] = None
_COOKING_METHODS_CACHE: Optional[List[Dict[str, Any]]] = None
_PORTION_GUIDANCE_CACHE: Optional[List[Dict[str, Any]]] = None
_AYURVEDA_PROFILES_CACHE: Optional[List[Dict[str, Any]]] = None
_DOSHA_DETERMINATION_RULES_CACHE: Optional[List[Dict[str, Any]]] = None
_VIKRITI_SEVERITY_RULES_CACHE: Optional[List[Dict[str, Any]]] = None
_AMA_LEVEL_RULES_CACHE: Optional[List[Dict[str, Any]]] = None


def _get_kb_path(filename: str) -> Path:
    """Get path to KB JSON file."""
    return Path(__file__).parent.parent.parent / "knowledge_base" / "ayurveda" / filename


def _load_prakriti_scoring() -> List[Dict[str, Any]]:
    """Load Prakriti scoring rules from KB."""
    global _PRAKRITI_SCORING_CACHE
    if _PRAKRITI_SCORING_CACHE is not None:
        return _PRAKRITI_SCORING_CACHE
    
    kb_path = _get_kb_path("prakriti_scoring_kb.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    _PRAKRITI_SCORING_CACHE = [rule for rule in data if rule.get("status") == "active"]
    return _PRAKRITI_SCORING_CACHE


def _load_vikriti_scoring() -> List[Dict[str, Any]]:
    """Load Vikriti scoring rules from KB."""
    global _VIKRITI_SCORING_CACHE
    if _VIKRITI_SCORING_CACHE is not None:
        return _VIKRITI_SCORING_CACHE
    
    kb_path = _get_kb_path("vikriti_scoring_kb.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    _VIKRITI_SCORING_CACHE = [rule for rule in data if rule.get("status") == "active"]
    return _VIKRITI_SCORING_CACHE


def _load_agni_classification() -> List[Dict[str, Any]]:
    """Load Agni classification rules from KB."""
    global _AGNI_CLASSIFICATION_CACHE
    if _AGNI_CLASSIFICATION_CACHE is not None:
        return _AGNI_CLASSIFICATION_CACHE
    
    kb_path = _get_kb_path("agni_classification_kb.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    _AGNI_CLASSIFICATION_CACHE = [rule for rule in data if rule.get("status") == "active"]
    return _AGNI_CLASSIFICATION_CACHE


def _load_ama_indicators() -> List[Dict[str, Any]]:
    """Load Ama indicators from KB."""
    global _AMA_INDICATORS_CACHE
    if _AMA_INDICATORS_CACHE is not None:
        return _AMA_INDICATORS_CACHE
    
    kb_path = _get_kb_path("ama_indicators_kb.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    _AMA_INDICATORS_CACHE = [rule for rule in data if rule.get("status") == "active"]
    return _AMA_INDICATORS_CACHE


def _load_dosha_food_qualities() -> List[Dict[str, Any]]:
    """Load dosha food qualities from KB."""
    global _DOSHA_FOOD_QUALITIES_CACHE
    if _DOSHA_FOOD_QUALITIES_CACHE is not None:
        return _DOSHA_FOOD_QUALITIES_CACHE
    
    kb_path = _get_kb_path("dosha_food_qualities_kb.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    _DOSHA_FOOD_QUALITIES_CACHE = [rule for rule in data if rule.get("status") == "active"]
    return _DOSHA_FOOD_QUALITIES_CACHE


def _load_agni_meal_timing() -> List[Dict[str, Any]]:
    """Load Agni meal timing rules from KB."""
    global _AGNI_MEAL_TIMING_CACHE
    if _AGNI_MEAL_TIMING_CACHE is not None:
        return _AGNI_MEAL_TIMING_CACHE
    
    kb_path = _get_kb_path("agni_meal_timing_kb.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    _AGNI_MEAL_TIMING_CACHE = [rule for rule in data if rule.get("status") == "active"]
    return _AGNI_MEAL_TIMING_CACHE


def _load_cooking_methods() -> List[Dict[str, Any]]:
    """Load cooking methods from KB."""
    global _COOKING_METHODS_CACHE
    if _COOKING_METHODS_CACHE is not None:
        return _COOKING_METHODS_CACHE
    
    kb_path = _get_kb_path("cooking_methods_kb.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    _COOKING_METHODS_CACHE = [rule for rule in data if rule.get("status") == "active"]
    return _COOKING_METHODS_CACHE


def _load_portion_guidance() -> List[Dict[str, Any]]:
    """Load portion guidance from KB."""
    global _PORTION_GUIDANCE_CACHE
    if _PORTION_GUIDANCE_CACHE is not None:
        return _PORTION_GUIDANCE_CACHE
    
    kb_path = _get_kb_path("portion_guidance_kb.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    _PORTION_GUIDANCE_CACHE = [rule for rule in data if rule.get("status") == "active"]
    return _PORTION_GUIDANCE_CACHE


def _load_ayurveda_profiles() -> List[Dict[str, Any]]:
    """Load Ayurveda profiles from KB."""
    global _AYURVEDA_PROFILES_CACHE
    if _AYURVEDA_PROFILES_CACHE is not None:
        return _AYURVEDA_PROFILES_CACHE
    
    kb_path = _get_kb_path("ayurveda_profiles_kb.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    _AYURVEDA_PROFILES_CACHE = [rule for rule in data if rule.get("status") == "active"]
    return _AYURVEDA_PROFILES_CACHE


def _load_dosha_determination_rules() -> List[Dict[str, Any]]:
    """Load dosha determination rules from KB."""
    global _DOSHA_DETERMINATION_RULES_CACHE
    if _DOSHA_DETERMINATION_RULES_CACHE is not None:
        return _DOSHA_DETERMINATION_RULES_CACHE
    
    kb_path = _get_kb_path("dosha_determination_rules_kb.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    _DOSHA_DETERMINATION_RULES_CACHE = [rule for rule in data if rule.get("status") == "active"]
    return _DOSHA_DETERMINATION_RULES_CACHE


def _load_vikriti_severity_rules() -> List[Dict[str, Any]]:
    """Load Vikriti severity rules from KB."""
    global _VIKRITI_SEVERITY_RULES_CACHE
    if _VIKRITI_SEVERITY_RULES_CACHE is not None:
        return _VIKRITI_SEVERITY_RULES_CACHE
    
    kb_path = _get_kb_path("vikriti_severity_rules_kb.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    _VIKRITI_SEVERITY_RULES_CACHE = [rule for rule in data if rule.get("status") == "active"]
    return _VIKRITI_SEVERITY_RULES_CACHE


def _load_ama_level_rules() -> List[Dict[str, Any]]:
    """Load Ama level rules from KB."""
    global _AMA_LEVEL_RULES_CACHE
    if _AMA_LEVEL_RULES_CACHE is not None:
        return _AMA_LEVEL_RULES_CACHE
    
    kb_path = _get_kb_path("ama_level_rules_kb.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    _AMA_LEVEL_RULES_CACHE = [rule for rule in data if rule.get("status") == "active"]
    return _AMA_LEVEL_RULES_CACHE


# ============================================================================
# PUBLIC API FUNCTIONS
# ============================================================================

def get_prakriti_scoring_rule(question_id: str) -> Optional[Dict[str, Any]]:
    """Get Prakriti scoring rule for a question ID."""
    rules = _load_prakriti_scoring()
    for rule in rules:
        if rule.get("question_id") == question_id:
            return rule
    return None


def get_all_prakriti_scoring_rules() -> List[Dict[str, Any]]:
    """Get all active Prakriti scoring rules."""
    return _load_prakriti_scoring()


def get_vikriti_scoring_rule(question_id: str) -> Optional[Dict[str, Any]]:
    """Get Vikriti scoring rule for a question ID."""
    rules = _load_vikriti_scoring()
    for rule in rules:
        if rule.get("question_id") == question_id:
            return rule
    return None


def get_all_vikriti_scoring_rules() -> List[Dict[str, Any]]:
    """Get all active Vikriti scoring rules."""
    return _load_vikriti_scoring()


def get_agni_classification_rule(question_id: str) -> Optional[Dict[str, Any]]:
    """Get Agni classification rule for a question ID."""
    rules = _load_agni_classification()
    for rule in rules:
        if rule.get("question_id") == question_id:
            return rule
    return None


def get_all_agni_classification_rules() -> List[Dict[str, Any]]:
    """Get all active Agni classification rules."""
    return _load_agni_classification()


def get_ama_indicator(indicator_id: str) -> Optional[Dict[str, Any]]:
    """Get Ama indicator by ID."""
    indicators = _load_ama_indicators()
    for indicator in indicators:
        if indicator.get("indicator_id") == indicator_id:
            return indicator
    return None


def get_all_ama_indicators() -> List[Dict[str, Any]]:
    """Get all active Ama indicators."""
    return _load_ama_indicators()


def get_dosha_food_qualities(dosha: str) -> Optional[Dict[str, Any]]:
    """Get food qualities for a dosha."""
    qualities = _load_dosha_food_qualities()
    for q in qualities:
        if q.get("dosha", "").lower() == dosha.lower():
            return q.get("food_qualities", {})
    return None


def get_agni_meal_timing(agni_type: str) -> Optional[Dict[str, Any]]:
    """Get meal timing recommendation for an Agni type."""
    timings = _load_agni_meal_timing()
    for timing in timings:
        if timing.get("agni_type", "").lower() == agni_type.lower():
            return timing
    return None


def get_cooking_methods(condition_id: Optional[str] = None, condition_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get cooking methods for a condition, or default."""
    methods = _load_cooking_methods()
    
    if condition_id and condition_type:
        for method in methods:
            if (method.get("condition_id") == condition_id and 
                method.get("condition_type") == condition_type):
                return method
    
    # Return default
    for method in methods:
        if method.get("is_default"):
            return method
    
    return methods[0] if methods else None


def get_portion_guidance(condition_id: Optional[str] = None, condition_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get portion guidance for a condition, or default."""
    guidances = _load_portion_guidance()
    
    if condition_id and condition_type:
        for guidance in guidances:
            if (guidance.get("condition_id") == condition_id and 
                guidance.get("condition_type") == condition_type):
                return guidance
    
    # Return default
    for guidance in guidances:
        if guidance.get("is_default"):
            return guidance
    
    return guidances[0] if guidances else None


def get_ayurveda_profile(dosha: str) -> Optional[Dict[str, Any]]:
    """Get Ayurveda profile for a dosha."""
    profiles = _load_ayurveda_profiles()
    for profile in profiles:
        if profile.get("dosha", "").lower() == dosha.lower():
            return profile
    return None


def get_dosha_determination_rule(rule_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get dosha determination rule, or default."""
    rules = _load_dosha_determination_rules()
    
    if rule_id:
        for rule in rules:
            if rule.get("rule_id") == rule_id:
                return rule
        return None
    
    # Return default
    for rule in rules:
        if rule.get("is_default"):
            return rule
    
    return rules[0] if rules else None


def get_vikriti_severity_rule(rule_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get Vikriti severity rule, or default."""
    rules = _load_vikriti_severity_rules()
    
    if rule_id:
        for rule in rules:
            if rule.get("rule_id") == rule_id:
                return rule
        return None
    
    # Return default
    for rule in rules:
        if rule.get("is_default"):
            return rule
    
    return rules[0] if rules else None


def get_ama_level_rule(rule_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get Ama level rule, or default."""
    rules = _load_ama_level_rules()
    
    if rule_id:
        for rule in rules:
            if rule.get("rule_id") == rule_id:
                return rule
        return None
    
    # Return default
    for rule in rules:
        if rule.get("is_default"):
            return rule
    
    return rules[0] if rules else None






