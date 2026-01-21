"""
Meal Structure Engine.

Generates structural skeleton of daily meal plan (no food items).
Defines meal count, timing windows, calorie allocation, and protein distribution.
"""
from typing import Dict, List, Any, Optional
from uuid import UUID
from datetime import timedelta

from app.platform.core.context import TargetContext, MealStructureContext
from app.platform.engines.meal_structure_engine.schemas import (
    BehavioralPreferences,
    ClientScheduleInput,
    NutritionTargetsInput,
    MealStructureOutput,
)
from app.platform.engines.meal_structure_engine.validators import (
    validate_time_format,
    parse_time,
    add_minutes,
    add_hours,
    detect_timing_overlaps,
    validate_dinner_before_sleep,
)
from app.platform.engines.meal_structure_engine.kb_meal_structure import (
    get_meal_count_by_calories,
    get_meal_count_by_fasting_window,
    get_meal_timing_rule,
    get_calorie_allocation_by_context,
    get_dinner_before_sleep_hours,
    _load_meal_count_rules,
)


class MealStructureEngine:
    """
    Meal Structure Engine.
    
    Responsibility:
    - Generate structural skeleton of daily meal plan (no food items)
    - Define number of meals, meal names, timing windows
    - Allocate calories per meal
    - Distribute protein across meals
    - Generate macro guardrails per meal
    - Validate and rebalance structure
    
    Inputs:
    - TargetContext (nutrition targets)
    - Assessment snapshot (client context, behavioral preferences)
    
    Outputs:
    - MealStructureContext with complete meal structure
    
    Rules:
    - Deterministic — same input → same output
    - Fully testable — no hidden state
    - Constraint-first — nutrition safety > preference
    - Human-biology aligned — sleep & digestion matter
    - All rules and thresholds loaded dynamically from KB JSON files
    """
    
    def __init__(self):
        """Initialize meal structure engine."""
        pass
    
    def generate_structure(
        self,
        target_context: TargetContext,
        assessment_snapshot: Dict[str, Any],
        client_preferences: Optional[Dict[str, Any]] = None
    ) -> MealStructureContext:
        """
        Generate meal structure.
        
        Args:
            target_context: Target context with nutrition targets
            assessment_snapshot: Assessment snapshot with client context
            client_preferences: Optional behavioral preferences override
            
        Returns:
            MealStructureContext with meal structure
            
        Raises:
            ValueError: If required inputs are missing or invalid
        """
        # Step 1: Extract and validate inputs
        client_context = self._extract_client_context(assessment_snapshot)
        behavioral_prefs = self._extract_behavioral_preferences(
            assessment_snapshot,
            client_preferences
        )
        nutrition_targets = self._extract_nutrition_targets(target_context)
        
        # Step 2: Determine meal count
        meal_count = self._determine_meal_count(
            nutrition_targets.target_calories,
            behavioral_prefs
        )
        
        # Step 3: Assign meal names
        meal_names = self._assign_meal_names(meal_count, behavioral_prefs)
        
        # Step 4: Calculate timing windows
        timing_windows = self._calculate_timing_windows(
            meal_names,
            client_context,
            behavioral_prefs,
            assessment_snapshot  # Pass for Ayurveda constraints (Bug 7.1)
        )
        
        # Step 5: Calculate energy weights (relative allocation, sum = 1.0)
        # Extract goals from assessment snapshot for weight loss adjustments
        goals = assessment_snapshot.get("goals", {}) if assessment_snapshot else {}
        
        energy_weight = self._calculate_energy_weights(
            meal_names,
            goals=goals,  # Pass goals for weight loss adjustments
            assessment_snapshot=assessment_snapshot  # Pass for rule selection
        )
        
        # Step 6: Validate structure
        validation_flags = self._validate_structure(
            energy_weight,
            timing_windows,
            behavioral_prefs,
            client_context
        )
        
        return MealStructureContext(
            assessment_id=target_context.assessment_id,
            meal_count=meal_count,
            meals=meal_names,
            timing_windows=timing_windows,
            energy_weight=energy_weight,
            flags=validation_flags
        )
    
    # --- Input Extraction Methods ----------------------------------------------
    
    def _extract_rule_selection_context(
        self,
        assessment_snapshot: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract context for KB rule selection from assessment snapshot.
        
        Args:
            assessment_snapshot: Assessment snapshot dictionary
            
        Returns:
            Dictionary with medical_conditions, activity_level, and age
        """
        medical_conditions = []
        activity_level = None
        age = None
        
        if assessment_snapshot:
            # Extract medical conditions from clinical_data.medical_history.conditions
            clinical_data = assessment_snapshot.get("clinical_data", {})
            medical_history = clinical_data.get("medical_history", {})
            if isinstance(medical_history, dict):
                conditions = medical_history.get("conditions", [])
                if isinstance(conditions, list):
                    medical_conditions = [str(c).lower() for c in conditions if c]
            
            # Extract activity level and age from client_context
            client_context = assessment_snapshot.get("client_context", {})
            activity_level = client_context.get("activity_level")
            age = client_context.get("age")
            if age is not None:
                try:
                    age = int(age)
                except (ValueError, TypeError):
                    age = None
        
        return {
            "medical_conditions": medical_conditions if medical_conditions else None,
            "activity_level": activity_level,
            "age": age
        }
    
    def _extract_client_context(
        self,
        assessment_snapshot: Dict[str, Any]
    ) -> ClientScheduleInput:
        """
        Extract and validate client context from assessment snapshot.
        
        Args:
            assessment_snapshot: Assessment snapshot dictionary
            
        Returns:
            ClientScheduleInput with validated schedule data
            
        Raises:
            ValueError: If required fields are missing
        """
        client_context = assessment_snapshot.get("client_context", {})
        
        wake_time = client_context.get("wake_time")
        sleep_time = client_context.get("sleep_time")
        
        if not wake_time or not sleep_time:
            raise ValueError(
                "wake_time and sleep_time are required in client_context. "
                "Please ensure these fields are collected during client creation."
            )
        
        work_schedule = client_context.get("work_schedule")
        
        return ClientScheduleInput(
            wake_time=wake_time,
            sleep_time=sleep_time,
            work_schedule=work_schedule
        )
    
    def _extract_behavioral_preferences(
        self,
        assessment_snapshot: Dict[str, Any],
        client_preferences: Optional[Dict[str, Any]] = None
    ) -> BehavioralPreferences:
        """
        Extract behavioral preferences from assessment snapshot.
        
        Args:
            assessment_snapshot: Assessment snapshot dictionary
            client_preferences: Optional preferences override
            
        Returns:
            BehavioralPreferences with defaults applied
        """
        lifestyle_data = assessment_snapshot.get("lifestyle_data", {})
        meal_prefs = lifestyle_data.get("meal_preferences", {})
        
        # Use client_preferences override if provided
        if client_preferences:
            meal_prefs = {**meal_prefs, **client_preferences}
        
        return BehavioralPreferences(**meal_prefs)
    
    def _extract_nutrition_targets(
        self,
        target_context: TargetContext
    ) -> NutritionTargetsInput:
        """
        Extract and validate nutrition targets from TargetContext.
        
        Note: Only calories_target is required for meal count calculation.
        Other macros are not needed for Meal Structure Engine (nutrition-agnostic).
        
        Args:
            target_context: Target context with nutrition targets
            
        Returns:
            NutritionTargetsInput with validated targets
            
        Raises:
            ValueError: If calories_target is missing (needed for meal count)
        """
        if not target_context.calories_target:
            raise ValueError("target_calories is required in TargetContext for meal count calculation")
        
        # Extract protein for schema validation (even though not used for allocation)
        # Support both new format (fixed "g" value) and old format (min_g/max_g ranges)
        proteins = target_context.macros.get("proteins", {}) if target_context.macros else {}
        protein_g = proteins.get("g") or proteins.get("max_g") or proteins.get("min_g")
        
        if not protein_g or protein_g <= 0:
            raise ValueError("protein target is required in macros (must be > 0)")
        
        # Extract other macros (optional, for schema validation)
        carbs = target_context.macros.get("carbohydrates", {}) if target_context.macros else {}
        fats = target_context.macros.get("fats", {}) if target_context.macros else {}
        
        # Helper function to extract macro value (new format first, then fallback to old format)
        def get_macro_g(macro_dict):
            return macro_dict.get("g") or macro_dict.get("max_g") or macro_dict.get("min_g")
        
        return NutritionTargetsInput(
            target_calories=target_context.calories_target,
            target_protein_g=protein_g,  # Required for schema validation
            target_carbs_g=get_macro_g(carbs),
            target_fat_g=get_macro_g(fats),
            priority_macro=None,
            constraint_flags=[]
        )
    
    # --- Core Logic Methods (to be implemented in Phase B) --------------------
    
    def _determine_meal_count(
        self,
        calories_target: float,
        behavioral_prefs: BehavioralPreferences
    ) -> int:
        """
        Determine number of meals based on rules.
        
        Decision hierarchy:
        1. User-specified meal count
        2. Fasting window–derived count
        3. Rule-based calculation
        
        Args:
            calories_target: Target calories per day
            behavioral_prefs: Behavioral preferences
            
        Returns:
            Number of meals (1-7)
        """
        # Get min/max from KB
        rules = _load_meal_count_rules()
        min_meals = None
        max_meals = None
        for rule in rules:
            if rule.get("is_default", False):
                min_meals = rule.get("min_meals")
                max_meals = rule.get("max_meals")
                break
        
        if min_meals is None or max_meals is None:
            raise ValueError("Meal count rules missing min_meals or max_meals in default rule")
        
        # Priority 1: User-specified meal count
        if behavioral_prefs.explicit_meal_count is not None:
            meal_count = behavioral_prefs.explicit_meal_count
            return max(min_meals, min(max_meals, meal_count))
        
        # Priority 2: Fasting window–derived count
        if behavioral_prefs.fasting_window:
            meal_count = get_meal_count_by_fasting_window(behavioral_prefs.fasting_window)
            if meal_count is not None:
                return max(min_meals, min(max_meals, meal_count))
        
        # Priority 3: Rule-based calculation from KB
        base_meals = get_meal_count_by_calories(calories_target)
        
        # Ensure within max_meals constraint
        max_meals = behavioral_prefs.max_meals
        return min(base_meals, max_meals)
    
    def _assign_meal_names(
        self,
        meal_count: int,
        behavioral_prefs: BehavioralPreferences
    ) -> List[str]:
        """
        Assign meal names based on meal count and preferences.
        
        Args:
            meal_count: Number of meals
            behavioral_prefs: Behavioral preferences
            
        Returns:
            List of meal names (e.g., ["breakfast", "lunch", "snack", "dinner"])
        """
        meal_names = []
        
        # Always include breakfast
        meal_names.append("breakfast")
        
        # For 2+ meals, include lunch
        if meal_count >= 2:
            meal_names.append("lunch")
        
        # For 3+ meals, include dinner
        if meal_count >= 3:
            meal_names.append("dinner")
        
        # Remaining slots are snacks
        remaining = meal_count - len(meal_names)
        if remaining > 0:
            if behavioral_prefs.snack_preference:
                # Add snacks
                for i in range(1, remaining + 1):
                    meal_names.append(f"snack{i}")
            else:
                # Distribute remaining slots to main meals
                # Add more lunch/dinner slots
                if remaining >= 1:
                    meal_names.insert(1, "lunch2")  # Second lunch
                if remaining >= 2:
                    meal_names.append("dinner2")  # Second dinner
        
        return meal_names
    
    def _calculate_timing_windows(
        self,
        meal_names: List[str],
        client_context: ClientScheduleInput,
        behavioral_prefs: BehavioralPreferences,
        assessment_snapshot: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[str]]:
        """
        Calculate timing windows for each meal.
        
        Rules:
        - Breakfast: 30-90 min after wake
        - Lunch: 4-5 hrs after breakfast
        - Snack: 2-3 hrs after meal
        - Dinner: ≥3 hrs before sleep
        
        Args:
            meal_names: List of meal names
            client_context: Client schedule context
            behavioral_prefs: Behavioral preferences
            
        Returns:
            Dictionary of meal names to [start_time, end_time] lists
        """
        timing_windows = {}
        wake_time = parse_time(client_context.wake_time)
        sleep_time = parse_time(client_context.sleep_time)
        
        # Handle case where sleep time is next day (e.g., 23:00)
        if sleep_time < wake_time:
            sleep_time = sleep_time + timedelta(days=1)
        
        # Track last meal end time for calculating next meal
        last_meal_end = wake_time
        
        for meal_name in meal_names:
            meal_lower = meal_name.lower()
            
            # Get timing rule from KB
            timing_rule = None
            if "breakfast" in meal_lower:
                timing_rule = get_meal_timing_rule("breakfast")
            elif "lunch" in meal_lower:
                timing_rule = get_meal_timing_rule("lunch")
            elif "snack" in meal_lower:
                timing_rule = get_meal_timing_rule("snack")
            elif "dinner" in meal_lower:
                timing_rule = get_meal_timing_rule("dinner")
            
            if not timing_rule:
                # Try default
                timing_rule = get_meal_timing_rule("default")
            
            if not timing_rule:
                raise ValueError(f"No timing rule found for meal type: {meal_name}")
            
            rule_type = timing_rule.get("timing_rule")
            if not rule_type:
                raise ValueError(f"Timing rule missing 'timing_rule' field for meal type: {meal_name}")
            
            if rule_type == "relative_to_wake":
                # Breakfast-style: relative to wake time
                start_offset = timing_rule.get("start_offset_minutes")
                end_offset = timing_rule.get("end_offset_minutes")
                if start_offset is None or end_offset is None:
                    raise ValueError(f"Timing rule missing offset values for meal type: {meal_name}")
                start = add_minutes(wake_time, start_offset)
                end = add_minutes(wake_time, end_offset)
                timing_windows[meal_name] = [
                    start.strftime("%H:%M"),
                    end.strftime("%H:%M")
                ]
                last_meal_end = end
            
            elif rule_type == "relative_to_previous_meal":
                # Lunch/Snack-style: relative to previous meal
                start_offset = timing_rule.get("start_offset_hours")
                end_offset = timing_rule.get("end_offset_hours")
                
                # Check if fallback to wake time is needed
                breakfast_exists = any("breakfast" in m.lower() for m in meal_names[:meal_names.index(meal_name)])
                if not breakfast_exists and timing_rule.get("fallback_rule") == "relative_to_wake":
                    # Use fallback
                    start_offset = timing_rule.get("fallback_start_offset_hours")
                    end_offset = timing_rule.get("fallback_end_offset_hours")
                
                if start_offset is None or end_offset is None:
                    raise ValueError(f"Timing rule missing offset values for meal type: {meal_name}")
                    start = add_hours(wake_time, start_offset)
                    end = add_hours(wake_time, end_offset)
                else:
                    start = add_hours(last_meal_end, start_offset)
                    end = add_hours(last_meal_end, end_offset)
                
                # NEW: Validate snack doesn't extend past sleep_time (Bug 5.1)
                if "snack" in meal_lower:
                    # Snacks should end at least 1 hour before sleep time
                    max_snack_end = sleep_time - timedelta(hours=1)
                    
                    # Handle day rollover: if end is on next day but sleep_time is current day
                    if end < start:  # End time rolled over to next day
                        # Compare end time (as next day) with sleep_time
                        end_next_day = end
                        if sleep_time < wake_time:
                            sleep_time_comparison = sleep_time + timedelta(days=1)
                        else:
                            sleep_time_comparison = sleep_time
                        
                        if end_next_day > sleep_time_comparison - timedelta(hours=1):
                            # Snack extends past sleep - adjust or skip
                            end = sleep_time - timedelta(hours=1)
                            window_duration = timing_rule.get("window_duration_hours", 1.0)
                            start = end - timedelta(hours=window_duration)
                            
                            # Ensure snack doesn't overlap with previous meal
                            if start < last_meal_end:
                                # Skip this snack - no room before sleep
                                continue  # Skip adding to timing_windows
                    else:
                        # Normal case: end is same day
                        if end > max_snack_end:
                            # Adjust snack to end before sleep
                            end = max_snack_end
                            window_duration = timing_rule.get("window_duration_hours", 1.0)
                            if window_duration:
                                start = end - timedelta(hours=window_duration)
                            else:
                                start = end - timedelta(hours=1)  # Default 1 hour window
                            
                            # Ensure snack doesn't overlap with previous meal
                            if start < last_meal_end:
                                # Skip snack if no room
                                continue  # Skip adding to timing_windows
                
                timing_windows[meal_name] = [
                    start.strftime("%H:%M"),
                    end.strftime("%H:%M")
                ]
                last_meal_end = end
            
            elif rule_type == "relative_to_sleep":
                # Dinner-style: relative to sleep time
                min_hours_before = timing_rule.get("min_hours_before_sleep")
                window_duration = timing_rule.get("window_duration_hours")
                min_hours_after_previous = timing_rule.get("min_hours_after_previous_meal")
                
                if min_hours_before is None or window_duration is None:
                    raise ValueError(f"Timing rule missing required values for meal type: {meal_name}")
                if min_hours_after_previous is None:
                    min_hours_after_previous = 1  # Default minimum gap
                
                # Calculate backwards from sleep time
                dinner_end = add_hours(sleep_time, -min_hours_before)
                dinner_start = add_hours(dinner_end, -window_duration)
                
                # Ensure dinner doesn't overlap with previous meal
                if dinner_start < last_meal_end:
                    # Shift dinner earlier
                    dinner_start = add_hours(last_meal_end, min_hours_after_previous)
                    dinner_end = add_hours(dinner_start, window_duration)
                
                # Ensure dinner ends well before sleep (at least 3 hours)
                if dinner_end >= sleep_time - timedelta(hours=3):
                    # Dinner too close to sleep, adjust
                    dinner_end = sleep_time - timedelta(hours=3)
                    dinner_start = dinner_end - timedelta(hours=window_duration)
                    if dinner_start < last_meal_end:
                        # No room for dinner - adjust start
                        dinner_start = last_meal_end + timedelta(hours=min_hours_after_previous)
                        dinner_end = dinner_start + timedelta(hours=window_duration)
                        # Re-check if still too close to sleep
                        if dinner_end >= sleep_time - timedelta(hours=3):
                            dinner_end = sleep_time - timedelta(hours=3)
                            dinner_start = dinner_end - timedelta(hours=window_duration)
                
                timing_windows[meal_name] = [
                    dinner_start.strftime("%H:%M"),
                    dinner_end.strftime("%H:%M")
                ]
                last_meal_end = dinner_end
        
        # FINAL VALIDATION: Ensure no meal window extends past sleep_time (Bug 5.1)
        validated_windows = {}
        for meal_name, window in timing_windows.items():
            start_str, end_str = window
            start_time = parse_time(start_str)
            end_time = parse_time(end_str)
            
            # Handle day rollover for end_time
            if end_time < start_time:
                end_time = end_time + timedelta(days=1)
            
            meal_lower = meal_name.lower()
            
            # Skip meals that end after sleep_time (for snacks) or too close (for dinner)
            if "snack" in meal_lower:
                # Snacks should end at least 1 hour before sleep
                max_snack_end = sleep_time - timedelta(hours=1)
                if sleep_time < wake_time:
                    max_snack_end = max_snack_end + timedelta(days=1)
                
                if end_time > max_snack_end:
                    continue  # Skip snack - extends past allowed time
                    
            elif "dinner" in meal_lower:
                # Dinner should end at least 3 hours before sleep
                max_dinner_end = sleep_time - timedelta(hours=3)
                if sleep_time < wake_time:
                    max_dinner_end = max_dinner_end + timedelta(days=1)
                
                if end_time > max_dinner_end:
                    # Adjust dinner to end before sleep
                    end_time = sleep_time - timedelta(hours=3)
                    if sleep_time < wake_time:
                        end_time = end_time - timedelta(days=1)
                    
                    start_time = end_time - timedelta(hours=2)  # 2-hour dinner window
                    
                    # Check if adjusted start overlaps with previous meal
                    # (We'll assume it's okay if it passed earlier validation)
            
            validated_windows[meal_name] = [
                start_time.strftime("%H:%M"),
                end_time.strftime("%H:%M")
            ]
        
        # NEW: Apply Ayurveda timing constraints (Bug 7.1)
        validated_windows = self._apply_ayurveda_timing_constraints(
            validated_windows, assessment_snapshot, sleep_time
        )
        
        return validated_windows
    
    def _apply_ayurveda_timing_constraints(
        self,
        timing_windows: Dict[str, List[str]],
        assessment_snapshot: Optional[Dict[str, Any]],
        sleep_time: timedelta
    ) -> Dict[str, List[str]]:
        """
        Apply Ayurveda-based meal timing constraints (Bug 7.1).
        
        Kapha dosha: Avoid heavy meals after sunset (18:00), no late-night snacks
        Pitta dosha: Avoid eating during peak pitta hours (10:00-14:00, 22:00-02:00)
        Vata dosha: Regular meal timing, avoid skipping meals
        
        Args:
            timing_windows: Current meal timing windows
            assessment_snapshot: Assessment snapshot (for Ayurveda data)
            sleep_time: Sleep time for reference
            
        Returns:
            Adjusted timing windows with Ayurveda constraints applied
        """
        if not assessment_snapshot:
            return timing_windows
        
        # Extract Ayurveda data from assessment snapshot
        ayurveda_data = assessment_snapshot.get("ayurveda_data", {})
        ayurveda_assessment = ayurveda_data.get("ayurveda_assessment", {})
        vikriti_notes = ayurveda_data.get("vikriti_notes", {})
        
        # Extract imbalanced doshas if available
        imbalanced_doshas = []
        if isinstance(vikriti_notes, dict):
            vikriti = vikriti_notes.get("vikriti") or {}
            if isinstance(vikriti, dict):
                imbalanced_doshas = vikriti.get("imbalanced_doshas", [])
        
        adjusted_windows = timing_windows.copy()
        
        # Apply Ayurveda timing constraints based on imbalanced doshas (Bug 7.1)
        for meal_name, window in adjusted_windows.items():
            if not window or len(window) < 2:
                continue
            
            start_str, end_str = window
            start_time = parse_time(start_str)
            end_time = parse_time(end_str)
            
            # Handle day rollover
            if end_time < start_time:
                end_time = end_time + timedelta(days=1)
            
            meal_lower = meal_name.lower()
            
            # Kapha dosha: Avoid heavy meals after sunset (18:00), no late-night snacks
            if "kapha" in [d.lower() for d in imbalanced_doshas]:
                sunset_hour = 18
                if "dinner" in meal_lower or "snack" in meal_lower:
                    # Move dinner/snack earlier if after sunset
                    if start_time.hour >= sunset_hour:
                        # Adjust to end before sunset
                        new_end = start_time.replace(hour=sunset_hour - 1, minute=0)
                        window_duration = end_time - start_time
                        new_start = new_end - window_duration
                        if new_start.hour >= 0:
                            adjusted_windows[meal_name] = [
                                new_start.strftime("%H:%M"),
                                new_end.strftime("%H:%M")
                            ]
            
            # Pitta dosha: Avoid eating during peak pitta hours (10:00-14:00, 22:00-02:00)
            if "pitta" in [d.lower() for d in imbalanced_doshas]:
                # Peak pitta hours: 10:00-14:00 and 22:00-02:00
                start_hour = start_time.hour
                end_hour = end_time.hour if end_time.hour < 24 else end_time.hour - 24
                
                # Check if meal overlaps with peak pitta hours
                overlaps_peak = (
                    (10 <= start_hour < 14) or (10 <= end_hour < 14) or
                    (22 <= start_hour <= 23) or (0 <= end_hour < 2) or
                    (end_time.hour >= 24 and end_time.hour - 24 < 2)
                )
                
                if overlaps_peak and "lunch" not in meal_lower:  # Lunch is exception
                    # Shift meal to avoid peak pitta hours
                    if start_hour >= 10 and start_hour < 14:
                        # Shift to after 14:00
                        new_start = start_time.replace(hour=14, minute=0)
                        window_duration = end_time - start_time
                        new_end = new_start + window_duration
                        adjusted_windows[meal_name] = [
                            new_start.strftime("%H:%M"),
                            new_end.strftime("%H:%M")
                        ]
                    elif start_hour >= 22 or end_hour < 2:
                        # Shift to before 22:00
                        new_end = start_time.replace(hour=21, minute=59)
                        window_duration = end_time - start_time
                        new_start = new_end - window_duration
                        if new_start.hour >= 0:
                            adjusted_windows[meal_name] = [
                                new_start.strftime("%H:%M"),
                                new_end.strftime("%H:%M")
                            ]
            
            # Vata dosha: Regular meal timing, avoid skipping meals (enforced by meal count)
            # No specific timing adjustments needed, but ensure regularity
            # This is handled by meal count and spacing
        
        return adjusted_windows
    
    def _calculate_energy_weights(
        self,
        meal_names: List[str],
        goals: Optional[Dict[str, Any]] = None,
        assessment_snapshot: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Calculate energy weights per meal (relative allocation, sum = 1.0).
        
        Uses same KB rules as calorie allocation, but returns weights (0.0-1.0) instead of calories.
        This makes Meal Structure Engine nutrition-agnostic.
        
        Args:
            meal_names: List of meal names
            goals: Optional goals dictionary (for weight loss snack adjustment)
            assessment_snapshot: Optional assessment snapshot for context (medical conditions, activity level)
            
        Returns:
            Dictionary of meal names to energy weights (sum = 1.0)
        """
        # Extract context for rule selection
        context = self._extract_rule_selection_context(assessment_snapshot)
        
        # Get appropriate calorie allocation rule from KB based on context
        allocation_rule = get_calorie_allocation_by_context(
            medical_conditions=context["medical_conditions"],
            goals=goals,
            activity_level=context["activity_level"]
        )
        meal_type_percentages = allocation_rule.get("meal_type_percentages", {})
        redistribution_rules = allocation_rule.get("redistribution_rules", {})
        
        # Fallback to default rule's redistribution_rules if current rule doesn't have it
        if not redistribution_rules or "no_snacks" not in redistribution_rules:
            from app.platform.engines.meal_structure_engine.kb_meal_structure import get_default_calorie_allocation
            default_rule = get_default_calorie_allocation()
            default_redistribution = default_rule.get("redistribution_rules", {})
            if default_redistribution:
                redistribution_rules = default_redistribution
        
        energy_weights = {}
        
        # Count meal types
        breakfast_count = sum(1 for m in meal_names if "breakfast" in m.lower())
        lunch_count = sum(1 for m in meal_names if "lunch" in m.lower())
        dinner_count = sum(1 for m in meal_names if "dinner" in m.lower())
        snack_count = sum(1 for m in meal_names if "snack" in m.lower())
        
        # Calculate weights for main meals using KB percentages
        allocated_weight = 0.0
        
        # Breakfast
        breakfast_pct_data = meal_type_percentages.get("breakfast", {})
        if not breakfast_pct_data:
            raise ValueError("Calorie allocation rule missing breakfast percentage")
        breakfast_pct = breakfast_pct_data.get("default")
        if breakfast_pct is None:
            raise ValueError("Calorie allocation rule missing default value for breakfast")
        breakfast_weight = breakfast_pct / 100.0
        for meal in meal_names:
            if "breakfast" in meal.lower():
                energy_weights[meal] = breakfast_weight
                allocated_weight += breakfast_weight
        
        # Lunch
        lunch_pct_data = meal_type_percentages.get("lunch", {})
        if not lunch_pct_data:
            raise ValueError("Calorie allocation rule missing lunch percentage")
        lunch_pct = lunch_pct_data.get("default")
        if lunch_pct is None:
            raise ValueError("Calorie allocation rule missing default value for lunch")
        lunch_weight = lunch_pct / 100.0
        for meal in meal_names:
            if "lunch" in meal.lower():
                energy_weights[meal] = lunch_weight
                allocated_weight += lunch_weight
        
        # Dinner
        dinner_pct_data = meal_type_percentages.get("dinner", {})
        if not dinner_pct_data:
            raise ValueError("Calorie allocation rule missing dinner percentage")
        dinner_pct = dinner_pct_data.get("default")
        if dinner_pct is None:
            raise ValueError("Calorie allocation rule missing default value for dinner")
        dinner_weight = dinner_pct / 100.0
        for meal in meal_names:
            if "dinner" in meal.lower():
                energy_weights[meal] = dinner_weight
                allocated_weight += dinner_weight
        
        # Distribute remaining weight to snacks (adjust for weight loss goals)
        remaining_weight = 1.0 - allocated_weight
        
        # Adjust snack weights for weight loss goals
        primary_goal = goals.get("primary_goal") if goals and isinstance(goals, dict) else None
        
        if snack_count > 0:
            if primary_goal == "weight_loss":
                # For weight loss, limit snack weight to max 10% per snack, max 2 snacks (20% total)
                max_snack_weight_per_snack = 0.10  # 10% per snack
                
                # Limit snack count to max 2 for weight loss
                effective_snack_count = min(snack_count, 2)
                
                # Calculate snack weight (but don't exceed remaining)
                total_snack_weight = min(
                    remaining_weight,
                    max_snack_weight_per_snack * effective_snack_count
                )
                
                per_snack_weight = total_snack_weight / snack_count if snack_count > 0 else 0
                
                # Allocate to snacks
                snacks_allocated = 0
                for meal in meal_names:
                    if "snack" in meal.lower() and snacks_allocated < effective_snack_count:
                        energy_weights[meal] = per_snack_weight
                        snacks_allocated += 1
                    elif "snack" in meal.lower():
                        # Skip extra snacks for weight loss
                        energy_weights[meal] = 0.0
                
                # Redistribute excess snack weight to main meals
                excess_weight = remaining_weight - total_snack_weight
                if excess_weight > 0:
                    # Distribute to main meals proportionally
                    no_snacks_rule = redistribution_rules.get("no_snacks", {})
                    breakfast_redist = no_snacks_rule.get("breakfast", 0.15) if no_snacks_rule else 0.15
                    lunch_redist = no_snacks_rule.get("lunch", 0.40) if no_snacks_rule else 0.40
                    dinner_redist = no_snacks_rule.get("dinner", 0.30) if no_snacks_rule else 0.30
                    
                    if breakfast_count > 0:
                        for meal in meal_names:
                            if "breakfast" in meal.lower():
                                energy_weights[meal] = energy_weights.get(meal, 0) + excess_weight * breakfast_redist
                                break
                    if lunch_count > 0:
                        for meal in meal_names:
                            if "lunch" in meal.lower():
                                energy_weights[meal] = energy_weights.get(meal, 0) + excess_weight * lunch_redist
                                break
                    if dinner_count > 0:
                        for meal in reversed(meal_names):
                            if "dinner" in meal.lower():
                                energy_weights[meal] = energy_weights.get(meal, 0) + excess_weight * dinner_redist
                                break
            else:
                # Normal allocation for non-weight-loss goals
                per_snack_weight = remaining_weight / snack_count if snack_count > 0 else 0
                for meal in meal_names:
                    if "snack" in meal.lower():
                        energy_weights[meal] = per_snack_weight
        elif remaining_weight > 0:
            # No snacks, use redistribution rule from KB (with fallback to defaults)
            no_snacks_rule = redistribution_rules.get("no_snacks", {})
            
            # Use default redistribution if rule not found
            if not no_snacks_rule:
                # Default redistribution: 50% lunch, 30% dinner, 20% breakfast
                lunch_redist = 0.5
                dinner_redist = 0.3
                breakfast_redist = 0.2
            else:
                lunch_redist = no_snacks_rule.get("lunch", 0.5)
                dinner_redist = no_snacks_rule.get("dinner", 0.3)
                breakfast_redist = no_snacks_rule.get("breakfast", 0.2)
            
            # Normalize to ensure sum = 1.0
            total_redist = lunch_redist + dinner_redist + breakfast_redist
            if total_redist > 0:
                lunch_redist = lunch_redist / total_redist
                dinner_redist = dinner_redist / total_redist
                breakfast_redist = breakfast_redist / total_redist
            
            if lunch_count > 0:
                for meal in meal_names:
                    if "lunch" in meal.lower():
                        energy_weights[meal] = energy_weights.get(meal, 0) + remaining_weight * lunch_redist
                        break
            if dinner_count > 0:
                for meal in reversed(meal_names):
                    if "dinner" in meal.lower():
                        energy_weights[meal] = energy_weights.get(meal, 0) + remaining_weight * dinner_redist
                        break
            if breakfast_count > 0 and len(meal_names) > 0:
                energy_weights[meal_names[0]] = energy_weights.get(meal_names[0], 0) + remaining_weight * breakfast_redist
        
        # Normalize to ensure sum = 1.0 (handle floating point precision)
        total_weight = sum(energy_weights.values())
        if total_weight > 0:
            energy_weights = {meal: weight / total_weight for meal, weight in energy_weights.items()}
        else:
            # If all zeros, distribute evenly
            per_meal = 1.0 / len(meal_names) if meal_names else 0
            energy_weights = {meal: per_meal for meal in meal_names}
        
        # Round to 2 decimal places
        energy_weights = {meal: round(weight, 2) for meal, weight in energy_weights.items()}
        
        # Ensure sum is exactly 1.0 after rounding (fix floating point and rounding errors)
        total_rounded = sum(energy_weights.values())
        difference = 1.0 - total_rounded
        
        if abs(difference) > 0.0001:  # Only adjust if difference is significant
            # Find the meal with the largest weight to adjust
            # This preserves meal intent while fixing technical precision
            largest_meal = max(energy_weights.items(), key=lambda x: x[1])[0]
            energy_weights[largest_meal] = round(energy_weights[largest_meal] + difference, 2)
        
        return energy_weights
    
    
    def _validate_structure(
        self,
        energy_weight: Dict[str, float],
        timing_windows: Dict[str, List[str]],
        behavioral_prefs: BehavioralPreferences,
        client_context: ClientScheduleInput
    ) -> List[str]:
        """
        Validate meal structure (nutrition-agnostic validation).
        
        Mandatory checks:
        - Energy weights sum to 1.0 (±0.01 tolerance for floating point)
        - Valid meal timing (no overlaps, dinner ≥3 hrs before sleep)
        
        Args:
            energy_weight: Energy weights per meal (should sum to 1.0)
            timing_windows: Timing windows for each meal
            behavioral_prefs: Behavioral preferences
            client_context: Client schedule context (for sleep time validation)
            
        Returns:
            List of flags indicating adjustments or warnings
        """
        flags = []
        
        # 1. Validate energy weights sum to 1.0
        total_weight = sum(energy_weight.values())
        tolerance = 0.01  # Allow small floating point differences for detection
        
        if abs(total_weight - 1.0) > tolerance:
            # Normalize to fix
            if total_weight > 0:
                # Normalize proportionally
                energy_weight.update({meal: weight / total_weight for meal, weight in energy_weight.items()})
                flags.append(f"energy_weights_normalized_{total_weight:.4f}")
            else:
                # If all zeros, distribute evenly
                per_meal = 1.0 / len(energy_weight) if energy_weight else 0
                energy_weight.update({meal: per_meal for meal in energy_weight.keys()})
                flags.append("energy_weights_reset_to_even_distribution")
        
        # Round to 2 decimal places and ensure exact sum = 1.0
        energy_weight.update({meal: round(weight, 2) for meal, weight in energy_weight.items()})
        total_rounded = sum(energy_weight.values())
        difference = 1.0 - total_rounded
        
        if abs(difference) > 0.0001:  # Only adjust if difference is significant
            # Adjust the largest weight to make sum exactly 1.0
            # This preserves meal intent while fixing technical precision
            largest_meal = max(energy_weight.items(), key=lambda x: x[1])[0]
            energy_weight[largest_meal] = round(energy_weight[largest_meal] + difference, 2)
            flags.append(f"energy_weights_adjusted_for_rounding_{difference:.4f}")
        
        # 2. Validate meal timing - detect overlaps
        overlaps = detect_timing_overlaps(timing_windows)
        if overlaps:
            overlap_pairs = ", ".join([f"{m1}-{m2}" for m1, m2 in overlaps])
            flags.append(f"timing_overlaps_detected_{overlap_pairs}")
        
        # 3. Validate dinner timing (threshold from KB)
        min_hours_before_sleep = get_dinner_before_sleep_hours()
        sleep_time = client_context.sleep_time
        for meal_name, window in timing_windows.items():
            if "dinner" in meal_name.lower() and len(window) == 2:
                dinner_end = window[1]
                is_valid, hours_before = validate_dinner_before_sleep(
                    dinner_end,
                    sleep_time,
                    min_hours_before_sleep=min_hours_before_sleep
                )
                
                if not is_valid:
                    flags.append(f"dinner_too_close_to_sleep_{hours_before:.1f}hrs")
        
        return flags

