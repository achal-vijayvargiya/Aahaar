"""
Ayurvedic Constraints Generator.

Generates food qualities, meal timing, and cooking method constraints
based on Prakriti, Vikriti, Agni, and Ama assessment.

Uses knowledge base (KB) files for:
- Dosha food qualities (prefer/avoid lists)
- Agni meal timing recommendations
- Cooking method recommendations
- Portion guidance recommendations
"""
from typing import Dict, List, Any, Optional
from .assessment_scorer import Dosha, AgniType, AmaLevel
from .kb_ayurveda import (
    get_dosha_food_qualities,
    get_agni_meal_timing,
    get_cooking_methods,
    get_portion_guidance,
)


def generate_ayurvedic_constraints(
    prakriti: Dict[str, Optional[str]],
    vikriti: Dict[str, Any],
    agni: str,
    ama: str,
) -> Dict[str, Any]:
    """
    Generate Ayurvedic constraints based on assessment results.
    
    Args:
        prakriti: Dictionary with "primary" and "secondary" dosha
        vikriti: Dictionary with "imbalanced_doshas" and "severity"
        agni: Agni type string
        ama: Ama level string
        
    Returns:
        Dictionary containing ayurvedic constraints:
        - food_qualities: prefer/avoid lists
        - meal_timing_bias: timing recommendation
        - cooking_methods: recommended cooking methods
        - portion_guidance: portion size recommendation
    """
    # Determine which doshas to balance (prioritize Vikriti over Prakriti)
    doshas_to_balance = vikriti.get("imbalanced_doshas", [])
    if not doshas_to_balance:
        # If no Vikriti, use Prakriti
        if prakriti.get("primary"):
            doshas_to_balance = [prakriti["primary"]]
        if prakriti.get("secondary"):
            doshas_to_balance.append(prakriti["secondary"])
    
    # Combine food qualities from all relevant doshas (from KB)
    prefer_qualities = set()
    avoid_qualities = set()
    
    for dosha in doshas_to_balance:
        food_qualities = get_dosha_food_qualities(dosha)
        if food_qualities:
            prefer_list = food_qualities.get("prefer", [])
            avoid_list = food_qualities.get("avoid", [])
            
            # Extract quality names from KB structure
            for item in prefer_list:
                if isinstance(item, dict):
                    prefer_qualities.add(item.get("quality", ""))
                else:
                    prefer_qualities.add(item)
            
            for item in avoid_list:
                if isinstance(item, dict):
                    avoid_qualities.add(item.get("quality", ""))
                else:
                    avoid_qualities.add(item)
    
    # If no doshas, use Vata as default (most common)
    if not prefer_qualities and not avoid_qualities:
        vata_qualities = get_dosha_food_qualities("Vata")
        if vata_qualities:
            prefer_list = vata_qualities.get("prefer", [])
            avoid_list = vata_qualities.get("avoid", [])
            
            for item in prefer_list:
                if isinstance(item, dict):
                    prefer_qualities.add(item.get("quality", ""))
                else:
                    prefer_qualities.add(item)
            
            for item in avoid_list:
                if isinstance(item, dict):
                    avoid_qualities.add(item.get("quality", ""))
                else:
                    avoid_qualities.add(item)
    
    # Resolve conflicts (if a quality is both prefer and avoid, prioritize avoid)
    prefer_qualities = prefer_qualities - avoid_qualities
    
    # Meal timing bias (from KB)
    agni_timing = get_agni_meal_timing(agni)
    meal_timing_bias = agni_timing.get("meal_timing", "regular") if agni_timing else "regular"
    
    # Cooking methods (from KB)
    cooking_methods_list = []
    cooking_methods_data = None
    
    if ama == AmaLevel.HIGH.value:
        cooking_methods_data = get_cooking_methods("high_ama", "ama_level")
    elif agni == AgniType.MANDA.value:
        cooking_methods_data = get_cooking_methods("manda_agni", "agni_type")
    elif agni == AgniType.TIKSHNA.value:
        cooking_methods_data = get_cooking_methods("tikshna_agni", "agni_type")
    
    if not cooking_methods_data:
        cooking_methods_data = get_cooking_methods()  # Default
    
    if cooking_methods_data:
        methods = cooking_methods_data.get("cooking_methods", [])
        for method in methods:
            if isinstance(method, dict):
                cooking_methods_list.append(method.get("method", ""))
            else:
                cooking_methods_list.append(method)
    
    # Portion guidance (from KB)
    portion_guidance_data = None
    
    if ama == AmaLevel.HIGH.value:
        portion_guidance_data = get_portion_guidance("high_ama", "ama_level")
    elif agni == AgniType.MANDA.value:
        portion_guidance_data = get_portion_guidance("manda_agni", "agni_type")
    elif agni == AgniType.VISHAMA.value:
        portion_guidance_data = get_portion_guidance("vishama_agni", "agni_type")
    elif agni == AgniType.TIKSHNA.value:
        portion_guidance_data = get_portion_guidance("tikshna_agni", "agni_type")
    
    if not portion_guidance_data:
        portion_guidance_data = get_portion_guidance()  # Default
    
    portion_guidance = portion_guidance_data.get("portion_guidance", "moderate") if portion_guidance_data else "moderate"
    
    return {
        "food_qualities": {
            "prefer": sorted([q for q in prefer_qualities if q]),
            "avoid": sorted([q for q in avoid_qualities if q]),
        },
        "meal_timing_bias": meal_timing_bias,
        "cooking_methods": cooking_methods_list if cooking_methods_list else ["boiled", "steamed"],
        "portion_guidance": portion_guidance,
    }

