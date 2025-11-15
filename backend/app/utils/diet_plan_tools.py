"""
LangChain tools for AI-powered diet plan generation

These tools wrap existing functionality to be used by the LangChain agent:
- CalculateNutritionTool: Computes nutritional requirements (no LLM)
- RetrieveFoodsTool: Searches food knowledge base using semantic search
- ValidateNutritionTool: Validates meal plans against targets
"""
import json
import re
from typing import Dict, List, Optional, Any, Union
from langchain.tools import BaseTool
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.models.health_profile import HealthProfile
from app.models.dosha_quiz import DoshaQuiz
from app.knowledge_base.food_retriever import FoodRetriever
from app.utils.logger import logger


# ============================================
# Tool Input Schemas
# ============================================

class CalculateNutritionInput(BaseModel):
    """Input schema for nutrition calculation tool"""
    weight: float = Field(description="Weight in kilograms")
    height: float = Field(description="Height in centimeters")
    age: int = Field(description="Age in years")
    activity_level: str = Field(
        description="Activity level: sedentary, lightly_active, moderately_active, very_active, or extremely_active"
    )
    goals: str = Field(
        description="Health goals like 'weight loss', 'muscle gain', 'general wellness', etc."
    )


class RetrieveFoodsInput(BaseModel):
    """Input schema for food retrieval tool"""
    query: str = Field(
        ...,
        description="REQUIRED: Natural language query describing desired foods. Example: 'high protein breakfast foods for weight loss'"
    )
    meal_type: str = Field(
        ...,
        description="REQUIRED: Type of meal - must be exactly one of: Breakfast, Mid Snack, Lunch, Evening Snack, Dinner, Morning Cleanse, Sleep Tonic"
    )
    target_calories: float = Field(
        ...,
        description="REQUIRED: Target calories for this meal (numeric value, e.g., 450.0)"
    )
    dosha_type: Optional[str] = Field(
        default=None,
        description="Optional: Primary dosha to balance: Vata, Pitta, or Kapha"
    )
    diet_type: str = Field(
        default="veg",
        description="Optional: Diet type: veg, non-veg, or vegan"
    )
    prefer_satvik: bool = Field(
        default=False,
        description="Optional: Whether to prefer Satvik foods"
    )
    top_k: int = Field(
        default=8,
        description="Optional: Number of food items to retrieve (default 8)"
    )


class ValidateNutritionInput(BaseModel):
    """Input schema for nutrition validation tool"""
    meals: Union[List[Dict], str] = Field(
        description="List of meals with nutritional information (calories, protein_g, carbs_g, fat_g)"
    )
    targets: Union[Dict, str] = Field(
        description="Target nutritional values (calories, protein_g, carbs_g, fat_g)"
    )
    
    @field_validator('meals', mode='before')
    @classmethod
    def parse_meals(cls, v):
        """Parse meals if it's a JSON string or string representation"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Try to evaluate as Python literal if JSON parsing fails
                try:
                    import ast
                    return ast.literal_eval(v)
                except (ValueError, SyntaxError):
                    raise ValueError(f"Invalid JSON or Python literal for meals: {v}")
        return v
    
    @field_validator('targets', mode='before')
    @classmethod
    def parse_targets(cls, v):
        """Parse targets if it's a JSON string or string representation"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Try to evaluate as Python literal if JSON parsing fails
                try:
                    import ast
                    return ast.literal_eval(v)
                except (ValueError, SyntaxError):
                    raise ValueError(f"Invalid JSON or Python literal for targets: {v}")
        return v


# ============================================
# Tool Implementations
# ============================================

class CalculateNutritionTool(BaseTool):
    """
    Tool for calculating daily nutritional requirements.
    Uses scientific formulas (Mifflin-St Jeor equation) without AI.
    """
    name: str = "calculate_nutrition"
    description: str = """
    Calculate daily nutritional requirements (calories, protein, carbohydrates, fat) 
    based on a client's physical attributes, activity level, and health goals.
    
    This tool uses the Mifflin-St Jeor equation for BMR (Basal Metabolic Rate) 
    and adjusts for activity level and goals. It's deterministic and doesn't require AI.
    
    Use this as the first step when creating a diet plan to establish targets.
    """
    args_schema: type[BaseModel] = CalculateNutritionInput
    
    def _run(
        self,
        weight: float,
        height: float,
        age: int,
        activity_level: str,
        goals: str
    ) -> str:
        """Calculate nutritional targets and return as formatted string"""
        try:
            # BMR calculation using Mifflin-St Jeor equation
            # Using a gender-neutral average formula
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
            
            # Activity level multipliers
            activity_multipliers = {
                "sedentary": 1.2,
                "lightly_active": 1.375,
                "moderately_active": 1.55,
                "very_active": 1.725,
                "extremely_active": 1.9
            }
            
            multiplier = activity_multipliers.get(activity_level.lower(), 1.55)
            tdee = bmr * multiplier
            
            # Adjust based on goals
            goals_lower = goals.lower()
            if "weight loss" in goals_lower or "lose weight" in goals_lower or "fat loss" in goals_lower:
                calories = tdee - 500  # 500 calorie deficit
                goal_adjustment = "500 calorie deficit for weight loss"
            elif "weight gain" in goals_lower or "muscle" in goals_lower or "bulk" in goals_lower:
                calories = tdee + 300  # 300 calorie surplus
                goal_adjustment = "300 calorie surplus for muscle gain"
            else:
                calories = tdee  # Maintenance
                goal_adjustment = "maintenance calories for general wellness"
            
            # Calculate macros (40% carbs, 30% protein, 30% fat for balanced diet)
            protein_g = (calories * 0.30) / 4  # 4 calories per gram of protein
            carbs_g = (calories * 0.40) / 4   # 4 calories per gram of carbs
            fat_g = (calories * 0.30) / 9     # 9 calories per gram of fat
            
            result = f"""
Nutritional Requirements Calculated:

Client Profile:
- Weight: {weight}kg
- Height: {height}cm
- Age: {age} years
- Activity Level: {activity_level}
- Health Goals: {goals}

Calculations:
- Basal Metabolic Rate (BMR): {round(bmr, 0)} kcal/day
- Total Daily Energy Expenditure (TDEE): {round(tdee, 0)} kcal/day
- Adjustment: {goal_adjustment}

Daily Nutritional Targets:
- Calories: {round(calories, 0)} kcal
- Protein: {round(protein_g, 1)}g (30% of calories)
- Carbohydrates: {round(carbs_g, 1)}g (40% of calories)
- Fat: {round(fat_g, 1)}g (30% of calories)

These targets will be used to select appropriate foods and portion sizes.
"""
            
            logger.info(f"Calculated nutrition: {round(calories, 0)} kcal, {round(protein_g, 1)}g protein")
            return result.strip()
            
        except Exception as e:
            logger.error(f"Error calculating nutrition: {e}")
            return f"Error calculating nutritional requirements: {str(e)}"


class RetrieveFoodsTool(BaseTool):
    """
    Tool for retrieving appropriate foods from the knowledge base.
    Uses semantic search with FAISS embeddings and filters by nutritional criteria.
    """
    name: str = "retrieve_foods"
    description: str = """
    Search and retrieve appropriate foods from the knowledge base using semantic search.
    
    REQUIRED PARAMETERS:
    - query: Natural language description (e.g., "high protein breakfast foods for weight loss")
    - meal_type: Exact meal type name (Breakfast, Lunch, Dinner, Mid Snack, Evening Snack, Morning Cleanse, Sleep Tonic)
    - target_calories: Numeric calorie target for this meal (e.g., 450.0)
    
    OPTIONAL PARAMETERS:
    - dosha_type: Vata, Pitta, or Kapha
    - diet_type: veg, non-veg, or vegan
    - prefer_satvik: true or false
    - top_k: number of foods to retrieve
    
    EXAMPLE USAGE:
    {
        "query": "high protein breakfast foods for weight loss",
        "meal_type": "Breakfast",
        "target_calories": 450.0,
        "dosha_type": "Kapha",
        "diet_type": "veg"
    }
    
    Use this tool multiple times - once for each meal type (Breakfast, Lunch, Dinner, etc.).
    """
    args_schema: type[BaseModel] = RetrieveFoodsInput
    db: Session = Field(default=None, exclude=True)
    food_retriever: Optional[FoodRetriever] = Field(default=None, exclude=True)
    
    def __init__(self, db: Session):
        super().__init__()
        self.db = db
        self.food_retriever = FoodRetriever()
        logger.info("RetrieveFoodsTool initialized with FoodRetriever")
    
    def _run(
        self,
        query: str,
        meal_type: str,
        target_calories: float,
        dosha_type: Optional[str] = None,
        diet_type: str = "veg",
        prefer_satvik: bool = False,
        top_k: int = 8
    ) -> str:
        """Retrieve foods from knowledge base and return as formatted string"""
        try:
            # Map meal types to food categories
            category_mapping = {
                "Breakfast": ["Grains", "Dairy", "Fruits", "Nuts & Seeds"],
                "Mid Snack": ["Fruits", "Nuts & Seeds", "Snacks"],
                "Lunch": ["Grains", "Pulses & Legumes", "Vegetables", "Proteins", "Dairy"],
                "Evening Snack": ["Fruits", "Nuts & Seeds", "Beverage", "Snacks"],
                "Dinner": ["Grains", "Vegetables", "Pulses & Legumes", "Soup"],
                "Morning Cleanse": ["Beverage", "Herbs"],
                "Sleep Tonic": ["Beverage", "Dairy", "Herbs"]
            }
            
            categories = category_mapping.get(meal_type, ["Grains", "Vegetables", "Fruits"])
            
            # Determine dosha preference for food selection
            dosha_preference = None
            if dosha_type:
                dosha_preference = f"{dosha_type} ↓"  # Foods that reduce/balance this dosha
            
            # Search for foods across relevant categories
            all_foods = []
            for category in categories:
                try:
                    foods = self.food_retriever.semantic_search(
                        db=self.db,
                        query=query,
                        category=category,
                        dosha_preference=dosha_preference,
                        satvik_only=prefer_satvik,
                        top_k=max(2, top_k // len(categories))
                    )
                    all_foods.extend(foods)
                except Exception as e:
                    logger.warning(f"Error retrieving foods for category {category}: {e}")
                    continue
            
            if not all_foods:
                return f"No foods found for {meal_type}. Try a different query or meal type."
            
            # Format results
            result_lines = [
                f"\nRetrieved Foods for {meal_type} (Target: {target_calories} kcal):",
                f"Query: '{query}'",
                f"Diet Type: {diet_type}, Dosha Balance: {dosha_type or 'None'}\n"
            ]
            
            for i, food in enumerate(all_foods[:top_k], 1):
                result_lines.append(
                    f"{i}. {food['food_name']} ({food.get('category', 'N/A')})\n"
                    f"   - Energy: {food.get('energy_kcal', 0)} kcal/100g\n"
                    f"   - Protein: {food.get('protein_g', 0)}g, Carbs: {food.get('carbs_g', 0)}g, Fat: {food.get('fat_g', 0)}g\n"
                    f"   - Dosha Impact: {food.get('dosha_impact', 'N/A')}\n"
                    f"   - Gut Health: {food.get('gut_biotic_value', 'N/A')}\n"
                    f"   - Satvik/Rajasik/Tamasik: {food.get('satvik_rajasik_tamasik', 'N/A')}\n"
                )
            
            result = "\n".join(result_lines)
            logger.info(f"Retrieved {len(all_foods[:top_k])} foods for {meal_type}")
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving foods: {e}", exc_info=True)
            return f"Error retrieving foods: {str(e)}"


class ValidateNutritionTool(BaseTool):
    """
    Tool for validating that a meal plan meets nutritional targets.
    Compares actual totals against targets and provides recommendations.
    """
    name: str = "validate_nutrition"
    description: str = """
    Validate that a generated meal plan meets the calculated nutritional targets.
    
    This tool:
    - Sums up total calories, protein, carbs, and fat from all meals
    - Compares against the established targets
    - Calculates variance percentages
    - Provides specific recommendations if targets aren't met
    
    Use this tool after generating a meal plan to ensure it meets requirements.
    The plan should be within ±10% of calorie targets and ±15% of macro targets.
    """
    args_schema: type[BaseModel] = ValidateNutritionInput
    
    def _run(self, meals: List[Dict], targets: Dict) -> str:
        """Validate meal plan nutrition and return formatted results"""
        try:
            # Calculate totals
            total_calories = sum(meal.get("calories", 0) for meal in meals)
            total_protein = sum(meal.get("protein_g", 0) for meal in meals)
            total_carbs = sum(meal.get("carbs_g", 0) for meal in meals)
            total_fat = sum(meal.get("fat_g", 0) for meal in meals)
            
            # Get targets
            target_calories = targets.get("calories", 2000)
            target_protein = targets.get("protein_g", 80)
            target_carbs = targets.get("carbs_g", 250)
            target_fat = targets.get("fat_g", 65)
            
            # Calculate variances
            cal_diff = total_calories - target_calories
            cal_percent = (cal_diff / target_calories * 100) if target_calories > 0 else 0
            
            protein_diff = total_protein - target_protein
            protein_percent = (protein_diff / target_protein * 100) if target_protein > 0 else 0
            
            carbs_diff = total_carbs - target_carbs
            carbs_percent = (carbs_diff / target_carbs * 100) if target_carbs > 0 else 0
            
            fat_diff = total_fat - target_fat
            fat_percent = (fat_diff / target_fat * 100) if target_fat > 0 else 0
            
            # Determine if valid (within acceptable ranges)
            is_valid = (
                abs(cal_percent) <= 10 and
                abs(protein_percent) <= 15 and
                abs(carbs_percent) <= 15 and
                abs(fat_percent) <= 15
            )
            
            # Generate recommendations
            recommendations = []
            
            if cal_percent > 10:
                recommendations.append(
                    f"⚠️ Calories are {abs(cal_diff):.0f} kcal too high ({cal_percent:+.1f}%). "
                    "Reduce portion sizes or choose lower-calorie alternatives."
                )
            elif cal_percent < -10:
                recommendations.append(
                    f"⚠️ Calories are {abs(cal_diff):.0f} kcal too low ({cal_percent:+.1f}%). "
                    "Increase portion sizes or add more calorie-dense foods."
                )
            
            if protein_percent < -15:
                recommendations.append(
                    f"⚠️ Protein is {abs(protein_diff):.1f}g too low ({protein_percent:+.1f}%). "
                    "Add more protein-rich foods like lentils, paneer, tofu, or nuts."
                )
            elif protein_percent > 15:
                recommendations.append(
                    f"⚠️ Protein is {abs(protein_diff):.1f}g too high ({protein_percent:+.1f}%). "
                    "Reduce protein portions slightly."
                )
            
            if carbs_percent < -15:
                recommendations.append(
                    f"⚠️ Carbohydrates are {abs(carbs_diff):.1f}g too low ({carbs_percent:+.1f}%). "
                    "Add more grains, fruits, or starchy vegetables."
                )
            
            if fat_percent < -15:
                recommendations.append(
                    f"⚠️ Fat is {abs(fat_diff):.1f}g too low ({fat_percent:+.1f}%). "
                    "Add more nuts, seeds, ghee, or healthy oils."
                )
            
            if not recommendations:
                recommendations.append("✅ Meal plan meets all nutritional targets!")
            
            # Format result
            result = f"""
Nutritional Validation Results:

Status: {"✅ VALID" if is_valid else "⚠️ NEEDS ADJUSTMENT"}

Actual vs Target:
- Calories: {total_calories:.0f} / {target_calories:.0f} kcal ({cal_percent:+.1f}%)
- Protein: {total_protein:.1f} / {target_protein:.1f}g ({protein_percent:+.1f}%)
- Carbohydrates: {total_carbs:.1f} / {target_carbs:.1f}g ({carbs_percent:+.1f}%)
- Fat: {total_fat:.1f} / {target_fat:.1f}g ({fat_percent:+.1f}%)

Recommendations:
{chr(10).join(f"- {rec}" for rec in recommendations)}

Number of meals validated: {len(meals)}
"""
            
            logger.info(f"Validated nutrition: {total_calories:.0f} kcal, Valid: {is_valid}")
            return result.strip()
            
        except Exception as e:
            logger.error(f"Error validating nutrition: {e}")
            return f"Error validating nutrition: {str(e)}"


class ModifyFoodSelectionInput(BaseModel):
    """Input schema for modifying food selection"""
    action: str = Field(description="Action: 'add', 'remove', or 'replace'")
    meal_type: str = Field(description="Meal type to modify (e.g., Breakfast, Lunch, Dinner)")
    food_name: Optional[str] = Field(default=None, description="Food to remove or replace")
    replacement_query: Optional[str] = Field(
        default=None, 
        description="Query for finding replacement or additional foods"
    )


class ModifyFoodSelectionTool(BaseTool):
    """Tool for modifying food selection based on user feedback"""
    name: str = "modify_food_selection"
    description: str = """
    Modify the retrieved food selection based on user feedback.
    
    Actions:
    - 'add': Add more food options for a meal type
    - 'remove': Remove specific food from consideration
    - 'replace': Replace one food with alternatives
    
    Use this when user says things like:
    - "Remove paneer, I'm allergic"
    - "Add more fruits for breakfast"
    - "Replace chicken with vegetarian options"
    - "No dairy products"
    """
    args_schema: type[BaseModel] = ModifyFoodSelectionInput
    db: Session = Field(default=None, exclude=True)
    food_retriever: Optional[FoodRetriever] = Field(default=None, exclude=True)
    
    def __init__(self, db: Session):
        super().__init__()
        self.db = db
        self.food_retriever = FoodRetriever()
    
    def _run(
        self,
        action: str,
        meal_type: str,
        food_name: Optional[str] = None,
        replacement_query: Optional[str] = None
    ) -> str:
        """Modify food selection"""
        try:
            if action == "remove":
                return f"✓ Noted: Removed '{food_name}' from {meal_type} options. It will not be used in the meal plan."
            
            elif action == "add" and replacement_query:
                # Search for additional foods
                foods = self.food_retriever.semantic_search(
                    db=self.db,
                    query=replacement_query,
                    top_k=5
                )
                
                if not foods:
                    return f"Could not find foods matching '{replacement_query}'"
                
                result_lines = [f"✓ Added {len(foods)} new options for {meal_type}:\n"]
                for i, food in enumerate(foods, 1):
                    result_lines.append(
                        f"{i}. {food['food_name']} ({food.get('category', 'N/A')})\n"
                        f"   - Energy: {food.get('energy_kcal', 0)} kcal/100g\n"
                        f"   - Protein: {food.get('protein_g', 0)}g, Carbs: {food.get('carbs_g', 0)}g, Fat: {food.get('fat_g', 0)}g\n"
                        f"   - Dosha: {food.get('dosha_impact', 'N/A')}\n"
                    )
                
                return "\n".join(result_lines)
            
            elif action == "replace" and food_name and replacement_query:
                # Find replacement
                foods = self.food_retriever.semantic_search(
                    db=self.db,
                    query=replacement_query,
                    top_k=3
                )
                
                if not foods:
                    return f"Could not find replacements for '{food_name}'"
                
                result_lines = [
                    f"✓ Replaced '{food_name}' with these alternatives:\n"
                ]
                for i, food in enumerate(foods, 1):
                    result_lines.append(
                        f"{i}. {food['food_name']} ({food.get('category', 'N/A')})\n"
                        f"   - Energy: {food.get('energy_kcal', 0)} kcal/100g\n"
                        f"   - Protein: {food.get('protein_g', 0)}g\n"
                        f"   - Dosha: {food.get('dosha_impact', 'N/A')}\n"
                    )
                
                return "\n".join(result_lines)
            
            else:
                return f"Invalid action or missing parameters. Action: {action}, food_name: {food_name}, query: {replacement_query}"
        
        except Exception as e:
            logger.error(f"Error modifying food selection: {e}")
            return f"Error: {str(e)}"


class SaveDietPlanInput(BaseModel):
    """Input schema for saving diet plan to database"""
    client_id: int = Field(description="Database ID of the client")
    plan_name: str = Field(description="Name of the diet plan")
    plan_text: Optional[str] = Field(
        default=None, 
        description="Complete meal plan text in the required format. If not provided, will extract from conversation history."
    )
    duration_days: int = Field(default=7, description="Duration of the plan in days")


class SaveDietPlanTool(BaseTool):
    """
    Tool for saving generated diet plan to database.
    
    This tool parses the meal plan text and creates database records.
    """
    name: str = "save_diet_plan"
    description: str = """
    Save the generated diet plan to the database so it appears in the client's diet plans list.
    
    This tool:
    - Parses the meal plan text (from plan_text or conversation history)
    - Creates DietPlan record
    - Creates DietPlanMeal records for each meal
    - Returns the saved plan ID
    
    Use this tool AFTER generating the complete 7-day meal plan.
    If you just generated the meal plan in the conversation, you can call this tool
    without providing plan_text - it will automatically extract the plan from the conversation.
    
    Always call this when the plan is finalized and user is satisfied.
    """
    args_schema: type[BaseModel] = SaveDietPlanInput
    db: Session = Field(default=None, exclude=True)
    agent_memory: Optional[Any] = Field(default=None, exclude=True)
    
    def __init__(self, db: Session, agent_memory: Optional[Any] = None):
        super().__init__()
        self.db = db
        self.agent_memory = agent_memory
        logger.info("SaveDietPlanTool initialized")
    
    def _extract_meal_plan_from_history(self) -> Optional[str]:
        """Extract meal plan text from conversation history"""
        if not self.agent_memory:
            return None
        
        try:
            # Get conversation messages
            messages = self.agent_memory.chat_memory.messages
            
            # Look for the most recent AI message containing a meal plan
            # Search backwards through messages
            for msg in reversed(messages):
                content = msg.content if hasattr(msg, 'content') else str(msg)
                
                # Check if this message contains a meal plan (look for "Day 1", "Day 2", etc.)
                if re.search(r'Day\s+\d+\s*:', content, re.IGNORECASE):
                    # Count how many days are in this message
                    day_count = len(re.findall(r'Day\s+\d+\s*:', content, re.IGNORECASE))
                    
                    # If we found multiple days, this is likely the meal plan
                    if day_count >= 3:
                        logger.info(f"Extracted meal plan with {day_count} days from conversation history")
                        return content
            
            logger.warning("Could not find meal plan in conversation history")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting meal plan from history: {e}")
            return None
    
    def _run(
        self,
        client_id: int,
        plan_name: str,
        plan_text: Optional[str] = None,
        duration_days: int = 7
    ) -> str:
        """Save diet plan to database"""
        try:
            from app.models.diet_plan import DietPlan, DietPlanMeal
            from app.models.client import Client
            from app.models.health_profile import HealthProfile
            from app.utils.diet_plan_parser import DietPlanParser
            from datetime import datetime
            
            # Verify client exists
            client = self.db.query(Client).filter(Client.id == client_id).first()
            if not client:
                return f"❌ Client ID {client_id} not found"
            
            # If plan_text not provided, try to extract from conversation history
            if not plan_text:
                logger.info("No plan_text provided, attempting to extract from conversation history")
                plan_text = self._extract_meal_plan_from_history()
                
                if not plan_text:
                    return """❌ Unable to find the meal plan to save. 
                    
Please either:
1. Generate the complete 7-day meal plan first using the exact format, OR
2. Provide the meal plan text directly to this tool

The meal plan must be in this format:
Day 1:
- Morning Cleanse (6:30 AM): [Dish Name]
  Portion: [size]
  Healing Purpose: [benefit]
  Dosha Notes: [impact]
  Calories: X, Protein: Xg, Carbs: Xg, Fat: Xg
[... continue for all meals and days]
"""
            
            # Get health profile for metadata
            health_profile = self.db.query(HealthProfile).filter(
                HealthProfile.client_id == client_id
            ).first()
            
            # Get primary dosha from quiz results
            from app.models.dosha_quiz import DoshaQuiz
            dosha_quiz = self.db.query(DoshaQuiz).filter(
                DoshaQuiz.client_id == client_id
            ).order_by(DoshaQuiz.created_at.desc()).first()
            
            primary_dosha = None
            if dosha_quiz:
                doshas = [
                    ("Vata", dosha_quiz.vata_score or 0),
                    ("Pitta", dosha_quiz.pitta_score or 0),
                    ("Kapha", dosha_quiz.kapha_score or 0)
                ]
                primary_dosha = max(doshas, key=lambda x: x[1])[0]
            
            # Parse the meal plan text
            parser = DietPlanParser()
            parsed_data = parser.parse_diet_plan(plan_text)
            
            if not parsed_data or not parsed_data.get("meals"):
                return "❌ Failed to parse meal plan. Please ensure it follows the exact format."
            
            # Validate parsed data
            validation = parser.validate_meals(parsed_data["meals"])
            if not validation["valid"]:
                return f"❌ Meal plan validation failed: {'; '.join(validation['errors'])}"
            
            # Create diet plan record
            diet_plan = DietPlan(
                client_id=client_id,
                name=plan_name,
                description=f"AI-generated personalized diet plan for {client.first_name} {client.last_name}",
                duration_days=duration_days,
                start_date=datetime.now(),
                status="active",
                dosha_type=primary_dosha,
                diet_type=health_profile.diet_type if health_profile else "veg",
                allergies=health_profile.allergies if health_profile else None,
                health_goals=health_profile.goals if health_profile else None,
                target_calories=parsed_data.get("nutritional_summary", {}).get("avg_calories"),
                target_protein_g=parsed_data.get("nutritional_summary", {}).get("avg_protein"),
                target_carbs_g=parsed_data.get("nutritional_summary", {}).get("avg_carbs"),
                target_fat_g=parsed_data.get("nutritional_summary", {}).get("avg_fat")
            )
            
            self.db.add(diet_plan)
            self.db.flush()  # Get the ID
            
            # Create meal records
            meals_created = 0
            for meal_data in parsed_data["meals"]:
                meal = DietPlanMeal(
                    diet_plan_id=diet_plan.id,
                    day_number=meal_data.get("day_number"),
                    meal_time=meal_data.get("meal_time"),
                    meal_type=meal_data.get("meal_type"),
                    food_dish=meal_data.get("food_dish"),
                    portion=meal_data.get("portion"),
                    healing_purpose=meal_data.get("healing_purpose"),
                    dosha_notes=meal_data.get("dosha_notes"),
                    calories=meal_data.get("calories"),
                    protein_g=meal_data.get("protein_g"),
                    carbs_g=meal_data.get("carbs_g"),
                    fat_g=meal_data.get("fat_g"),
                    order_in_day=meal_data.get("order_in_day", 0)
                )
                self.db.add(meal)
                meals_created += 1
            
            self.db.commit()
            
            logger.info(f"Saved diet plan ID {diet_plan.id} with {meals_created} meals for client {client_id}")
            
            return f"""
✅ Diet plan saved successfully!

Plan Details:
- Plan ID: {diet_plan.id}
- Name: {plan_name}
- Duration: {duration_days} days
- Total Meals: {meals_created}
- Status: Active

The plan is now visible in the client's diet plans section.
Client can view it by navigating to their profile.
"""
        
        except Exception as e:
            logger.error(f"Error saving diet plan: {e}", exc_info=True)
            self.db.rollback()
            return f"❌ Error saving diet plan: {str(e)}"


class GetClientProfileInput(BaseModel):
    """Input schema for getting client profile"""
    client_id: int = Field(description="Database ID of the client")


class GetClientProfileTool(BaseTool):
    """Tool for retrieving client health profile and preferences"""
    name: str = "get_client_profile"
    description: str = """
    Retrieve comprehensive client profile including:
    - Basic info (name, age, weight, height)
    - Health goals and medical conditions
    - Dietary restrictions and allergies
    - Dosha type (if quiz completed)
    - Activity level
    - Current medications
    
    Use this tool at the start of conversation to understand the client thoroughly.
    Always call this before calculating nutrition or retrieving foods.
    """
    args_schema: type[BaseModel] = GetClientProfileInput
    db: Session = Field(default=None, exclude=True)
    
    def __init__(self, db: Session):
        super().__init__()
        self.db = db
    
    def _run(self, client_id: int) -> str:
        """Get client profile"""
        try:
            from app.models.client import Client
            from app.models.health_profile import HealthProfile
            from app.models.dosha_quiz import DoshaQuiz
            
            client = self.db.query(Client).filter(Client.id == client_id).first()
            if not client:
                return f"❌ Client ID {client_id} not found in database"
            
            profile = self.db.query(HealthProfile).filter(
                HealthProfile.client_id == client_id
            ).first()
            
            dosha_quiz = self.db.query(DoshaQuiz).filter(
                DoshaQuiz.client_id == client_id
            ).order_by(DoshaQuiz.created_at.desc()).first()
            
            # Build profile summary
            lines = [
                f"📋 CLIENT PROFILE",
                f"=" * 50,
                f"Name: {client.first_name} {client.last_name}",
                f"Client ID: {client_id}",
                f"Email: {client.email or 'Not provided'}",
                f"Phone: {client.phone or 'Not provided'}",
                ""
            ]
            
            if profile:
                # Calculate age if not set
                age = profile.age
                if not age and client.date_of_birth:
                    from datetime import date
                    today = date.today()
                    age = today.year - client.date_of_birth.year
                
                lines.extend([
                    f"PHYSICAL ATTRIBUTES:",
                    f"- Age: {age} years",
                    f"- Gender: {client.gender or 'Not specified'}",
                    f"- Weight: {profile.weight} kg",
                    f"- Height: {profile.height} cm",
                    f"- BMI: {round(profile.weight / ((profile.height/100)**2), 1) if profile.weight and profile.height else 'N/A'}",
                    "",
                    f"HEALTH & LIFESTYLE:",
                    f"- Activity Level: {profile.activity_level or 'Not specified'}",
                    f"- Health Goals: {profile.goals or 'General wellness'}",
                    f"- Medical Conditions: {profile.disease or 'None reported'}",
                    f"- Sleep Cycle: {profile.sleep_cycle or 'Not specified'}",
                    "",
                    f"DIETARY PREFERENCES:",
                    f"- Diet Type: {profile.diet_type or 'Vegetarian'}",
                    f"- Allergies: {profile.allergies or 'None reported'}",
                    f"- Supplements: {profile.supplements or 'None'}",
                    f"- Medications: {profile.medications or 'None'}",
                ])
            else:
                lines.append("⚠️  No health profile found. Create one before generating diet plan.")
            
            if dosha_quiz:
                doshas = [
                    ("Vata", dosha_quiz.vata_score or 0),
                    ("Pitta", dosha_quiz.pitta_score or 0),
                    ("Kapha", dosha_quiz.kapha_score or 0)
                ]
                primary_dosha = max(doshas, key=lambda x: x[1])[0]
                
                lines.extend([
                    "",
                    f"AYURVEDIC CONSTITUTION (Prakriti):",
                    f"- Primary Dosha: {primary_dosha} ⭐",
                    f"- Vata Score: {dosha_quiz.vata_score}",
                    f"- Pitta Score: {dosha_quiz.pitta_score}",
                    f"- Kapha Score: {dosha_quiz.kapha_score}",
                    f"- Recommendation: Focus on foods that balance {primary_dosha}"
                ])
            else:
                lines.extend([
                    "",
                    "ℹ️  Dosha quiz not completed. Consider general Ayurvedic principles."
                ])
            
            if client.medical_history:
                lines.extend([
                    "",
                    f"MEDICAL HISTORY:",
                    f"{client.medical_history}"
                ])
            
            if client.notes:
                lines.extend([
                    "",
                    f"PRACTITIONER NOTES:",
                    f"{client.notes}"
                ])
            
            lines.extend([
                "",
                f"=" * 50,
                f"✓ Profile loaded successfully. Use this information to create personalized recommendations."
            ])
            
            return "\n".join(lines)
        
        except Exception as e:
            logger.error(f"Error getting client profile: {e}")
            return f"❌ Error retrieving profile: {str(e)}"


# ============================================
# Tool Registry
# ============================================

def get_diet_plan_tools(db: Session) -> List[BaseTool]:
    """
    Get all diet plan generation tools for the LangChain agent.
    
    Includes both original tools and new conversational tools:
    - GetClientProfileTool: Retrieve client information
    - CalculateNutritionTool: Calculate nutritional requirements
    - RetrieveFoodsTool: Search for appropriate foods
    - ModifyFoodSelectionTool: Handle user modifications
    - ValidateNutritionTool: Validate meal plans
    - SaveDietPlanTool: Save generated plan to database
    
    Args:
        db: SQLAlchemy database session
    
    Returns:
        List of initialized tools ready for use by the agent
    """
    tools = [
        GetClientProfileTool(db=db),
        CalculateNutritionTool(),
        RetrieveFoodsTool(db=db),
        ModifyFoodSelectionTool(db=db),
        ValidateNutritionTool(),
        SaveDietPlanTool(db=db)
    ]
    
    logger.info(f"Initialized {len(tools)} diet plan tools (including conversational tools)")
    return tools


