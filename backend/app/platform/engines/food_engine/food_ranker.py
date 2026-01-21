"""
Food Ranking System.

Multi-tier ranking system for food items with configurable tier enable/disable.

Tiers:
1. Medical Safety (40-50% weight)
2. Nutritional Alignment (25-30% weight)
3. Ayurveda Alignment (15-20% weight)
4. Variety & Rotation (10-15% weight)
5. User Preferences (5-10% weight)
6. Practical Factors (5% weight)
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from app.platform.core.context import (
    MNTContext,
    TargetContext,
    AyurvedaContext,
    DiagnosisContext,
)


@dataclass
class RankingTierConfig:
    """Configuration for ranking tiers - enable/disable and weights."""
    # Tier 1: Medical Safety
    enable_medical_safety: bool = True
    medical_safety_weight: float = 0.45  # 45% of total score
    
    # Tier 2: Nutritional Alignment
    enable_nutrition_alignment: bool = True
    nutrition_alignment_weight: float = 0.27  # 27% of total score
    
    # Tier 3: Ayurveda Alignment
    enable_ayurveda_alignment: bool = True
    ayurveda_alignment_weight: float = 0.18  # 18% of total score
    
    # Tier 4: Variety & Rotation
    enable_variety: bool = True
    variety_weight: float = 0.10  # 10% of total score
    
    # Tier 5: User Preferences
    enable_preferences: bool = True
    preferences_weight: float = 0.05  # 5% of total score
    
    # Tier 6: Practical Factors
    enable_practical: bool = True
    practical_weight: float = 0.05  # 5% of total score
    
    def get_total_weight(self) -> float:
        """Get total weight of enabled tiers."""
        total = 0.0
        if self.enable_medical_safety:
            total += self.medical_safety_weight
        if self.enable_nutrition_alignment:
            total += self.nutrition_alignment_weight
        if self.enable_ayurveda_alignment:
            total += self.ayurveda_alignment_weight
        if self.enable_variety:
            total += self.variety_weight
        if self.enable_preferences:
            total += self.preferences_weight
        if self.enable_practical:
            total += self.practical_weight
        return total
    
    def normalize_weights(self):
        """Normalize weights so they sum to 1.0."""
        total = self.get_total_weight()
        if total > 0:
            if self.enable_medical_safety:
                self.medical_safety_weight /= total
            if self.enable_nutrition_alignment:
                self.nutrition_alignment_weight /= total
            if self.enable_ayurveda_alignment:
                self.ayurveda_alignment_weight /= total
            if self.enable_variety:
                self.variety_weight /= total
            if self.enable_preferences:
                self.preferences_weight /= total
            if self.enable_practical:
                self.practical_weight /= total


class FoodRanker:
    """
    Food ranking system with configurable tiers.
    
    Calculates comprehensive ranking scores for food items based on multiple factors.
    Each tier can be enabled/disabled independently.
    """
    
    def __init__(self, tier_config: Optional[RankingTierConfig] = None):
        """
        Initialize food ranker.
        
        Args:
            tier_config: Ranking tier configuration. If None, uses default config.
        """
        self.tier_config = tier_config or RankingTierConfig()
        # Normalize weights to ensure they sum to 1.0
        self.tier_config.normalize_weights()
    
    def rank_foods(
        self,
        foods: List[Dict[str, Any]],
        medical_conditions: List[str],
        mnt_context: MNTContext,
        target_context: TargetContext,
        ayurveda_context: Optional[AyurvedaContext] = None,
        diagnosis_context: Optional[DiagnosisContext] = None,
        client_preferences: Optional[Dict[str, Any]] = None,
        meal_targets: Optional[Dict[str, float]] = None,
        rotation_history: Optional[List[str]] = None,
        meal_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Rank foods using all enabled tiers.
        
        Args:
            foods: List of food dictionaries to rank
            medical_conditions: List of medical condition IDs
            mnt_context: MNT context with constraints
            target_context: Target context with nutrition targets
            ayurveda_context: Optional Ayurveda context
            diagnosis_context: Optional diagnosis context
            client_preferences: Optional client preferences
            meal_targets: Optional meal-specific nutrition targets
            rotation_history: Optional list of recently used food IDs
            meal_name: Optional meal name for context
        
        Returns:
            List of food dictionaries with ranking metadata, sorted by score (highest first)
        """
        if not foods:
            return []
        
        ranked_foods = []
        
        for food in foods:
            # Calculate tier scores
            tier_scores = {}
            total_score = 0.0
            ranking_factors = {}
            
            # Tier 1: Medical Safety
            if self.tier_config.enable_medical_safety:
                score, factors = self._calculate_medical_safety_score(
                    food, medical_conditions, mnt_context, diagnosis_context
                )
                tier_scores["medical_safety"] = score
                total_score += score * self.tier_config.medical_safety_weight
                ranking_factors.update(factors)
            
            # Tier 2: Nutritional Alignment
            if self.tier_config.enable_nutrition_alignment:
                score, factors = self._calculate_nutrition_alignment_score(
                    food, target_context, meal_targets, mnt_context
                )
                tier_scores["nutrition_alignment"] = score
                total_score += score * self.tier_config.nutrition_alignment_weight
                ranking_factors.update(factors)
            
            # Tier 3: Ayurveda Alignment
            if self.tier_config.enable_ayurveda_alignment:
                score, factors = self._calculate_ayurveda_alignment_score(
                    food, ayurveda_context
                )
                tier_scores["ayurveda_alignment"] = score
                total_score += score * self.tier_config.ayurveda_alignment_weight
                ranking_factors.update(factors)
            
            # Tier 4: Variety & Rotation
            if self.tier_config.enable_variety:
                score, factors = self._calculate_variety_score(
                    food, rotation_history, meal_name
                )
                tier_scores["variety"] = score
                total_score += score * self.tier_config.variety_weight
                ranking_factors.update(factors)
            
            # Tier 5: User Preferences
            if self.tier_config.enable_preferences:
                score, factors = self._calculate_preference_score(
                    food, client_preferences
                )
                tier_scores["preferences"] = score
                total_score += score * self.tier_config.preferences_weight
                ranking_factors.update(factors)
            
            # Tier 6: Practical Factors
            if self.tier_config.enable_practical:
                score, factors = self._calculate_practical_score(food)
                tier_scores["practical"] = score
                total_score += score * self.tier_config.practical_weight
                ranking_factors.update(factors)
            
            # Add ranking metadata to food
            food_with_ranking = food.copy()
            food_with_ranking["ranking"] = {
                "total_score": round(total_score, 2),
                "tier_scores": {k: round(v, 2) for k, v in tier_scores.items()},
                "ranking_factors": ranking_factors,
            }
            
            ranked_foods.append((food_with_ranking, total_score))
        
        # Sort by total score (highest first)
        ranked_foods.sort(key=lambda x: x[1], reverse=True)
        
        # Add rank position
        result = []
        for rank, (food, score) in enumerate(ranked_foods, start=1):
            food["ranking"]["rank"] = rank
            result.append(food)
        
        return result
    
    def _calculate_medical_safety_score(
        self,
        food: Dict[str, Any],
        medical_conditions: List[str],
        mnt_context: MNTContext,
        diagnosis_context: Optional[DiagnosisContext]
    ) -> tuple[float, Dict[str, Any]]:
        """
        Tier 1: Calculate medical safety score.
        
        Returns:
            (score, factors_dict)
        """
        score = 0.0
        factors = {}
        
        if not medical_conditions:
            return score, factors
        
        mnt_profile = food.get("mnt_profile", {})
        medical_tags = mnt_profile.get("medical_tags", {})
        compatibility_levels = food.get("compatibility_levels", {})
        
        # Condition to tag mapping
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
        
        # 1.1 Condition Safety Tags (+100 per matching condition)
        safe_conditions = []
        for condition in medical_conditions:
            tag_key = condition_to_tag.get(condition.lower())
            if tag_key and medical_tags.get(tag_key, False):
                score += 100.0
                safe_conditions.append(condition)
        
        if safe_conditions:
            factors["condition_safe_tags"] = safe_conditions
        
        # 1.2 Condition Compatibility Level
        safe_compat = 0
        caution_compat = 0
        for condition in medical_conditions:
            compat = compatibility_levels.get(condition, "").lower()
            if compat == "safe":
                score += 50.0
                safe_compat += 1
            elif compat == "caution":
                score += 20.0
                caution_compat += 1
        
        if safe_compat > 0:
            factors["safe_compatibility"] = safe_compat
        if caution_compat > 0:
            factors["caution_compatibility"] = caution_compat
        
        # 1.3 MNT Compliance Flags (+10 per matching flag)
        macro_compliance = mnt_profile.get("macro_compliance", {})
        micro_compliance = mnt_profile.get("micro_compliance", {})
        
        # Check macro constraints
        macro_constraints = mnt_context.macro_constraints or {}
        compliance_count = 0
        
        if macro_constraints.get("carbs_g", {}).get("max"):
            if macro_compliance.get("low_carb"):
                score += 10.0
                compliance_count += 1
        
        if macro_constraints.get("fat_g", {}).get("max"):
            if macro_compliance.get("low_fat"):
                score += 10.0
                compliance_count += 1
        
        if macro_constraints.get("protein_g", {}).get("min"):
            if macro_compliance.get("high_protein"):
                score += 10.0
                compliance_count += 1
        
        # Check micro constraints
        micro_constraints = mnt_context.micro_constraints or {}
        if micro_constraints.get("sodium_mg", {}).get("max"):
            if micro_compliance.get("low_sodium"):
                score += 10.0
                compliance_count += 1
        
        if compliance_count > 0:
            factors["mnt_compliance_flags"] = compliance_count
        
        # 1.4 Preferred Conditions (+30 per matching)
        preferred_conditions = mnt_profile.get("preferred_conditions", [])
        preferred_count = 0
        for condition in medical_conditions:
            if condition.lower() in [p.lower() for p in preferred_conditions]:
                score += 30.0
                preferred_count += 1
        
        if preferred_count > 0:
            factors["preferred_conditions"] = preferred_count
        
        # 1.5 Inclusion Tags (+10 per tag)
        inclusion_tags = mnt_profile.get("food_inclusion_tags", [])
        if inclusion_tags:
            score += len(inclusion_tags) * 10.0
            factors["inclusion_tags"] = len(inclusion_tags)
        
        # 1.6 Exclusion Tags Penalty (-5 per tag, but food still included)
        exclusion_tags = mnt_profile.get("food_exclusion_tags", [])
        if exclusion_tags:
            score -= len(exclusion_tags) * 5.0
            factors["exclusion_tags_penalty"] = len(exclusion_tags)
        
        return score, factors
    
    def _calculate_nutrition_alignment_score(
        self,
        food: Dict[str, Any],
        target_context: TargetContext,
        meal_targets: Optional[Dict[str, float]],
        mnt_context: MNTContext
    ) -> tuple[float, Dict[str, Any]]:
        """
        Tier 2: Calculate nutritional alignment score.
        
        Returns:
            (score, factors_dict)
        """
        score = 0.0
        factors = {}
        
        nutrition = food.get("nutrition", {})
        if not nutrition:
            return score, factors
        
        calories = nutrition.get("calories", 0) or 0.0
        macros = nutrition.get("macros", {}) or {}
        protein_g = macros.get("protein_g", 0) or 0.0
        carbs_g = macros.get("carbs_g", 0) or 0.0
        fiber_g = macros.get("fiber_g", 0) or 0.0
        fat_g = macros.get("fat_g", 0) or 0.0
        
        # Use meal targets if available, otherwise daily targets
        targets = meal_targets if meal_targets else {}
        daily_targets = target_context.macros or {}
        
        target_protein = targets.get("protein_g") or daily_targets.get("protein_g") or 0.0
        target_carbs = targets.get("carbs_g") or daily_targets.get("carbs_g") or 0.0
        target_calories = targets.get("calories") or target_context.calories_target or 0.0
        
        # 2.1 Protein Density (if protein target is high)
        if target_protein > 0 and calories > 0:
            protein_density = (protein_g / calories) * 100.0  # g per 100 kcal
            target_protein_density = (target_protein / target_calories) * 100.0 if target_calories > 0 else 0.0
            
            if target_protein_density > 0:
                ratio = protein_density / target_protein_density
                if ratio >= 1.0:
                    score += 20.0  # High protein food
                    factors["high_protein_density"] = round(protein_density, 1)
                elif ratio >= 0.8:
                    score += 15.0
                    factors["good_protein_density"] = round(protein_density, 1)
                elif ratio >= 0.6:
                    score += 10.0
                    factors["moderate_protein_density"] = round(protein_density, 1)
        
        # 2.2 Fiber Content (+15 max, based on fiber per 100g)
        if fiber_g >= 5.0:
            score += 15.0
            factors["high_fiber"] = round(fiber_g, 1)
        elif fiber_g >= 3.0:
            score += 10.0
            factors["moderate_fiber"] = round(fiber_g, 1)
        elif fiber_g >= 1.0:
            score += 5.0
            factors["some_fiber"] = round(fiber_g, 1)
        
        # 2.3 Macro Balance (how well food fits meal targets)
        if target_calories > 0:
            # Calculate food's macro percentages
            food_protein_pct = (protein_g * 4 / calories * 100) if calories > 0 else 0
            food_carbs_pct = (carbs_g * 4 / calories * 100) if calories > 0 else 0
            food_fat_pct = (fat_g * 9 / calories * 100) if calories > 0 else 0
            
            # Calculate target macro percentages
            target_protein_pct = (target_protein * 4 / target_calories * 100) if target_calories > 0 else 0
            target_carbs_pct = (target_carbs * 4 / target_calories * 100) if target_calories > 0 else 0
            
            # Score based on alignment (simplified - prioritize protein if needed)
            if target_protein_pct > 0:
                protein_ratio = food_protein_pct / target_protein_pct if target_protein_pct > 0 else 0
                if 0.8 <= protein_ratio <= 1.2:
                    score += 10.0
                    factors["protein_aligned"] = True
        
        # 2.4 Calorie Density (for weight management)
        calorie_density = nutrition.get("calorie_density_kcal_per_g", 0) or 0.0
        if calorie_density > 0:
            # Lower density is better for weight management
            # Score inversely proportional to density
            if calorie_density <= 1.0:  # Very low density (vegetables)
                score += 10.0
                factors["low_calorie_density"] = round(calorie_density, 2)
            elif calorie_density <= 2.0:  # Low density
                score += 7.0
                factors["moderate_calorie_density"] = round(calorie_density, 2)
            elif calorie_density <= 3.0:  # Moderate density
                score += 3.0
        
        return score, factors
    
    def _calculate_ayurveda_alignment_score(
        self,
        food: Dict[str, Any],
        ayurveda_context: Optional[AyurvedaContext]
    ) -> tuple[float, Dict[str, Any]]:
        """
        Tier 3: Calculate Ayurveda alignment score.
        
        Returns:
            (score, factors_dict)
        """
        score = 0.0
        factors = {}
        
        if not ayurveda_context:
            return score, factors
        
        dosha_primary = getattr(ayurveda_context, "dosha_primary", None)
        if not dosha_primary:
            return score, factors
        
        # Get Ayurveda preferences
        notes = getattr(ayurveda_context, "vikriti_notes", {}) or {}
        food_prefs = notes.get("food_preferences", [])
        prefer_ids = {p["food_id"] for p in food_prefs if p.get("preference_type") == "prefer"}
        avoid_ids = {p["food_id"] for p in food_prefs if p.get("preference_type") == "avoid"}
        
        food_id = food.get("food_id")
        
        # 3.1 Explicit Preferences
        if food_id in prefer_ids:
            score += 50.0
            factors["ayurveda_preferred"] = True
        elif food_id in avoid_ids:
            score -= 30.0
            factors["ayurveda_avoided"] = True
        
        # 3.2 Dosha Alignment (if Ayurvedic profile available)
        # Note: This would require ayurvedic_profile data in food dict
        # For now, we rely on explicit preferences
        
        # 3.3 Guna Classification (if available)
        # Would check for satvik/rajasik/tamasik classification
        
        return score, factors
    
    def _calculate_variety_score(
        self,
        food: Dict[str, Any],
        rotation_history: Optional[List[str]],
        meal_name: Optional[str]
    ) -> tuple[float, Dict[str, Any]]:
        """
        Tier 4: Calculate variety and rotation score.
        
        Returns:
            (score, factors_dict)
        """
        score = 50.0  # Base score (neutral)
        factors = {}
        
        if not rotation_history:
            return score, factors
        
        food_id = food.get("food_id")
        
        # 4.1 Recent Usage Penalty
        if food_id in rotation_history:
            # Penalize based on how recently used
            # More recent = higher penalty
            try:
                index = rotation_history.index(food_id)
                # Recent items (last 3) get higher penalty
                if index < 3:
                    penalty = (3 - index) * 15.0
                    score -= penalty
                    factors["recently_used"] = f"{index + 1} meals ago"
                elif index < 7:
                    penalty = (7 - index) * 5.0
                    score -= penalty
                    factors["used_recently"] = f"{index + 1} meals ago"
            except ValueError:
                pass  # Not in history
        
        # 4.2 Category Diversity (if we had category-level history)
        # Would check if same food type was used recently
        
        return score, factors
    
    def _calculate_preference_score(
        self,
        food: Dict[str, Any],
        client_preferences: Optional[Dict[str, Any]]
    ) -> tuple[float, Dict[str, Any]]:
        """
        Tier 5: Calculate user preference score.
        
        Returns:
            (score, factors_dict)
        """
        score = 0.0
        factors = {}
        
        if not client_preferences:
            return score, factors
        
        food_id = food.get("food_id")
        likes = set(client_preferences.get("likes", []))
        dislikes = set(client_preferences.get("dislikes", []))
        
        # 5.1 Client Likes
        if food_id in likes:
            score += 20.0
            factors["client_liked"] = True
        
        # 5.2 Client Dislikes (should be filtered, but if included: heavy penalty)
        if food_id in dislikes:
            score -= 50.0
            factors["client_disliked"] = True
        
        # 5.3 Dietary Preferences (if available)
        # Would check vegetarian/vegan alignment
        
        return score, factors
    
    def _calculate_practical_score(
        self,
        food: Dict[str, Any]
    ) -> tuple[float, Dict[str, Any]]:
        """
        Tier 6: Calculate practical factors score.
        
        Returns:
            (score, factors_dict)
        """
        score = 0.0
        factors = {}
        
        # 6.1 Portion Flexibility
        serving_size = food.get("serving_size_per_exchange_g")
        if serving_size:
            # Standard serving sizes (30-100g) are easier to portion
            if 30.0 <= serving_size <= 100.0:
                score += 5.0
                factors["standard_serving_size"] = True
        
        # 6.2 Recipe Compatibility (simplified - whole foods are generally better)
        food_type = food.get("food_type")
        if food_type in ["grain", "legume", "vegetable", "fruit"]:
            score += 3.0
            factors["whole_food"] = True
        
        # 6.3 Cooking State (raw foods might be easier)
        cooking_state = food.get("cooking_state")
        if cooking_state == "raw":
            score += 2.0
            factors["ready_to_eat"] = True
        
        return score, factors
