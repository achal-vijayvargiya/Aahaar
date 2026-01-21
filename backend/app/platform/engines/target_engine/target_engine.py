"""
Target Engine.
Calculates nutrition targets using IBW-based formulas (Case Study Method).
"""
import logging
from typing import Dict, Optional, Any
from uuid import uuid4

from app.platform.core.context import MNTContext, TargetContext
from app.platform.engines.target_engine.kb_target_formulas import (
    get_micro_target,
    get_all_active_nutrient_ids,
)

logger = logging.getLogger(__name__)


class TargetEngine:
    """
    Target Engine - Simple IBW-based calculation.
    
    Uses case study formulas:
    - IBW = Height - 100 (male) or Height - 105 (female)
    - Energy = IBW × Activity Factor (22.5/27.5/32.5)
    - Protein (g) = 0.8 × IBW
    - Fat = 22.5% of Energy
    - Carbs = Remainder
    """
    
    def __init__(self):
        """Initialize target engine."""
        pass

    def _calculate_ibw(self, height_cm: Optional[float], gender: Optional[str] = None) -> Optional[float]:
        """
        Calculate Ideal Body Weight (IBW) using Brocca's Index.
        
        Formula:
        - Male: IBW = Height (cm) - 100
        - Female: IBW = Height (cm) - 105
        
        Args:
            height_cm: Height in centimeters
            gender: Gender string ("male" | "female" or variants)
            
        Returns:
            IBW in kilograms or None if height is not available
        """
        if height_cm is None:
            logger.debug("[IBW] Height is None, cannot calculate IBW")
            return None
        
        gender_lower = (gender or "").lower()
        if gender_lower in ["female", "f"]:
            ibw = height_cm - 105.0
            logger.info(f"[IBW] Female: {height_cm} - 105 = {ibw:.2f} kg")
        else:
            ibw = height_cm - 100.0
            logger.info(f"[IBW] Male/Default: {height_cm} - 100 = {ibw:.2f} kg")
        
        return ibw

    def _get_activity_factor(self, activity_level: Optional[str]) -> float:
        """
        Get activity factor for energy calculation.
        
        Activity Factors:
        - Sedentary: 22.5 kcal/kg IBW
        - Moderate Active: 27.5 kcal/kg IBW
        - Highly Active: 32.5 kcal/kg IBW
        
        Args:
            activity_level: Activity level string
            
        Returns:
            Activity factor (kcal/kg IBW)
        """
        if activity_level is None:
            return 22.5
        
        activity_lower = activity_level.lower()
        
        if activity_lower in ["sedentary", "sedentary_lifestyle"]:
            factor = 22.5
        elif activity_lower in ["lightly_active", "moderately_active", "moderate_active", "moderate"]:
            factor = 27.5
        elif activity_lower in ["very_active", "highly_active", "extremely_active"]:
            factor = 32.5
        else:
            factor = 22.5  # Default to sedentary
        
        logger.info(f"[Activity Factor] {activity_level} → {factor} kcal/kg IBW")
        return factor

    def calculate_calories(
        self,
        client_profile: Dict[str, Any],
        mnt_context: MNTContext,
        activity_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate calorie target using IBW-based method.
        
        Formula: Energy (kcal) = IBW × Activity Factor
        
        Args:
            client_profile: Client profile with height, gender
            mnt_context: MNT context with calorie constraints
            activity_level: Activity level for activity factor
            
        Returns:
            Dictionary containing:
            - calories_target: Target calorie value
            - calculation_source: "ibw_based"
            - ibw: Ideal body weight in kg
        """
        logger.info("[Calorie Calculation] Starting IBW-based calculation")
        
        height_cm = client_profile.get("height_cm")
        gender = client_profile.get("gender")
        
        # Calculate IBW
        ibw = self._calculate_ibw(height_cm, gender)
        if ibw is None:
            logger.error("[Calorie Calculation] Cannot calculate - height is required")
            return {
                "calories_target": None,
                "calculation_source": "error",
                "ibw": None,
            }
        
        # Get activity factor
        activity_factor = self._get_activity_factor(activity_level)
        
        # Calculate energy: IBW × Activity Factor
        base_calories = ibw * activity_factor
        logger.info(f"[Calorie Calculation] Energy = IBW × Activity Factor")
        logger.info(f"  Energy = {ibw:.2f} kg × {activity_factor} kcal/kg IBW = {base_calories:.2f} kcal")
        
        calories_target = base_calories
        
        # Apply MNT calorie constraints if present
        macro_constraints = mnt_context.macro_constraints or {}
        calorie_constraints = macro_constraints.get("calories", {})
        
        # Apply min/max limits
        min_cal = calorie_constraints.get("min")
        max_cal = calorie_constraints.get("max")
        if min_cal is not None:
            calories_target = max(calories_target, min_cal)
            logger.info(f"[Calorie Calculation] Applied min constraint: {min_cal} kcal")
        if max_cal is not None:
            calories_target = min(calories_target, max_cal)
            logger.info(f"[Calorie Calculation] Applied max constraint: {max_cal} kcal")
        
        logger.info(f"[Calorie Calculation] Final calories target: {calories_target:.2f} kcal")
        
        return {
            "calories_target": float(calories_target),
            "calculation_source": "ibw_based",
            "ibw": float(ibw),
        }

    def calculate_macros(
        self,
        calories_target: float,
        client_profile: Dict[str, Any],
        mnt_context: MNTContext,
        diagnosis_context: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Calculate macro nutrients using case study formulas.
        
        Formulas:
        - Protein (g) = 0.8 × IBW
        - Protein kcal = Protein (g) × 4
        - Protein % = (Protein kcal ÷ Energy) × 100
        - Fat kcal = 22.5% × Energy
        - Fat (g) = Fat kcal ÷ 9
        - Carb % = 100% - Protein% - Fat%
        - Carb kcal = Carb% × Energy
        - Carb (g) = Carb kcal ÷ 4
        
        Args:
            calories_target: Target calorie value
            client_profile: Client profile data
            mnt_context: MNT context with macro constraints
            
        Returns:
            Dictionary containing macros with grams and percentages
        """
        logger.info(f"[Macro Calculation] Starting macro calculation for {calories_target:.2f} kcal")
        
        if calories_target is None or calories_target <= 0:
            logger.warning("[Macro Calculation] Invalid calories target")
            return {
                "carbohydrates": {"g": 0, "percent": 0.0},
                "proteins": {"g": 0, "percent": 0.0},
                "fats": {"g": 0, "percent": 0.0},
            }
        
        # Get IBW for protein calculation
        height_cm = client_profile.get("height_cm")
        gender = client_profile.get("gender")
        ibw = self._calculate_ibw(height_cm, gender)
        
        if ibw is None or ibw <= 0:
            logger.warning("[Macro Calculation] Cannot calculate - IBW not available")
            return {
                "carbohydrates": {"g": 0, "percent": 0.0},
                "proteins": {"g": 0, "percent": 0.0},
                "fats": {"g": 0, "percent": 0.0},
            }
        
        # Formula 1: Protein (g) = 0.8 × IBW
        protein_g = 0.8 * ibw
        logger.info(f"[Macro Calculation] Protein (g) = 0.8 × {ibw:.2f} = {protein_g:.2f} g")
        
        # Formula 2: Protein kcal = Protein (g) × 4
        protein_kcal = protein_g * 4.0
        logger.info(f"[Macro Calculation] Protein kcal = {protein_g:.2f} × 4 = {protein_kcal:.2f} kcal")
        
        # Formula 3: Protein % = (Protein kcal ÷ Energy) × 100
        protein_pct = (protein_kcal / calories_target) * 100.0
        logger.info(f"[Macro Calculation] Protein % = ({protein_kcal:.2f} ÷ {calories_target:.2f}) × 100 = {protein_pct:.2f}%")
        
        # Formula 4: Fat kcal = 22.5% × Energy
        fat_pct = 22.5
        fat_kcal = calories_target * fat_pct / 100.0
        logger.info(f"[Macro Calculation] Fat kcal = {fat_pct}% × {calories_target:.2f} = {fat_kcal:.2f} kcal")
        
        # Formula 5: Fat (g) = Fat kcal ÷ 9
        fat_g = fat_kcal / 9.0
        logger.info(f"[Macro Calculation] Fat (g) = {fat_kcal:.2f} ÷ 9 = {fat_g:.2f} g")
        
        # Formula 6: Carb % = 100% - Protein% - Fat%
        carb_pct = 100.0 - protein_pct - fat_pct
        logger.info(f"[Macro Calculation] Carb % = 100 - {protein_pct:.2f} - {fat_pct} = {carb_pct:.2f}%")
        
        # Formula 7: Carb kcal = Carb% × Energy
        carb_kcal = carb_pct * calories_target / 100.0
        logger.info(f"[Macro Calculation] Carb kcal = {carb_pct:.2f}% × {calories_target:.2f} = {carb_kcal:.2f} kcal")
        
        # Formula 8: Carb (g) = Carb kcal ÷ 4
        carb_g = carb_kcal / 4.0
        logger.info(f"[Macro Calculation] Carb (g) = {carb_kcal:.2f} ÷ 4 = {carb_g:.2f} g")
        
        # Apply MNT macro constraints if present
        macro_constraints = mnt_context.macro_constraints or {}
        mnt_protein = macro_constraints.get("protein_percent") or {}
        mnt_fat = macro_constraints.get("fat_percent") or {}
        mnt_carb = macro_constraints.get("carbohydrates_percent") or {}
        
        # Adjust if MNT constraints are more restrictive
        if "min" in mnt_protein:
            mnt_protein_min_pct = mnt_protein["min"]
            mnt_protein_min_g = (calories_target * mnt_protein_min_pct / 100.0) / 4.0
            if mnt_protein_min_g > protein_g:
                protein_g = mnt_protein_min_g
                protein_kcal = protein_g * 4.0
                protein_pct = (protein_kcal / calories_target) * 100.0
                # Recalculate carbs
                carb_pct = 100.0 - protein_pct - fat_pct
                carb_kcal = carb_pct * calories_target / 100.0
                carb_g = carb_kcal / 4.0
        
        if "max" in mnt_fat:
            mnt_fat_max_pct = mnt_fat["max"]
            if mnt_fat_max_pct < fat_pct:
                fat_pct = mnt_fat_max_pct
                fat_kcal = calories_target * fat_pct / 100.0
                fat_g = fat_kcal / 9.0
                # Recalculate carbs
                carb_pct = 100.0 - protein_pct - fat_pct
                carb_kcal = carb_pct * calories_target / 100.0
                carb_g = carb_kcal / 4.0
        
        if "max" in mnt_carb:
            mnt_carb_max_pct = mnt_carb["max"]
            if mnt_carb_max_pct < carb_pct:
                carb_pct = mnt_carb_max_pct
                carb_kcal = carb_pct * calories_target / 100.0
                carb_g = carb_kcal / 4.0
        
        logger.info(f"[Macro Calculation] Final - Protein: {protein_g:.2f}g ({protein_pct:.2f}%), Fat: {fat_g:.2f}g ({fat_pct:.2f}%), Carbs: {carb_g:.2f}g ({carb_pct:.2f}%)")
        
        return {
            "carbohydrates": {
                "g": round(carb_g, 2),
                "percent": round(carb_pct, 2)
            },
            "proteins": {
                "g": round(protein_g, 2),
                "percent": round(protein_pct, 2)
            },
            "fats": {
                "g": round(fat_g, 2),
                "percent": round(fat_pct, 2)
            },
        }

    def calculate_key_micros(
        self,
        client_profile: Dict[str, Any],
        mnt_context: MNTContext
    ) -> Dict[str, Any]:
        """
        Calculate key micronutrient targets.
        
        Args:
            client_profile: Client profile data
            mnt_context: MNT context with micro constraints
            
        Returns:
            Dictionary containing key micronutrient targets
        """
        micro_constraints = mnt_context.micro_constraints or {}
        
        gender = (client_profile.get("gender") or "").lower()
        age = client_profile.get("age")
        conditions = []
        
        # Get micronutrient targets from KB
        micros = {}
        nutrient_ids = get_all_active_nutrient_ids()
        
        if not nutrient_ids:
            raise ValueError("No active nutrients found in micro targets KB")
        
        for nutrient_id in nutrient_ids:
            target = get_micro_target(nutrient_id, gender, age, conditions)
            if target:
                micros[nutrient_id] = target.copy()
        
        # Apply MNT micro constraints
        for key, constraint in micro_constraints.items():
            if key not in micros:
                micros[key] = {}
            for bound, value in constraint.items():
                if bound == "min":
                    micros[key]["min"] = max(micros[key].get("min", value), value)
                elif bound == "max":
                    micros[key]["max"] = min(micros[key].get("max", value), value)
        
        return micros

    def calculate_targets(
        self,
        client_profile: Dict[str, Any],
        mnt_context: MNTContext,
        activity_level: Optional[str] = None,
        diagnosis_context: Optional[Any] = None
    ) -> TargetContext:
        """
        Calculate all nutrition targets.
        
        Args:
            client_profile: Client profile with age, gender, height, weight
            mnt_context: MNT context with constraints
            activity_level: Activity level for energy calculation
            
        Returns:
            TargetContext with calculated calories, macros, and key micros
        """
        logger.info(f"[Target Calculation] Starting target calculation")
        
        # Calculate calories
        calories_info = self.calculate_calories(client_profile, mnt_context, activity_level)
        calories_target = calories_info.get("calories_target")
        calculation_source = calories_info.get("calculation_source")
        
        # Calculate macros
        macros = self.calculate_macros(calories_target, client_profile, mnt_context, diagnosis_context)
        
        # Calculate key micros
        key_micros = self.calculate_key_micros(client_profile, mnt_context)
        
        logger.info(f"[Target Calculation] Complete - Calories: {calories_target:.2f} kcal, Source: {calculation_source}")
        
        return TargetContext(
            assessment_id=mnt_context.assessment_id,
            calories_target=calories_target,
            macros=macros,
            key_micros=key_micros,
            calculation_source=calculation_source
        )
