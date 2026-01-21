"""
LLM-based script to populate missing values in food KB tables.

Populates:
1. kb_food_nutrition_base.glycemic_properties (GI, GL, classification)
2. kb_food_master.common_serving_unit (e.g., "1 cup", "1 medium", "100g")
3. kb_food_master.common_serving_size_g (grams for common serving)

Uses batch processing (5-10 foods per API call) for cost efficiency.

Usage:
    python -m app.platform.knowledge_base.foods.import_missing_values_llm
    python -m app.platform.knowledge_base.foods.import_missing_values_llm --dry-run
    python -m app.platform.knowledge_base.foods.import_missing_values_llm --batch-size 10 --model qwen/qwen-2.5-7b-instruct
    python -m app.platform.knowledge_base.foods.import_missing_values_llm --resume-from 50
"""

import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
from decimal import Decimal

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.platform.data.models.kb_food_master import KBFoodMaster
from app.platform.data.models.kb_food_nutrition_base import KBFoodNutritionBase
from app.utils.logger import logger
from app.config import settings

try:
    from openai import OpenAI
except ImportError:
    raise ImportError("openai package not installed. Run: pip install openai")


class LLMFoodValueExtractor:
    """Extract missing food values using LLM with batch processing."""
    
    FALLBACK_MODELS = [
        "meta-llama/llama-3.3-70b-instruct:free",
        "anthropic/claude-3.5-sonnet",
        "meta-llama/llama-3.1-70b-instruct",
        "google/gemini-pro-1.5",
    ]
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model or "anthropic/claude-3.5-sonnet"  # Better accuracy for GI values
        self.current_model = self.model
        
        if not self.api_key or self.api_key == "sk-or-v1-placeholder-get-from-openrouter-ai":
            raise ValueError("OPENROUTER_API_KEY not configured. Set it in .env file or pass via --api-key")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://drassistent.com",
                "X-Title": "DrAssistent Food Value Extraction"
            }
        )
        
        logger.info(f"Initialized LLM extractor with model: {self.current_model}")
    
    def extract_batch(
        self,
        foods: List[Dict[str, Any]],
        batch_size: int = 10,
        max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Extract missing values for a batch of foods.
        
        Args:
            foods: List of food dictionaries with food_id, display_name, category, macros
            batch_size: Number of foods per API call (not used here, batch is pre-split)
            max_retries: Maximum retry attempts
        
        Returns:
            List of result dictionaries with food_id, glycemic_index, common_serving_unit, common_serving_size_g
        """
        models_to_try = [self.current_model] + self.FALLBACK_MODELS
        
        for attempt in range(max_retries):
            for model_attempt in models_to_try:
                try:
                    result = self._call_llm_batch(foods, model_attempt)
                    if result:
                        self.current_model = model_attempt  # Update to working model
                        return result
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "rate" in error_str.lower():
                        if model_attempt != models_to_try[-1]:
                            logger.warning(f"Rate limit on {model_attempt}, trying next model...")
                            time.sleep(2)
                            continue
                        else:
                            wait_time = (2 ** attempt) * 5
                            logger.warning(f"All models rate limited. Waiting {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                    else:
                        logger.error(f"Error with {model_attempt}: {e}")
                        if model_attempt == models_to_try[-1] and attempt == max_retries - 1:
                            # Last attempt failed, return None results
                            logger.error(f"Failed to extract values for batch after {max_retries} attempts")
                            return [
                                {
                                    "food_id": food["food_id"],
                                    "glycemic_index": None,
                                    "common_serving_unit": None,
                                    "common_serving_size_g": None
                                }
                                for food in foods
                            ]
        
        # If all retries failed
        return [
            {
                "food_id": food["food_id"],
                "glycemic_index": None,
                "common_serving_unit": None,
                "common_serving_size_g": None
            }
            for food in foods
        ]
    
    def _call_llm_batch(
        self,
        foods: List[Dict[str, Any]],
        model: str
    ) -> List[Dict[str, Any]]:
        """Call LLM for a batch of foods. Tries tools first, falls back to JSON mode."""
        prompt = self._build_batch_prompt(foods)
        
        # Try with tools first (for models that support it)
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a nutrition expert. You MUST provide Glycemic Index (GI) values (0-150) for ALL foods with carbohydrates. Only return null for GI if the food has absolutely zero carbohydrates (like pure oils or meat without carbs). Use values from Sydney University GI Database or International GI Tables."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                # Don't use response_format with tools (conflicts)
                tools=[{
                    "type": "function",
                    "function": {
                        "name": "get_food_missing_values",
                        "description": "Get missing values for foods: GI, serving unit, and serving size",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "foods": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "food_id": {"type": "string", "description": "Food ID"},
                                        "glycemic_index": {
                                            "type": ["integer", "null"],
                                            "description": "Glycemic Index value (0-150) from research databases. MUST provide a number for foods with carbohydrates. Only use null if food has absolutely zero carbohydrates (like pure oil or meat without carbs)."
                                        },
                                            "common_serving_unit": {
                                                "type": ["string", "null"],
                                                "description": "Common household serving unit (e.g., '1 cup', '1 medium', '1 piece', '100g', '1 tbsp')"
                                            },
                                            "common_serving_size_g": {
                                                "type": ["number", "null"],
                                                "description": "Weight in grams for the common serving unit"
                                            }
                                        },
                                        "required": ["food_id"]
                                    }
                                }
                            },
                            "required": ["foods"]
                        }
                    }
                }],
                tool_choice={"type": "function", "function": {"name": "get_food_missing_values"}}
            )
            
            # Parse response
            message = response.choices[0].message
            if message.tool_calls:
                # New format: tool_calls
                tool_call = message.tool_calls[0]
                if tool_call.function.name == "get_food_missing_values":
                    args = json.loads(tool_call.function.arguments)
                    return args.get("foods", [])
            else:
                # Fallback: try to parse as JSON directly from content
                content = message.content
                if content:
                    try:
                        data = json.loads(content)
                        if isinstance(data, dict) and "foods" in data:
                            return data["foods"]
                    except json.JSONDecodeError:
                        pass
            
        except Exception as e:
            error_str = str(e)
            # If model doesn't support tools (404) or has other issues, fall back to JSON mode
            if "404" in error_str or "tool" in error_str.lower() or "endpoints" in error_str.lower():
                logger.info(f"Model {model} doesn't support tools, falling back to JSON mode")
                return self._call_llm_batch_json_mode(foods, model)
            else:
                logger.error(f"Error calling LLM with model {model}: {e}")
                raise
        
        # If we got here but no valid response, try JSON mode
        logger.warning("No valid tool response, trying JSON mode fallback")
        return self._call_llm_batch_json_mode(foods, model)
    
    def _call_llm_batch_json_mode(
        self,
        foods: List[Dict[str, Any]],
        model: str
    ) -> List[Dict[str, Any]]:
        """Call LLM using JSON mode (for models that don't support tools)."""
        prompt = self._build_batch_prompt_json(foods)
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                        {
                            "role": "system",
                            "content": "You are a nutrition expert. You MUST provide Glycemic Index (GI) values (0-150) for ALL foods with carbohydrates. Only return null for GI if the food has absolutely zero carbohydrates. Return ONLY valid JSON, no other text."
                        },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            # Parse JSON response
            content = response.choices[0].message.content
            if content:
                # Remove markdown code blocks if present
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                try:
                    data = json.loads(content)
                    if isinstance(data, dict) and "foods" in data:
                        return data["foods"]
                    elif isinstance(data, list):
                        return data
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    logger.error(f"Response content: {content[:500]}")
            
            return []
        
        except Exception as e:
            # If response_format is not supported, try without it
            if "response_format" in str(e).lower():
                logger.info(f"Model {model} doesn't support response_format, trying without it")
                try:
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a nutrition expert. You MUST provide Glycemic Index (GI) values (0-150) for ALL foods with carbohydrates. Only return null for GI if the food has absolutely zero carbohydrates. Return ONLY valid JSON in the exact format specified, no other text."
                            },
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1
                    )
                    
                    content = response.choices[0].message.content
                    if content:
                        # Remove markdown code blocks if present
                        if "```json" in content:
                            content = content.split("```json")[1].split("```")[0].strip()
                        elif "```" in content:
                            content = content.split("```")[1].split("```")[0].strip()
                        
                        try:
                            data = json.loads(content)
                            if isinstance(data, dict) and "foods" in data:
                                return data["foods"]
                            elif isinstance(data, list):
                                return data
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse JSON response: {e}")
                            logger.error(f"Response content: {content[:500]}")
                    
                    return []
                except Exception as e2:
                    logger.error(f"Error in JSON mode fallback: {e2}")
                    raise
            else:
                logger.error(f"Error calling LLM in JSON mode with model {model}: {e}")
                raise
    
    def _build_batch_prompt(self, foods: List[Dict[str, Any]]) -> str:
        """Build prompt for batch of foods."""
        prompt = "You are a nutrition expert. Extract GI, serving unit, and serving size for each food.\n\n"
        prompt += "**CRITICAL RULE**: If a food contains ANY carbohydrates, you MUST provide a GI value (0-150). "
        prompt += "Only use null for GI if the food has ZERO carbs (pure oils, pure meat, water).\n\n"
        prompt += "**GI Reference Values** (from Sydney University GI Database):\n"
        prompt += "- White rice (cooked): 73\n"
        prompt += "- Brown rice (cooked): 68\n"
        prompt += "- Apple: 36\n"
        prompt += "- Banana: 51\n"
        prompt += "- Wheat roti/chapati: 62\n"
        prompt += "- Sugar: 65\n"
        prompt += "- Potato (boiled): 78\n"
        prompt += "- Lentils/dal: 30-40\n"
        prompt += "- Most vegetables: 10-30\n"
        prompt += "- Most fruits: 30-60\n\n"
        prompt += "**Serving Information**: Provide typical Indian household measures:\n"
        prompt += "- '1 cup' for liquids, cooked grains, vegetables\n"
        prompt += "- '1 medium' for fruits (apple, banana, orange)\n"
        prompt += "- '1 piece' for roti, idli, dosa\n"
        prompt += "- '100g' for items measured by weight\n"
        prompt += "- '1 tbsp' for oils, ghee, condiments\n\n"
        prompt += "**Foods to process**:\n\n"
        
        for idx, food in enumerate(foods, 1):
            food_id = food.get("food_id", "")
            display_name = food.get("display_name", "")
            
            prompt += f"{idx}. Food ID: {food_id}\n"
            prompt += f"   Name: {display_name}\n"
            prompt += "   ---\n"
        
        prompt += "\n**REMINDER**: Every food with carbohydrates MUST have a GI value. Do NOT return null for GI unless carbs are zero."
        prompt += "\nProvide data for ALL foods in the batch."
        
        return prompt
    
    def _build_batch_prompt_json(self, foods: List[Dict[str, Any]]) -> str:
        """Build prompt for batch of foods with explicit JSON schema (for JSON mode)."""
        prompt = "You are a nutrition expert. Extract GI, serving unit, and serving size for each food.\n\n"
        prompt += "**CRITICAL RULE**: If a food contains ANY carbohydrates, you MUST provide a GI value (0-150). "
        prompt += "Only use null for GI if the food has ZERO carbs (pure oils, pure meat, water).\n\n"
        prompt += "**GI Reference Values** (from Sydney University GI Database):\n"
        prompt += "- White rice (cooked): 73\n"
        prompt += "- Brown rice (cooked): 68\n"
        prompt += "- Apple: 36\n"
        prompt += "- Banana: 51\n"
        prompt += "- Wheat roti/chapati: 62\n"
        prompt += "- Sugar: 65\n"
        prompt += "- Potato (boiled): 78\n"
        prompt += "- Lentils/dal: 30-40\n"
        prompt += "- Most vegetables: 10-30\n"
        prompt += "- Most fruits: 30-60\n\n"
        prompt += "**Foods to process**:\n\n"
        
        for idx, food in enumerate(foods, 1):
            food_id = food.get("food_id", "")
            display_name = food.get("display_name", "")
            
            prompt += f"{idx}. Food ID: {food_id}\n"
            prompt += f"   Name: {display_name}\n"
            prompt += "   ---\n"
        
        prompt += "\n\nReturn ONLY valid JSON in this exact format (no markdown, no code blocks):\n"
        prompt += "{\n"
        prompt += '  "foods": [\n'
        prompt += '    {"food_id": "example1", "glycemic_index": 73, "common_serving_unit": "1 cup", "common_serving_size_g": 200},\n'
        prompt += '    {"food_id": "example2", "glycemic_index": 36, "common_serving_unit": "1 medium", "common_serving_size_g": 182},\n'
        prompt += '    {"food_id": "example3", "glycemic_index": null, "common_serving_unit": "1 tbsp", "common_serving_size_g": 14}\n'
        prompt += '  ]\n'
        prompt += '}\n\n'
        prompt += "**REMINDER**: Every food with carbohydrates MUST have a GI value. Do NOT return null for GI unless carbs are zero."
        prompt += "\nProvide data for ALL foods in the batch."
        
        return prompt
    
    def _retry_food_gi(
        self,
        food: Any,
        carbs_g: float,
        dry_run: bool
    ) -> Optional[Dict[str, Any]]:
        """Retry getting GI for a single food with a very explicit prompt."""
        prompt = f"""You are a nutrition expert. I need the Glycemic Index (GI) for this specific food.

Food Name: {food.display_name}
Food ID: {food.food_id}
Category: {food.category or 'Unknown'}
Carbohydrates: {carbs_g}g per 100g

**CRITICAL**: This food has {carbs_g}g of carbohydrates, so it MUST have a GI value (0-150).
Do NOT return null. Provide a GI value based on:
- Sydney University GI Database
- International GI Tables
- Similar foods in the same category

Examples:
- Rice (white): 73, Rice (brown): 68
- Wheat products: 50-70
- Fruits: 30-60
- Vegetables: 10-30
- Legumes/dal: 30-40

Return ONLY a JSON object with this exact format:
{{"food_id": "{food.food_id}", "glycemic_index": <number 0-150>}}

Do NOT return null for glycemic_index. Provide a number."""
        
        try:
            # Use JSON mode for retry
            response = self.client.chat.completions.create(
                model=self.current_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a nutrition expert. You MUST provide a GI value (0-150) for any food with carbohydrates. Never return null for GI if carbs exist."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if content:
                # Remove markdown if present
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                try:
                    data = json.loads(content)
                    if isinstance(data, dict) and data.get("glycemic_index") is not None:
                        return data
                except json.JSONDecodeError:
                    pass
            
            return None
        except Exception as e:
            logger.error(f"Error in retry for {food.food_id}: {e}")
            return None


def safe_float(value: Any) -> float:
    """Safely convert value to float, returning 0.0 if None or invalid."""
    if value is None:
        return 0.0
    try:
        if isinstance(value, Decimal):
            return float(value)
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def calculate_glycemic_load(gi: Optional[int], carbs_g: float, fiber_g: float = 0) -> float:
    """Calculate Glycemic Load per 100g."""
    if gi is None or gi == 0:
        return 0.0
    
    available_carbs = carbs_g - fiber_g
    if available_carbs <= 0:
        return 0.0
    
    glycemic_load = (gi * available_carbs) / 100.0
    return round(glycemic_load, 2)


def classify_gi(gi: Optional[int]) -> str:
    """Classify GI value."""
    if gi is None or gi == 0:
        return "no_gi"
    elif gi < 20:
        return "very_low_gi"
    elif gi < 55:
        return "low_gi"
    elif gi < 70:
        return "medium_gi"
    else:
        return "high_gi"


def update_missing_values(
    db: Session,
    extractor: LLMFoodValueExtractor,
    batch_size: int = 10,
    resume_from: int = 0,
    dry_run: bool = False
) -> Dict[str, int]:
    """Update missing values for all foods."""
    stats = {
        "total_foods": 0,
        "needs_update": 0,
        "processed": 0,
        "glycemic_updated": 0,
        "serving_unit_updated": 0,
        "serving_size_updated": 0,
        "skipped_no_nutrition": 0,
        "skipped_already_complete": 0,
        "errors": 0,
    }
    
    # Get all foods with nutrition data
    foods = db.query(KBFoodMaster).join(KBFoodNutritionBase).all()
    stats["total_foods"] = len(foods)
    
    logger.info(f"Found {len(foods)} foods with nutrition data")
    logger.info(f"Resuming from index {resume_from}")
    
    # Prepare food data for batch processing
    food_batches = []
    current_batch = []
    
    for idx, food in enumerate(foods[resume_from:], start=resume_from):
        nutrition = food.nutrition
        if not nutrition:
            stats["skipped_no_nutrition"] += 1
            continue
        
        macros = nutrition.macros or {}
        carbs_g = safe_float(macros.get("carbs_g", 0))
        fiber_g = safe_float(macros.get("fiber_g", 0))
        calories_kcal = safe_float(nutrition.calories_kcal)
        
        # Check if already has values
        needs_gi = not nutrition.glycemic_properties or not nutrition.glycemic_properties.get("glycemic_index")
        needs_serving = not food.common_serving_unit or not food.common_serving_size_g
        
        if not needs_gi and not needs_serving:
            stats["skipped_already_complete"] += 1
            continue  # Skip if all values present
        
        stats["needs_update"] += 1
        
        # Only send food_id and display_name to LLM - simpler is better
        food_data = {
            "food_id": food.food_id,
            "display_name": food.display_name,
            # Store carbs_g for GL calculation later (not sent to LLM)
            "_carbs_g": carbs_g,
            "_fiber_g": fiber_g,
        }
        
        current_batch.append(food_data)
        
        if len(current_batch) >= batch_size:
            food_batches.append(current_batch)
            current_batch = []
    
    if current_batch:
        food_batches.append(current_batch)
    
    logger.info(f"Found {stats['needs_update']} foods needing updates")
    logger.info(f"Created {len(food_batches)} batches of up to {batch_size} foods each")
    logger.info(f"Skipped {stats['skipped_already_complete']} foods that already have all values")
    
    if len(food_batches) == 0:
        logger.info("No foods need updates. Exiting.")
        return stats
    
    # Process batches
    for batch_idx, batch in enumerate(food_batches):
        try:
            logger.info(f"\n{'='*70}")
            logger.info(f"Processing batch {batch_idx + 1}/{len(food_batches)} ({len(batch)} foods)...")
            logger.info(f"Foods: {', '.join([f['food_id'] for f in batch])}")
            
            # Extract values using LLM
            results = extractor.extract_batch(batch, batch_size=len(batch))
            
            if not results:
                logger.warning(f"No results returned for batch {batch_idx + 1}")
                stats["errors"] += len(batch)
                continue
            
            # Update database
            for result in results:
                food_id = result.get("food_id")
                if not food_id:
                    continue
                
                food = db.query(KBFoodMaster).filter(
                    KBFoodMaster.food_id == food_id
                ).first()
                
                if not food:
                    logger.warning(f"Food not found: {food_id}")
                    continue
                
                nutrition = food.nutrition
                if not nutrition:
                    continue
                
                # Update glycemic properties
                gi = result.get("glycemic_index")
                if gi is not None:
                    macros = nutrition.macros or {}
                    carbs_g = safe_float(macros.get("carbs_g", 0))
                    fiber_g = safe_float(macros.get("fiber_g", 0))
                    
                    gl = calculate_glycemic_load(gi, carbs_g, fiber_g)
                    classification = classify_gi(gi)
                    
                    glycemic_props = {
                        "glycemic_index": gi,
                        "glycemic_load_per_100g": gl,
                        "glycemic_classification": classification
                    }
                    
                    if dry_run:
                        logger.info(f"  [DRY RUN] Would update GI for {food.food_id}: GI={gi}, GL={gl}, Class={classification}")
                    else:
                        nutrition.glycemic_properties = glycemic_props
                        db.add(nutrition)
                    
                    stats["glycemic_updated"] += 1
                elif gi is None:
                    macros = nutrition.macros or {}
                    carbs_g = safe_float(macros.get("carbs_g", 0))
                    if carbs_g > 0:
                        # LLM returned null but food has carbs - retry with explicit prompt
                        logger.warning(f"  ⚠️  LLM returned null GI for {food_id} ({food.display_name}) but food has {carbs_g}g carbs. Retrying...")
                        retry_result = extractor._retry_food_gi(food, carbs_g, dry_run)
                        if retry_result and retry_result.get("glycemic_index") is not None:
                            gi = retry_result.get("glycemic_index")
                            gl = calculate_glycemic_load(gi, carbs_g, safe_float(macros.get("fiber_g", 0)))
                            classification = classify_gi(gi)
                            glycemic_props = {
                                "glycemic_index": gi,
                                "glycemic_load_per_100g": gl,
                                "glycemic_classification": classification
                            }
                            if dry_run:
                                logger.info(f"  ✓ Retry successful: GI={gi}, GL={gl}, Class={classification}")
                            else:
                                nutrition.glycemic_properties = glycemic_props
                                db.add(nutrition)
                            stats["glycemic_updated"] += 1
                        else:
                            logger.error(f"  ✗ Retry failed for {food_id}. Still null GI.")
                            stats["errors"] += 1
                
                # Update serving unit and size
                serving_unit = result.get("common_serving_unit")
                serving_size_g = result.get("common_serving_size_g")
                
                if serving_unit and serving_size_g:
                    if dry_run:
                        logger.info(f"  [DRY RUN] Would update serving for {food.food_id}: {serving_unit} = {serving_size_g}g")
                    else:
                        food.common_serving_unit = serving_unit
                        food.common_serving_size_g = Decimal(str(serving_size_g))
                        db.add(food)
                    
                    stats["serving_unit_updated"] += 1
                    stats["serving_size_updated"] += 1
                elif serving_unit or serving_size_g:
                    # Partial update
                    if serving_unit:
                        if dry_run:
                            logger.info(f"  [DRY RUN] Would update serving unit for {food.food_id}: {serving_unit}")
                        else:
                            food.common_serving_unit = serving_unit
                            db.add(food)
                        stats["serving_unit_updated"] += 1
                    if serving_size_g:
                        if dry_run:
                            logger.info(f"  [DRY RUN] Would update serving size for {food.food_id}: {serving_size_g}g")
                        else:
                            food.common_serving_size_g = Decimal(str(serving_size_g))
                            db.add(food)
                        stats["serving_size_updated"] += 1
                
                stats["processed"] += 1
            
            # Commit batch
            if not dry_run:
                db.commit()
                logger.info(f"✓ Committed batch {batch_idx + 1}")
            else:
                logger.info(f"✓ [DRY RUN] Would commit batch {batch_idx + 1}")
            
            # Rate limiting delay between batches
            if batch_idx + 1 < len(food_batches):
                time.sleep(2)  # 2 second delay between batches
        
        except Exception as e:
            logger.error(f"Error processing batch {batch_idx + 1}: {e}", exc_info=True)
            stats["errors"] += len(batch)
            if not dry_run:
                db.rollback()
            continue
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="Import missing food values using LLM")
    parser.add_argument("--batch-size", type=int, default=10, 
                       help="Batch size for API calls (5-10 recommended, default: 10)")
    parser.add_argument("--resume-from", type=int, default=0, 
                       help="Resume from food index (default: 0)")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Dry run mode (don't update database)")
    parser.add_argument("--model", type=str, 
                       default="anthropic/claude-3.5-sonnet",
                       help="LLM model to use (default: anthropic/claude-3.5-sonnet for better GI accuracy)")
    parser.add_argument("--api-key", type=str, 
                       help="OpenRouter API key (defaults to OPENROUTER_API_KEY env var)")
    
    args = parser.parse_args()
    
    try:
        extractor = LLMFoodValueExtractor(api_key=args.api_key, model=args.model)
    except ValueError as e:
        logger.error(str(e))
        return
    
    db = SessionLocal()
    
    try:
        stats = update_missing_values(
            db, extractor, args.batch_size, args.resume_from, args.dry_run
        )
        
        logger.info("\n" + "=" * 70)
        logger.info("SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total foods: {stats['total_foods']}")
        logger.info(f"Foods needing updates: {stats['needs_update']}")
        logger.info(f"Processed: {stats['processed']}")
        logger.info(f"Glycemic properties updated: {stats['glycemic_updated']}")
        logger.info(f"Serving unit updated: {stats['serving_unit_updated']}")
        logger.info(f"Serving size updated: {stats['serving_size_updated']}")
        logger.info(f"Skipped (no nutrition): {stats['skipped_no_nutrition']}")
        logger.info(f"Skipped (already complete): {stats['skipped_already_complete']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info("=" * 70)
        logger.info(f"Model used: {extractor.current_model}")
        logger.info(f"Batch size: {args.batch_size}")
        logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
        logger.info("=" * 70)
        
        if args.dry_run:
            logger.info("\nThis was a dry run. Run without --dry-run to update the database.")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        if not args.dry_run:
            db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()

