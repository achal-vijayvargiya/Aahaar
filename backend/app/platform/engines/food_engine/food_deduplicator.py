"""
Food Deduplication System.

Deduplicates food variations (same food, different types/varieties) from food lists.
Keeps only one food per variation group before ranking.
"""
import re
from typing import Dict, List, Any, Optional
from collections import defaultdict


class FoodDeduplicator:
    """Deduplicates food variations by identifying base food groups."""
    
    def __init__(
        self,
        enable_scientific_name_matching: bool = True,
        enable_base_name_matching: bool = True
    ):
        self.enable_scientific_name_matching = enable_scientific_name_matching
        self.enable_base_name_matching = enable_base_name_matching
    
    def extract_scientific_name(self, display_name: str) -> Optional[str]:
        """Extract scientific name from parentheses."""
        if not display_name:
            return None
        match = re.search(r'\(([^)]+)\)', display_name)
        if match:
            return match.group(1).strip().lower()
        return None
    
    def extract_base_food_name(self, display_name: str) -> Optional[str]:
        """Extract base food name (before first comma)."""
        if not display_name:
            return None
        name_without_scientific = re.sub(r'\([^)]+\)', '', display_name).strip()
        base_name = name_without_scientific.split(',')[0].strip()
        return base_name.lower().strip() if base_name else None
    
    def get_food_group_key(self, food: Dict[str, Any]) -> Optional[str]:
        """Get group key for a food to identify variations."""
        display_name = food.get("display_name", "")
        if not display_name:
            return None
        
        if self.enable_scientific_name_matching:
            scientific_name = self.extract_scientific_name(display_name)
            if scientific_name:
                return f"scientific:{scientific_name}"
        
        if self.enable_base_name_matching:
            base_name = self.extract_base_food_name(display_name)
            if base_name:
                skip_words = {"other", "mixed", "various", "assorted", "combination"}
                if base_name not in skip_words and len(base_name) > 2:
                    return f"base:{base_name}"
        
        return None
    
    def deduplicate_foods(
        self,
        foods: List[Dict[str, Any]],
        keep_best_ranked: bool = False
    ) -> List[Dict[str, Any]]:
        """Deduplicate food variations, keeping only one food per group."""
        if not foods:
            return []
        
        food_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        ungrouped_foods: List[Dict[str, Any]] = []
        
        for food in foods:
            group_key = self.get_food_group_key(food)
            if group_key:
                food_groups[group_key].append(food)
            else:
                ungrouped_foods.append(food)
        
        deduplicated = []
        
        for group_key, group_foods in food_groups.items():
            if len(group_foods) == 1:
                deduplicated.append(group_foods[0])
            else:
                if keep_best_ranked:
                    has_ranking = any(
                        f.get("ranking", {}).get("rank") is not None 
                        for f in group_foods
                    )
                    if has_ranking:
                        sorted_group = sorted(
                            group_foods,
                            key=lambda f: f.get("ranking", {}).get("rank", 999999)
                        )
                        best_food = sorted_group[0]
                    else:
                        best_food = group_foods[0]
                else:
                    best_food = group_foods[0]
                
                best_food = best_food.copy()
                if "ranking" not in best_food:
                    best_food["ranking"] = {}
                
                best_food["ranking"]["deduplication"] = {
                    "group_key": group_key,
                    "variations_found": len(group_foods),
                    "variation_food_ids": [f.get("food_id") for f in group_foods[1:]],
                    "variation_display_names": [f.get("display_name") for f in group_foods[1:]]
                }
                
                deduplicated.append(best_food)
        
        deduplicated.extend(ungrouped_foods)
        
        has_ranking = any(
            f.get("ranking", {}).get("rank") is not None 
            for f in deduplicated
        )
        if has_ranking:
            deduplicated.sort(key=lambda f: f.get("ranking", {}).get("rank", 999999))
        
        return deduplicated
