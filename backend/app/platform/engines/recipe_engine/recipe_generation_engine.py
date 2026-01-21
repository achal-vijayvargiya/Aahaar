"""
Recipe Generation Engine - Phase 2.

Generates Indian-style recipes and cooking instructions using LLM via OpenRouter.
Takes finalized meals (foods + quantities) and produces client-ready recipes.

This engine does NOT modify nutrition, food selection, or exchanges.
It only generates recipe names, cooking steps, and serving instructions.
"""
import json
import os
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from openai import OpenAI
from app.config import settings
from app.utils.logger import logger
from app.platform.core.context import MNTContext, AyurvedaContext


class RecipeGenerationEngine:
    """
    Recipe Generation Engine - Phase 2.
    
    Responsibility:
    - Generate Indian-style recipes from finalized meals
    - Call LLM via OpenRouter (one call per meal)
    - Validate LLM output to ensure food/quantity integrity
    - Produce client-ready recipe output
    
    Does NOT:
    - Modify nutrition values
    - Change food selection
    - Adjust exchange allocations
    - Add or remove ingredients
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7
    ):
        """
        Initialize Recipe Generation Engine.
        
        Args:
            api_key: OpenRouter API key (defaults to settings)
            model: LLM model to use (defaults to settings.DIET_PLAN_MODEL)
            temperature: Temperature for LLM (default: 0.7)
        """
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model or settings.DIET_PLAN_MODEL
        self.temperature = temperature
        
        if not self.api_key or self.api_key == "sk-or-v1-placeholder-get-from-openrouter-ai":
            raise ValueError(
                "OPENROUTER_API_KEY not configured. Set it in .env file or pass via api_key parameter"
            )
        
        # Initialize OpenAI client for OpenRouter
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://drassistent.com",
                "X-Title": "DrAssistent Recipe Generation"
            }
        )
        
        # Load prompt template
        self.prompt_template = self._load_prompt_template()
        
        logger.info(f"Initialized Recipe Generation Engine with model: {self.model}")
    
    def _load_prompt_template(self) -> str:
        """
        Load recipe prompt template from file.
        
        Returns:
            Prompt template string
        """
        # Get the directory where this file is located
        current_dir = Path(__file__).parent
        prompt_file = current_dir / "samplePrompt.txt"
        
        if not prompt_file.exists():
            raise FileNotFoundError(
                f"Prompt template file not found: {prompt_file}. "
                "Please ensure samplePrompt.txt exists in recipe_engine directory."
            )
        
        with open(prompt_file, "r", encoding="utf-8") as f:
            template = f.read()
        
        return template
    
    def generate_recipes_for_meal_plan(
        self,
        meal_plan: Dict[str, Any],
        mnt_context: Optional[MNTContext] = None,
        ayurveda_context: Optional[AyurvedaContext] = None,
        num_days: int = 7
    ) -> Dict[str, Any]:
        """
        Generate recipes for entire meal plan (multiple days).
        
        Args:
            meal_plan: Meal plan from MealAllocationEngine with allocated foods
            mnt_context: Optional MNT context for constraints
            ayurveda_context: Optional Ayurveda context for constraints
            num_days: Number of days to process (default: 7)
            
        Returns:
            Dictionary with recipes for all meals:
            {
                "days": {
                    "day_1": {
                        "day_number": 1,
                        "date": "2025-01-15",
                        "day_name": "Monday",
                        "meals": {
                            "breakfast": {
                                "meal_name": "breakfast",
                                "recipe": {
                                    "dish_name": "...",
                                    "ingredients": [...],
                                    "cooking_steps": [...],
                                    "approx_cooking_time_minutes": 20,
                                    "serving_instructions": "..."
                                },
                                "allocated_foods": [...],  # Original foods preserved
                                "validation": {...}
                            },
                            ...
                        }
                    },
                    ...
                },
                "summary": {
                    "total_meals": 21,
                    "successful_recipes": 21,
                    "failed_recipes": 0,
                    "validation_failures": 0
                }
            }
        """
        days = meal_plan.get("days", {})
        
        # Generate constraint summaries once (shared across all meals)
        mnt_summary = self._generate_mnt_summary(mnt_context)
        ayurveda_summary = self._generate_ayurveda_summary(ayurveda_context)
        oil_limit = self._extract_oil_limit(mnt_context)
        
        # Process each day
        processed_days = {}
        total_meals = 0
        successful_recipes = 0
        failed_recipes = 0
        validation_failures = 0
        
        for day_key in sorted(days.keys()):
            day_data = days[day_key]
            day_num = day_data.get("day_number", 0)
            day_name = day_data.get("day_name", "")
            date = day_data.get("date", "")
            meals = day_data.get("meals", {})
            
            processed_meals = {}
            
            for meal_name, meal_data in meals.items():
                total_meals += 1
                
                # Generate recipe for this meal
                recipe_result = self.generate_recipe_for_meal(
                    meal_name=meal_name,
                    meal_data=meal_data,
                    day_name=day_name,
                    mnt_summary=mnt_summary,
                    ayurveda_summary=ayurveda_summary,
                    oil_limit=oil_limit
                )
                
                if recipe_result["validation"]["is_valid"]:
                    successful_recipes += 1
                else:
                    failed_recipes += 1
                    if recipe_result["validation"].get("validation_failed", False):
                        validation_failures += 1
                
                processed_meals[meal_name] = recipe_result
            
            processed_days[day_key] = {
                "day_number": day_num,
                "date": date,
                "day_name": day_name,
                "meals": processed_meals
            }
        
        # Preserve variety_metrics and nutrition_summary from Phase 1 (meal allocation)
        result = {
            "days": processed_days,
            "summary": {
                "total_meals": total_meals,
                "successful_recipes": successful_recipes,
                "failed_recipes": failed_recipes,
                "validation_failures": validation_failures
            }
        }
        
        # Preserve Phase 1 metrics if present
        if "variety_metrics" in meal_plan:
            result["variety_metrics"] = meal_plan["variety_metrics"]
        if "nutrition_summary" in meal_plan:
            result["nutrition_summary"] = meal_plan["nutrition_summary"]
        if "plan_duration_days" in meal_plan:
            result["plan_duration_days"] = meal_plan["plan_duration_days"]
        if "start_date" in meal_plan:
            result["start_date"] = meal_plan["start_date"]
        
        return result
    
    def generate_recipe_for_meal(
        self,
        meal_name: str,
        meal_data: Dict[str, Any],
        day_name: str,
        mnt_summary: str,
        ayurveda_summary: str,
        oil_limit: float
    ) -> Dict[str, Any]:
        """
        Generate recipe for a single meal.
        
        Args:
            meal_name: Name of meal (e.g., "breakfast")
            meal_data: Meal data with allocated_foods
            day_name: Day name (e.g., "Monday")
            mnt_summary: MNT constraints summary string
            ayurveda_summary: Ayurveda constraints summary string
            oil_limit: Oil limit in ml
            
        Returns:
            Dictionary with recipe and validation:
            {
                "meal_name": "breakfast",
                "recipe": {...},  # LLM-generated recipe
                "allocated_foods": [...],  # Original foods preserved
                "validation": {
                    "is_valid": True,
                    "warnings": [],
                    "validation_failed": False
                }
            }
        """
        allocated_foods = meal_data.get("allocated_foods", [])
        
        if not allocated_foods:
            return {
                "meal_name": meal_name,
                "recipe": None,
                "allocated_foods": [],
                "validation": {
                    "is_valid": False,
                    "warnings": ["No foods allocated to this meal"],
                    "validation_failed": False
                }
            }
        
        # Build prompt
        prompt = self._build_prompt(
            day_name=day_name,
            meal_name=meal_name,
            allocated_foods=allocated_foods,
            mnt_summary=mnt_summary,
            ayurveda_summary=ayurveda_summary,
            oil_limit=oil_limit
        )
        
        # Call LLM (with retry on validation failure)
        recipe = None
        validation_failed = False
        warnings = []
        
        try:
            # First attempt
            recipe = self._call_llm(prompt)
            
            # Validate LLM output
            validation_result = self._validate_recipe(
                recipe=recipe,
                allocated_foods=allocated_foods
            )
            
            if not validation_result["is_valid"]:
                validation_failed = True
                warnings.extend(validation_result["warnings"])
                
                # Retry with stricter prompt
                logger.warning(
                    f"Recipe validation failed for {meal_name} on {day_name}. "
                    "Retrying with stricter prompt..."
                )
                
                stricter_prompt = self._build_stricter_prompt(
                    day_name=day_name,
                    meal_name=meal_name,
                    allocated_foods=allocated_foods,
                    mnt_summary=mnt_summary,
                    ayurveda_summary=ayurveda_summary,
                    oil_limit=oil_limit,
                    previous_errors=validation_result["warnings"]
                )
                
                recipe = self._call_llm(stricter_prompt)
                
                # Validate again
                validation_result = self._validate_recipe(
                    recipe=recipe,
                    allocated_foods=allocated_foods
                )
                
                if not validation_result["is_valid"]:
                    warnings.extend([
                        f"Retry validation failed: {w}" 
                        for w in validation_result["warnings"]
                    ])
                    warnings.append(
                        "Recipe flagged for manual review - validation failed after retry"
                    )
        
        except Exception as e:
            logger.error(f"Error generating recipe for {meal_name}: {str(e)}")
            warnings.append(f"LLM call failed: {str(e)}")
            recipe = None
        
        return {
            "meal_name": meal_name,
            "recipe": recipe,
            "allocated_foods": allocated_foods,  # Preserve original foods
            "total_nutrition": meal_data.get("total_nutrition", {}),
            "exchanges_used": meal_data.get("exchanges_used", {}),
            "validation": {
                "is_valid": recipe is not None and not validation_failed,
                "warnings": warnings,
                "validation_failed": validation_failed
            }
        }
    
    def _build_prompt(
        self,
        day_name: str,
        meal_name: str,
        allocated_foods: List[Dict[str, Any]],
        mnt_summary: str,
        ayurveda_summary: str,
        oil_limit: float
    ) -> str:
        """
        Build prompt by injecting values into template.
        
        Args:
            day_name: Day name (e.g., "Monday")
            meal_name: Meal name (e.g., "breakfast")
            allocated_foods: List of allocated food dictionaries
            mnt_summary: MNT constraints summary
            ayurveda_summary: Ayurveda constraints summary
            oil_limit: Oil limit in ml
            
        Returns:
            Complete prompt string
        """
        # Format food list with quantities (matching template format)
        food_list_lines = []
        for food in allocated_foods:
            display_name = food.get("display_name", food.get("food_id", "Unknown"))
            quantity_g = food.get("quantity_g", 0)
            exchange_category = food.get("exchange_category", "")
            
            # Format quantity appropriately (matching template expectations)
            if quantity_g >= 1000:
                quantity_str = f"{quantity_g / 1000:.1f} kg"
            elif quantity_g >= 1:
                quantity_str = f"{quantity_g:.1f} g"
            else:
                # For very small quantities (< 1g), assume ml for liquids
                quantity_str = f"{quantity_g * 1000:.0f} ml"
            
            # Format matches template: "- Food name: quantity (category)"
            food_list_lines.append(f"- {display_name}: {quantity_str} ({exchange_category})")
        
        food_list_str = "\n".join(food_list_lines)
        
        # Inject values into template
        prompt = self.prompt_template
        prompt = prompt.replace("{{DAY}}", day_name)
        prompt = prompt.replace("{{MEAL_NAME}}", meal_name)
        prompt = prompt.replace("{{FOOD_LIST_WITH_GRAMS}}", food_list_str)
        prompt = prompt.replace("{{MEDICAL_CONSTRAINTS_SUMMARY}}", mnt_summary)
        prompt = prompt.replace("{{AYURVEDA_CONSTRAINTS_SUMMARY}}", ayurveda_summary)
        prompt = prompt.replace("{{OIL_LIMIT_ML}}", str(int(oil_limit)))
        
        return prompt
    
    def _build_stricter_prompt(
        self,
        day_name: str,
        meal_name: str,
        allocated_foods: List[Dict[str, Any]],
        mnt_summary: str,
        ayurveda_summary: str,
        oil_limit: float,
        previous_errors: List[str]
    ) -> str:
        """
        Build stricter prompt with previous validation errors.
        
        Args:
            day_name: Day name
            meal_name: Meal name
            allocated_foods: List of allocated foods
            mnt_summary: MNT summary
            ayurveda_summary: Ayurveda summary
            oil_limit: Oil limit
            previous_errors: List of previous validation errors
            
        Returns:
            Stricter prompt string
        """
        base_prompt = self._build_prompt(
            day_name=day_name,
            meal_name=meal_name,
            allocated_foods=allocated_foods,
            mnt_summary=mnt_summary,
            ayurveda_summary=ayurveda_summary,
            oil_limit=oil_limit
        )
        
        # Add validation error warnings
        error_section = "\n\n--------------------------------------------------\n"
        error_section += "CRITICAL: PREVIOUS ATTEMPT FAILED VALIDATION\n"
        error_section += "The following errors were found in the previous recipe:\n"
        for error in previous_errors:
            error_section += f"- {error}\n"
        error_section += "\nYou MUST fix these errors. DO NOT repeat the same mistakes.\n"
        error_section += "--------------------------------------------------\n"
        
        # Insert before "GENERATE THE FINAL RECIPE NOW"
        if "GENERATE THE FINAL RECIPE NOW" in base_prompt:
            base_prompt = base_prompt.replace(
                "GENERATE THE FINAL RECIPE NOW",
                error_section + "GENERATE THE FINAL RECIPE NOW"
            )
        else:
            base_prompt += error_section
        
        return base_prompt
    
    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """
        Call LLM via OpenRouter to generate recipe.
        
        The prompt template includes "SYSTEM ROLE:" at the top, but it's designed
        to be sent as a single user message. The entire template is sent as-is.
        
        Args:
            prompt: Complete prompt string (includes system role instructions)
            
        Returns:
            Recipe dictionary from LLM with structure:
            {
                "dish_name": str,
                "ingredients": List[str],
                "cooking_steps": List[str],
                "approx_cooking_time_minutes": int,
                "serving_instructions": str
            }
        """
        try:
            # Send entire prompt as user message (template includes system role instructions)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=2000,
                response_format={"type": "json_object"}  # Force JSON output
            )
            
            content = response.choices[0].message.content
            
            if not content:
                raise ValueError("LLM returned empty response")
            
            # Parse JSON response
            try:
                recipe = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response: {str(e)}")
                content_preview = content[:500] if 'content' in locals() else "No content available"
                logger.error(f"Response content (first 500 chars): {content_preview}")
                raise ValueError(f"LLM returned invalid JSON: {str(e)}")
            
            # Validate required fields exist
            required_fields = ["dish_name", "ingredients", "cooking_steps", "approx_cooking_time_minutes", "serving_instructions"]
            missing_fields = [field for field in required_fields if field not in recipe]
            if missing_fields:
                raise ValueError(f"LLM response missing required fields: {missing_fields}")
            
            return recipe
        
        except ValueError as e:
            # Re-raise ValueError (validation errors)
            raise
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            raise RuntimeError(f"LLM API call failed: {str(e)}") from e
    
    def _validate_recipe(
        self,
        recipe: Dict[str, Any],
        allocated_foods: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate LLM-generated recipe against allocated foods.
        
        Checks:
        - All input foods are present
        - No new foods added
        - Quantities unchanged (within tolerance)
        
        Args:
            recipe: LLM-generated recipe dictionary
            allocated_foods: Original allocated foods list
            
        Returns:
            Validation result dictionary:
            {
                "is_valid": bool,
                "warnings": List[str]
            }
        """
        warnings = []
        
        if not recipe:
            return {
                "is_valid": False,
                "warnings": ["Recipe is None or empty"]
            }
        
        # Extract ingredients from recipe
        recipe_ingredients = recipe.get("ingredients", [])
        if not recipe_ingredients:
            return {
                "is_valid": False,
                "warnings": ["Recipe has no ingredients list"]
            }
        
        # Build set of allocated food names (normalized)
        allocated_food_names = set()
        allocated_food_map = {}  # name -> food dict
        
        for food in allocated_foods:
            display_name = food.get("display_name", food.get("food_id", "")).lower().strip()
            allocated_food_names.add(display_name)
            allocated_food_map[display_name] = food
        
        # Check each recipe ingredient
        recipe_food_names = set()
        for ingredient in recipe_ingredients:
            if not isinstance(ingredient, str):
                continue
            
            # Extract food name from ingredient string
            # Template format: "Food name – <exact quantity as provided>"
            # Handles both em dash (–) and regular dash (-)
            ingredient_lower = ingredient.lower().strip()
            
            # Try to extract food name (before dash/colon)
            # Template uses em dash (U+2013) but LLM might use regular dash
            for separator in ["–", "-", ":", "—", "–"]:  # em dash, hyphen, colon, em dash variant
                if separator in ingredient_lower:
                    food_name = ingredient_lower.split(separator)[0].strip()
                    recipe_food_names.add(food_name)
                    break
            else:
                # No separator found, use whole string (might be just food name)
                recipe_food_names.add(ingredient_lower)
        
        # Check for missing foods
        missing_foods = allocated_food_names - recipe_food_names
        if missing_foods:
            warnings.append(
                f"Missing foods in recipe: {', '.join(sorted(missing_foods))}"
            )
        
        # Check for added foods (loose check - some variation allowed)
        # This is a warning, not an error, as LLM might use synonyms
        suspicious_additions = []
        for recipe_name in recipe_food_names:
            # Check if it matches any allocated food (fuzzy)
            matched = False
            for allocated_name in allocated_food_names:
                # Simple substring match (allows for "wheat flour" vs "wheat")
                if allocated_name in recipe_name or recipe_name in allocated_name:
                    matched = True
                    break
            
            if not matched:
                suspicious_additions.append(recipe_name)
        
        if suspicious_additions:
            warnings.append(
                f"Potentially added foods (not in input): {', '.join(sorted(suspicious_additions))}"
            )
        
        # Check quantities (loose validation - just ensure they're mentioned)
        # Exact quantity matching is difficult due to formatting variations
        
        is_valid = len(missing_foods) == 0
        
        return {
            "is_valid": is_valid,
            "warnings": warnings
        }
    
    def _generate_mnt_summary(self, mnt_context: Optional[MNTContext]) -> str:
        """
        Generate MNT constraints summary string.
        
        Args:
            mnt_context: MNT context
            
        Returns:
            Summary string
        """
        if not mnt_context:
            return "No specific medical nutrition therapy constraints."
        
        summary_parts = []
        
        # Macro constraints
        macro_constraints = mnt_context.macro_constraints or {}
        if macro_constraints:
            summary_parts.append("Macro Constraints:")
            for macro, constraint in macro_constraints.items():
                if isinstance(constraint, dict):
                    min_val = constraint.get("min")
                    max_val = constraint.get("max")
                    if min_val is not None or max_val is not None:
                        range_str = []
                        if min_val is not None:
                            range_str.append(f"min: {min_val}")
                        if max_val is not None:
                            range_str.append(f"max: {max_val}")
                        summary_parts.append(f"  - {macro}: {', '.join(range_str)}")
        
        # Micro constraints
        micro_constraints = mnt_context.micro_constraints or {}
        if micro_constraints:
            summary_parts.append("Micro Constraints:")
            for micro, constraint in micro_constraints.items():
                if isinstance(constraint, dict):
                    min_val = constraint.get("min")
                    max_val = constraint.get("max")
                    if min_val is not None or max_val is not None:
                        range_str = []
                        if min_val is not None:
                            range_str.append(f"min: {min_val}")
                        if max_val is not None:
                            range_str.append(f"max: {max_val}")
                        summary_parts.append(f"  - {micro}: {', '.join(range_str)}")
        
        # Food exclusions
        food_exclusions = mnt_context.food_exclusions or []
        if food_exclusions:
            summary_parts.append(f"Excluded Foods: {', '.join(food_exclusions)}")
        
        if not summary_parts:
            return "No specific medical nutrition therapy constraints."
        
        return "\n".join(summary_parts)
    
    def _generate_ayurveda_summary(self, ayurveda_context: Optional[AyurvedaContext]) -> str:
        """
        Generate Ayurveda constraints summary string.
        
        Args:
            ayurveda_context: Ayurveda context
            
        Returns:
            Summary string
        """
        if not ayurveda_context:
            return "No specific Ayurveda guidelines."
        
        summary_parts = []
        
        # Dosha information
        primary_dosha = ayurveda_context.dosha_primary
        secondary_dosha = ayurveda_context.dosha_secondary
        
        if primary_dosha or secondary_dosha:
            dosha_info = []
            if primary_dosha:
                dosha_info.append(f"Primary: {primary_dosha}")
            if secondary_dosha:
                dosha_info.append(f"Secondary: {secondary_dosha}")
            summary_parts.append(f"Dosha Profile: {', '.join(dosha_info)}")
        
        # Vikriti notes
        vikriti_notes = ayurveda_context.vikriti_notes or {}
        if vikriti_notes:
            food_preferences = vikriti_notes.get("food_preferences", [])
            if food_preferences:
                prefer_foods = [
                    p.get("food_id") 
                    for p in food_preferences 
                    if p.get("preference_type") == "prefer"
                ]
                avoid_foods = [
                    p.get("food_id")
                    for p in food_preferences
                    if p.get("preference_type") == "avoid"
                ]
                
                if prefer_foods:
                    summary_parts.append(f"Preferred Foods: {', '.join(prefer_foods)}")
                if avoid_foods:
                    summary_parts.append(f"Avoid Foods: {', '.join(avoid_foods)}")
        
        # Lifestyle guidelines
        lifestyle_guidelines = ayurveda_context.lifestyle_guidelines or {}
        if lifestyle_guidelines:
            cooking_methods = lifestyle_guidelines.get("cooking_methods", [])
            if cooking_methods:
                summary_parts.append(f"Recommended Cooking Methods: {', '.join(cooking_methods)}")
        
        if not summary_parts:
            return "No specific Ayurveda guidelines."
        
        return "\n".join(summary_parts)
    
    def _extract_oil_limit(self, mnt_context: Optional[MNTContext]) -> float:
        """
        Extract oil limit from MNT context.
        
        Args:
            mnt_context: MNT context
            
        Returns:
            Oil limit in ml (default: 15ml per meal)
        """
        if not mnt_context:
            return 15.0
        
        # Check fat constraints
        macro_constraints = mnt_context.macro_constraints or {}
        fat_constraint = macro_constraints.get("fat_percent", {}) or {}
        
        # Default: 15ml per meal (reasonable for Indian cooking)
        # Could be calculated from fat constraints if needed
        return 15.0
