"""
Exchange System Constants.

Standard exchange nutrition values for Indian food categories.
Based on Indian Exchange Lists for Diabetes (IET).

This module now loads data from KB files via kb_exchange_system.
Maintains backward compatibility with existing code.
"""
from typing import Dict
from enum import Enum
from .kb_exchange_system import get_exchange_nutrition as kb_get_exchange_nutrition


class ExchangeCategory(str, Enum):
    """Exchange categories for Indian foods."""
    CEREAL = "cereal"
    PULSE = "pulse"
    MILK = "milk"
    PANEER = "paneer"
    VEGETABLE_A = "vegetable_a"
    VEGETABLE_B = "vegetable_b"
    VEGETABLE_NON_STARCHY = "vegetable_non_starchy"  # Keep for backward compatibility
    VEGETABLE_STARCHY = "vegetable_starchy"  # Keep for backward compatibility
    FRUIT = "fruit"
    FAT = "fat"
    NUTS_SEEDS = "nuts_seeds"
    EGG_WHITES = "egg_whites"
    JAGGERY = "jaggery"


def get_exchange_nutrition(exchange_type: str) -> Dict[str, float]:
    """
    Get nutrition values for one exchange of given type (from KB).
    
    Args:
        exchange_type: Exchange category name
        
    Returns:
        Dictionary with calories, protein_g, carbs_g, fat_g
    """
    return kb_get_exchange_nutrition(exchange_type)


def calculate_nutrition_from_exchanges(exchanges: Dict[str, int]) -> Dict[str, float]:
    """
    Calculate total nutrition from exchange counts.
    
    Args:
        exchanges: Dictionary of exchange_type -> count
        
    Returns:
        Dictionary with total calories, protein_g, carbs_g, fat_g
    """
    total = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    
    for exchange_type, count in exchanges.items():
        nutrition = get_exchange_nutrition(exchange_type)
        for nutrient, value in nutrition.items():
            total[nutrient] += value * count
    
    return total

