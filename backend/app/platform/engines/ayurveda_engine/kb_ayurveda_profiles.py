"""
Knowledge Base for Ayurveda profiles (loaded from KB).

Deterministic, rule-based preferences for each dosha.
"""
from typing import Dict, Any, Optional
from .kb_ayurveda import get_ayurveda_profile


def get_profile(dosha: str) -> Optional[Dict[str, Any]]:
    """
    Return KB profile for given dosha (from KB JSON file).
    
    Args:
        dosha: Dosha name (e.g., "vata", "pitta", "kapha")
        
    Returns:
        Profile dictionary or None if not found
    """
    if not dosha:
        return None
    
    profile = get_ayurveda_profile(dosha)
    if not profile:
        return None
    
    # Convert KB structure to expected format for backward compatibility
    result = {}
    
    # Handle favor_spices
    favor_spices = profile.get("favor_spices", [])
    if favor_spices:
        # Extract spice names from KB structure
        spice_list = []
        for item in favor_spices:
            if isinstance(item, dict):
                spice_list.append(item.get("spice", ""))
            else:
                spice_list.append(item)
        result["favor_spices"] = spice_list
    
    # Handle favor (for pitta/kapha)
    favor = profile.get("favor", [])
    if favor:
        favor_list = []
        for item in favor:
            if isinstance(item, dict):
                favor_list.append(item.get("food", ""))
            else:
                favor_list.append(item)
        result["favor"] = favor_list
    
    # Handle favor_foods (for vata)
    favor_foods = profile.get("favor_foods", [])
    if favor_foods:
        favor_list = []
        for item in favor_foods:
            if isinstance(item, dict):
                favor_list.append(item.get("food", ""))
            else:
                favor_list.append(item)
        result["favor"] = favor_list
    
    # Handle avoid
    avoid = profile.get("avoid", [])
    if avoid:
        avoid_list = []
        for item in avoid:
            if isinstance(item, dict):
                avoid_list.append(item.get("food", ""))
            else:
                avoid_list.append(item)
        result["avoid"] = avoid_list
    
    # Handle meal_timing
    result["meal_timing"] = profile.get("meal_timing", "regular_meals")
    
    # Handle food_temperature
    result["food_temperature"] = profile.get("food_temperature", "warm")
    
    # Handle lifestyle
    lifestyle = profile.get("lifestyle", [])
    if lifestyle:
        lifestyle_list = []
        for item in lifestyle:
            if isinstance(item, dict):
                lifestyle_list.append(item.get("practice", ""))
            else:
                lifestyle_list.append(item)
        result["lifestyle"] = lifestyle_list
    
    return result

