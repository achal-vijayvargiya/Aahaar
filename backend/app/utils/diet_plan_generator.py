"""
AI-Powered Diet Plan Generator

Generates personalized 7-day diet plans based on:
- Health profile (goals, dosha, diet type, allergies)
- Nutritional requirements
- Food database with Ayurvedic properties
"""
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.health_profile import HealthProfile
from app.models.food_item import FoodItem
from app.models.dosha_quiz import DoshaQuiz
from app.knowledge_base.food_retriever import FoodRetriever
from app.utils.logger import logger


class DietPlanGenerator:
    """
    Intelligent diet plan generator that creates personalized meal plans.
    """
    
    # Standard meal schedule
    MEAL_SCHEDULE = [
        {"time": "6:30 AM", "type": "Morning Cleanse", "order": 1},
        {"time": "8:30 AM", "type": "Breakfast", "order": 2},
        {"time": "11:00 AM", "type": "Mid Snack", "order": 3},
        {"time": "1:30 PM", "type": "Lunch", "order": 4},
        {"time": "4:30 PM", "type": "Evening Snack", "order": 5},
        {"time": "7:00 PM", "type": "Dinner", "order": 6},
        {"time": "9:00 PM", "type": "Sleep Tonic", "order": 7}
    ]
    
    # Calorie distribution across meals (as percentage of daily total)
    CALORIE_DISTRIBUTION = {
        "Morning Cleanse": 0.03,  # 3% - light cleansing drink
        "Breakfast": 0.25,        # 25% - hearty breakfast
        "Mid Snack": 0.10,        # 10% - light snack
        "Lunch": 0.35,            # 35% - main meal
        "Evening Snack": 0.10,    # 10% - light snack
        "Dinner": 0.15,           # 15% - light dinner
        "Sleep Tonic": 0.02       # 2% - bedtime drink
    }
    
    def __init__(self, db: Session):
        """Initialize diet plan generator."""
        self.db = db
        self.food_retriever = FoodRetriever()
        logger.info("DietPlanGenerator initialized")
    
    def generate_plan(
        self,
        client_id: int,
        health_profile: HealthProfile,
        duration_days: int = 7,
        custom_goals: Optional[str] = None,
        custom_diet_type: Optional[str] = None,
        custom_allergies: Optional[str] = None,
        prefer_satvik: bool = False,
        include_regional_foods: Optional[str] = None,
        meal_variety: str = "moderate"
    ) -> Dict:
        """
        Generate a complete diet plan.
        
        Returns:
            Dictionary with plan metadata and meals
        """
        logger.info(f"Generating diet plan for client_id={client_id}, duration={duration_days} days")
        
        # Calculate nutritional targets
        targets = self._calculate_nutritional_targets(health_profile)
        
        # Determine dosha to balance
        dosha_type = self._get_primary_dosha(client_id)
        
        # Get diet preferences
        diet_type = custom_diet_type or health_profile.diet_type or "veg"
        allergies = custom_allergies or health_profile.allergies or ""
        goals = custom_goals or health_profile.goals or "general wellness"
        
        # Fetch appropriate foods by category
        food_categories = self._get_food_by_categories(
            goals=goals,
            dosha_type=dosha_type,
            diet_type=diet_type,
            allergies=allergies,
            prefer_satvik=prefer_satvik,
            region=include_regional_foods
        )
        
        # Generate meals for each day
        meals = []
        for day in range(1, duration_days + 1):
            day_meals = self._generate_day_meals(
                day_number=day,
                food_categories=food_categories,
                daily_targets=targets,
                dosha_type=dosha_type,
                diet_type=diet_type,
                allergies=allergies,
                goals=goals,
                variety_level=meal_variety
            )
            meals.extend(day_meals)
        
        # Create plan metadata
        plan_data = {
            "client_id": client_id,
            "name": self._generate_plan_name(goals, duration_days),
            "description": self._generate_plan_description(goals, dosha_type, targets),
            "duration_days": duration_days,
            "health_goals": goals,
            "dosha_type": dosha_type,
            "diet_type": diet_type,
            "allergies": allergies,
            "target_calories": targets["calories"],
            "target_protein_g": targets["protein"],
            "target_carbs_g": targets["carbs"],
            "target_fat_g": targets["fat"],
            "meals": meals
        }
        
        logger.info(f"Generated diet plan with {len(meals)} meals")
        return plan_data
    
    def _calculate_nutritional_targets(self, health_profile: HealthProfile) -> Dict[str, float]:
        """
        Calculate daily nutritional targets based on health profile.
        Uses Mifflin-St Jeor equation and activity level.
        """
        # Default values if not enough data
        if not health_profile.weight or not health_profile.height or not health_profile.age:
            return {
                "calories": 2000,
                "protein": 80,
                "carbs": 250,
                "fat": 65
            }
        
        # Calculate BMR (Basal Metabolic Rate)
        weight_kg = health_profile.weight
        height_cm = health_profile.height
        age = health_profile.age
        
        # Assuming average gender distribution, use a moderate formula
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
        
        # Activity multipliers
        activity_multipliers = {
            "sedentary": 1.2,
            "lightly_active": 1.375,
            "moderately_active": 1.55,
            "very_active": 1.725,
            "extremely_active": 1.9
        }
        
        activity_level = health_profile.activity_level or "moderately_active"
        multiplier = activity_multipliers.get(activity_level, 1.55)
        
        # Calculate total daily energy expenditure (TDEE)
        tdee = bmr * multiplier
        
        # Adjust based on goals
        goals = (health_profile.goals or "").lower()
        if "weight loss" in goals or "lose weight" in goals:
            calories = tdee - 500  # Deficit for weight loss
        elif "weight gain" in goals or "muscle" in goals:
            calories = tdee + 300  # Surplus for muscle gain
        else:
            calories = tdee  # Maintenance
        
        # Calculate macros (40% carbs, 30% protein, 30% fat for balanced diet)
        protein = (calories * 0.30) / 4  # 4 calories per gram
        carbs = (calories * 0.40) / 4
        fat = (calories * 0.30) / 9  # 9 calories per gram
        
        return {
            "calories": round(calories, 0),
            "protein": round(protein, 1),
            "carbs": round(carbs, 1),
            "fat": round(fat, 1)
        }
    
    def _get_primary_dosha(self, client_id: int) -> Optional[str]:
        """Get primary dosha from quiz results."""
        quiz_result = self.db.query(DoshaQuiz).filter(
            DoshaQuiz.client_id == client_id
        ).order_by(DoshaQuiz.created_at.desc()).first()
        
        if not quiz_result:
            return None
        
        # Return the dosha with highest score
        doshas = {
            "Vata": quiz_result.vata_score or 0,
            "Pitta": quiz_result.pitta_score or 0,
            "Kapha": quiz_result.kapha_score or 0
        }
        primary = max(doshas, key=doshas.get)
        return primary
    
    def _get_food_by_categories(
        self,
        goals: str,
        dosha_type: Optional[str],
        diet_type: str,
        allergies: str,
        prefer_satvik: bool,
        region: Optional[str]
    ) -> Dict[str, List[Dict]]:
        """
        Fetch foods organized by categories, filtered by requirements.
        """
        # Build search query based on goals
        search_queries = {
            "Breakfast": f"nutritious breakfast foods for {goals}",
            "Lunch": f"wholesome lunch foods for {goals}",
            "Dinner": f"light dinner foods for {goals}",
            "Snack": f"healthy snacks for {goals}",
            "Beverage": f"healing drinks and tonics",
        }
        
        # Get all available categories
        all_categories = self.food_retriever.get_all_categories(self.db)
        
        foods_by_category = {}
        
        # Map meal types to food categories
        category_mapping = {
            "Morning Cleanse": ["Beverage", "Detox Tea", "Herbal Infusion"],
            "Breakfast": ["Grains", "Dairy", "Fruits", "Nuts & Seeds"],
            "Mid Snack": ["Fruits", "Nuts & Seeds", "Snacks"],
            "Lunch": ["Grains", "Pulses & Legumes", "Vegetables", "Dairy", "Proteins"],
            "Evening Snack": ["Fruits", "Nuts & Seeds", "Snacks", "Beverage"],
            "Dinner": ["Grains", "Vegetables", "Pulses & Legumes", "Soup"],
            "Sleep Tonic": ["Beverage", "Herbal Infusion", "Dairy"]
        }
        
        # Fetch foods for each category
        for meal_type, categories in category_mapping.items():
            meal_foods = []
            for category in categories:
                if category in all_categories or True:  # Try all categories
                    query = search_queries.get(meal_type.split()[0], f"healthy foods for {goals}")
                    
                    # Apply dosha filter
                    dosha_preference = None
                    if dosha_type:
                        # To balance dosha, we want foods that reduce it
                        dosha_preference = f"{dosha_type} ↓"
                    
                    try:
                        foods = self.food_retriever.semantic_search(
                            db=self.db,
                            query=query,
                            category=category if category in all_categories else None,
                            dosha_preference=dosha_preference,
                            satvik_only=prefer_satvik,
                            top_k=10
                        )
                        meal_foods.extend(foods)
                    except Exception as e:
                        logger.warning(f"Error fetching foods for category {category}: {e}")
                        continue
            
            if meal_foods:
                foods_by_category[meal_type] = meal_foods
        
        logger.info(f"Fetched foods for {len(foods_by_category)} meal types")
        return foods_by_category
    
    def _generate_day_meals(
        self,
        day_number: int,
        food_categories: Dict[str, List[Dict]],
        daily_targets: Dict[str, float],
        dosha_type: Optional[str],
        diet_type: str,
        allergies: str,
        goals: str,
        variety_level: str
    ) -> List[Dict]:
        """Generate meals for a single day."""
        day_meals = []
        
        for meal_info in self.MEAL_SCHEDULE:
            meal_type = meal_info["type"]
            meal_time = meal_info["time"]
            order = meal_info["order"]
            
            # Get target calories for this meal
            meal_calories = daily_targets["calories"] * self.CALORIE_DISTRIBUTION[meal_type]
            
            # Select appropriate food
            meal_data = self._select_meal_food(
                meal_type=meal_type,
                available_foods=food_categories.get(meal_type, []),
                target_calories=meal_calories,
                dosha_type=dosha_type,
                diet_type=diet_type,
                day_number=day_number,
                variety_level=variety_level
            )
            
            # Create meal entry
            meal = {
                "day_number": day_number,
                "meal_time": meal_time,
                "meal_type": meal_type,
                "order_in_day": order,
                "food_dish": meal_data["dish_name"],
                "food_item_ids": meal_data.get("food_ids", ""),
                "healing_purpose": meal_data["healing_purpose"],
                "portion": meal_data["portion"],
                "dosha_notes": meal_data["dosha_notes"],
                "notes": meal_data.get("notes", ""),
                "calories": meal_data.get("calories", meal_calories),
                "protein_g": meal_data.get("protein", 0),
                "carbs_g": meal_data.get("carbs", 0),
                "fat_g": meal_data.get("fat", 0)
            }
            
            day_meals.append(meal)
        
        return day_meals
    
    def _select_meal_food(
        self,
        meal_type: str,
        available_foods: List[Dict],
        target_calories: float,
        dosha_type: Optional[str],
        diet_type: str,
        day_number: int,
        variety_level: str
    ) -> Dict:
        """
        Select appropriate food for a meal based on requirements.
        """
        # Special handling for cleansers and tonics
        if meal_type == "Morning Cleanse":
            return self._create_morning_cleanse(dosha_type)
        
        if meal_type == "Sleep Tonic":
            return self._create_sleep_tonic(dosha_type)
        
        # For other meals, select from available foods
        if not available_foods:
            return self._create_default_meal(meal_type, target_calories, dosha_type)
        
        # Select food based on variety level and day
        variety_indices = {
            "low": day_number % 3,      # Repeat every 3 days
            "moderate": day_number % 5,  # Repeat every 5 days
            "high": day_number            # Different each day
        }
        
        index = variety_indices.get(variety_level, day_number % 5) % len(available_foods)
        selected_food = available_foods[index]
        
        # Calculate portion based on target calories
        food_calories = selected_food.get("energy_kcal", 100)
        if food_calories > 0:
            portion_multiplier = target_calories / food_calories
            portion_g = portion_multiplier * 100  # Base is per 100g
        else:
            portion_g = 100
        
        # Create meal description
        dish_name = selected_food["food_name"]
        healing_purpose = self._generate_healing_purpose(selected_food, meal_type)
        portion = self._format_portion(portion_g, selected_food.get("serving_size", ""))
        dosha_notes = selected_food.get("dosha_impact", "")
        
        return {
            "dish_name": dish_name,
            "food_ids": str(selected_food.get("id", "")),
            "healing_purpose": healing_purpose,
            "portion": portion,
            "dosha_notes": dosha_notes,
            "calories": target_calories,
            "protein": selected_food.get("protein_g", 0) * portion_multiplier,
            "carbs": selected_food.get("carbs_g", 0) * portion_multiplier,
            "fat": selected_food.get("fat_g", 0) * portion_multiplier,
            "notes": f"Rich in {selected_food.get('key_micronutrients', 'nutrients')}"
        }
    
    def _create_morning_cleanse(self, dosha_type: Optional[str]) -> Dict:
        """Create morning cleanse drink based on dosha."""
        cleanses = {
            "Vata": {
                "name": "Warm Lemon Ginger Water",
                "purpose": "Ignites digestive fire, balances Vata",
                "portion": "1 glass (250ml)",
                "notes": "Warm water with lemon juice and grated ginger"
            },
            "Pitta": {
                "name": "Cooling Cucumber Mint Water",
                "purpose": "Cools and hydrates, balances Pitta",
                "portion": "1 glass (250ml)",
                "notes": "Room temperature water with cucumber and mint"
            },
            "Kapha": {
                "name": "Warm Honey Water with Turmeric",
                "purpose": "Stimulates metabolism, balances Kapha",
                "portion": "1 glass (250ml)",
                "notes": "Warm water with honey and turmeric"
            }
        }
        
        cleanse = cleanses.get(dosha_type, cleanses["Vata"])
        return {
            "dish_name": cleanse["name"],
            "food_ids": "",
            "healing_purpose": cleanse["purpose"],
            "portion": cleanse["portion"],
            "dosha_notes": f"Specifically formulated for {dosha_type} balance",
            "calories": 15,
            "protein": 0,
            "carbs": 3,
            "fat": 0,
            "notes": cleanse["notes"]
        }
    
    def _create_sleep_tonic(self, dosha_type: Optional[str]) -> Dict:
        """Create bedtime drink based on dosha."""
        tonics = {
            "Vata": {
                "name": "Warm Ashwagandha Milk",
                "purpose": "Calms nervous system, promotes restful sleep",
                "portion": "1 cup (200ml)",
                "notes": "Warm milk with ashwagandha powder and nutmeg"
            },
            "Pitta": {
                "name": "Cool Rose Milk",
                "purpose": "Cools body temperature, promotes calm sleep",
                "portion": "1 cup (200ml)",
                "notes": "Cool milk with rose water and cardamom"
            },
            "Kapha": {
                "name": "Turmeric Ginger Tea",
                "purpose": "Aids digestion, promotes lightness",
                "portion": "1 cup (200ml)",
                "notes": "Herbal tea with turmeric, ginger, and black pepper"
            }
        }
        
        tonic = tonics.get(dosha_type, tonics["Vata"])
        return {
            "dish_name": tonic["name"],
            "food_ids": "",
            "healing_purpose": tonic["purpose"],
            "portion": tonic["portion"],
            "dosha_notes": f"Calming evening tonic for {dosha_type}",
            "calories": 80,
            "protein": 3,
            "carbs": 10,
            "fat": 3,
            "notes": tonic["notes"]
        }
    
    def _create_default_meal(
        self,
        meal_type: str,
        target_calories: float,
        dosha_type: Optional[str]
    ) -> Dict:
        """Create a default meal when no foods are available."""
        default_meals = {
            "Breakfast": {
                "name": "Oatmeal with Fruits and Nuts",
                "purpose": "Provides sustained energy and fiber",
                "portion": "1 bowl (200g)"
            },
            "Mid Snack": {
                "name": "Fresh Seasonal Fruit",
                "purpose": "Provides vitamins and natural sugars",
                "portion": "1 medium fruit"
            },
            "Lunch": {
                "name": "Vegetable Khichdi with Dal",
                "purpose": "Complete balanced meal, easy to digest",
                "portion": "1 plate (300g)"
            },
            "Evening Snack": {
                "name": "Herbal Tea with Nuts",
                "purpose": "Light refreshment with healthy fats",
                "portion": "1 cup tea + handful nuts"
            },
            "Dinner": {
                "name": "Vegetable Soup with Quinoa",
                "purpose": "Light, nutritious, easy to digest",
                "portion": "1 bowl (250ml)"
            }
        }
        
        meal = default_meals.get(meal_type, default_meals["Lunch"])
        
        return {
            "dish_name": meal["name"],
            "food_ids": "",
            "healing_purpose": meal["purpose"],
            "portion": meal["portion"],
            "dosha_notes": f"Suitable for {dosha_type} balance" if dosha_type else "Balanced meal",
            "calories": target_calories,
            "protein": target_calories * 0.15 / 4,
            "carbs": target_calories * 0.55 / 4,
            "fat": target_calories * 0.30 / 9,
            "notes": "Adjust spices according to your dosha"
        }
    
    def _generate_healing_purpose(self, food: Dict, meal_type: str) -> str:
        """Generate healing purpose based on food properties."""
        purposes = []
        
        # Based on nutritional content
        protein = food.get("protein_g", 0)
        if protein > 10:
            purposes.append("supports muscle health and repair")
        
        # Based on Ayurvedic properties
        dosha = food.get("dosha_impact", "")
        if "↓" in dosha:
            balanced_dosha = dosha.split("↓")[0].strip()
            purposes.append(f"balances {balanced_dosha}")
        
        # Based on gut health
        gut_value = food.get("gut_biotic_value", "")
        if "Prebiotic" in gut_value:
            purposes.append("supports gut health")
        
        # Based on satvik value
        satvik = food.get("satvik_rajasik_tamasik", "")
        if satvik == "Satvik":
            purposes.append("promotes mental clarity and calmness")
        
        if purposes:
            return ", ".join(purposes).capitalize()
        
        return f"Nutritious option for {meal_type.lower()}"
    
    def _format_portion(self, grams: float, serving_size: str) -> str:
        """Format portion size in a user-friendly way."""
        if serving_size:
            return serving_size
        
        if grams < 50:
            return f"{int(grams)}g (small portion)"
        elif grams < 150:
            return f"{int(grams)}g (1 cup)"
        elif grams < 250:
            return f"{int(grams)}g (1 large serving)"
        else:
            return f"{int(grams)}g (1-2 servings)"
    
    def _generate_plan_name(self, goals: str, duration: int) -> str:
        """Generate a descriptive name for the plan."""
        goal_keywords = {
            "weight loss": "Weight Loss",
            "muscle": "Muscle Building",
            "detox": "Detox & Cleanse",
            "energy": "Energy Boost",
            "digestion": "Digestive Health",
            "immunity": "Immunity Boost"
        }
        
        goals_lower = goals.lower()
        plan_type = "Wellness"
        
        for keyword, plan_name in goal_keywords.items():
            if keyword in goals_lower:
                plan_type = plan_name
                break
        
        return f"{plan_type} Plan - {duration} Days"
    
    def _generate_plan_description(
        self,
        goals: str,
        dosha_type: Optional[str],
        targets: Dict[str, float]
    ) -> str:
        """Generate plan description."""
        desc_parts = [
            f"Personalized {duration_days if 'duration_days' in locals() else 7}-day meal plan designed for {goals}."
        ]
        
        if dosha_type:
            desc_parts.append(f"Focuses on balancing {dosha_type} dosha through appropriate food choices.")
        
        desc_parts.append(
            f"Daily targets: {int(targets['calories'])} kcal, "
            f"{int(targets['protein'])}g protein, "
            f"{int(targets['carbs'])}g carbs, "
            f"{int(targets['fat'])}g fat."
        )
        
        return " ".join(desc_parts)

