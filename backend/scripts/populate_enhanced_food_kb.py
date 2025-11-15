"""
Populate Enhanced Food Knowledge Base

This script populates the relational tables from existing food_items data:
- food_dosha_effects
- food_disease_relations
- food_allergens
- food_goal_scores
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.food_item import FoodItem
from app.models.food_dosha_effect import FoodDoshaEffect
from app.models.food_disease_relation import FoodDiseaseRelation
from app.models.food_allergen import FoodAllergen
from app.models.food_goal_score import FoodGoalScore
from app.utils.logger import logger


# Allergen keywords mapping
ALLERGEN_KEYWORDS = {
    "dairy": ["milk", "paneer", "cheese", "curd", "yogurt", "ghee", "butter", "cream"],
    "gluten": ["wheat", "atta", "maida", "bread", "roti", "chapati", "pasta"],
    "nuts": ["peanut", "almond", "cashew", "walnut", "pistachio", "hazelnut"],
    "soy": ["soy", "tofu", "soya"],
    "lactose": ["milk", "dairy", "curd", "yogurt"],
    "eggs": ["egg", "omelette"],
    "fish": ["fish", "salmon", "tuna", "sardine"],
    "shellfish": ["prawn", "shrimp", "crab", "lobster"],
}

# Disease-food rules
DISEASE_AVOID_KEYWORDS = {
    "diabetes": ["sugar", "jaggery", "honey", "sweet", "candy", "chocolate"],
    "hypertension": ["salt", "pickle", "papad", "salted"],
    "heart_disease": ["fried", "deep fried", "butter", "ghee"],
    "kidney_disease": [],  # Will use high protein check
}

DISEASE_BENEFICIAL_KEYWORDS = {
    "diabetes": ["bitter gourd", "methi", "fenugreek", "cinnamon", "jamun"],
    "hypertension": ["banana", "beetroot", "garlic", "spinach"],
    "heart_disease": ["oats", "flaxseed", "walnuts", "fish"],
}


def populate_dosha_effects(db: Session):
    """Populate food_dosha_effects from existing dosha_impact text"""
    logger.info("Populating food dosha effects...")
    
    foods = db.query(FoodItem).filter(FoodItem.dosha_impact.isnot(None)).all()
    count = 0
    
    for food in foods:
        # Parse existing dosha_impact text
        effects = FoodDoshaEffect.parse_dosha_impact_text(food.dosha_impact)
        
        for effect_data in effects:
            # Check if already exists
            existing = db.query(FoodDoshaEffect).filter(
                FoodDoshaEffect.food_id == food.id,
                FoodDoshaEffect.dosha_type == effect_data['dosha_type']
            ).first()
            
            if not existing:
                dosha_effect = FoodDoshaEffect(
                    food_id=food.id,
                    dosha_type=effect_data['dosha_type'],
                    effect=effect_data['effect'],
                    intensity=effect_data['intensity']
                )
                db.add(dosha_effect)
                count += 1
    
    db.commit()
    logger.info(f"Created {count} dosha effect records")


def populate_allergens(db: Session):
    """Populate food_allergens based on food names and categories"""
    logger.info("Populating food allergens...")
    
    foods = db.query(FoodItem).all()
    count = 0
    
    # Track what we've already added in this session to avoid duplicates within batch
    added_in_session = set()
    
    for food in foods:
        food_name_lower = food.food_name.lower()
        category_lower = (food.category or "").lower()
        
        # Track allergens for this food to avoid duplicates
        food_allergens = set()
        
        # Check for allergens by keyword
        for allergen, keywords in ALLERGEN_KEYWORDS.items():
            if any(keyword in food_name_lower for keyword in keywords):
                food_allergens.add(allergen)
        
        # Category-based allergens
        if "dairy" in category_lower and food_name_lower not in ["ghee"]:
            food_allergens.add("dairy")
        
        # Add each unique allergen for this food
        for allergen in food_allergens:
            key = (food.id, allergen)
            
            # Skip if already added in this session
            if key in added_in_session:
                continue
            
            # Check if already exists in DB
            existing = db.query(FoodAllergen).filter(
                FoodAllergen.food_id == food.id,
                FoodAllergen.allergen == allergen
            ).first()
            
            if not existing:
                allergen_record = FoodAllergen(
                    food_id=food.id,
                    allergen=allergen,
                    severity="major"
                )
                db.add(allergen_record)
                added_in_session.add(key)
                count += 1
    
    # Commit all at once
    try:
        db.commit()
        logger.info(f"Created {count} allergen records")
    except Exception as e:
        logger.error(f"Error committing allergens: {e}")
        db.rollback()
        logger.info(f"Created 0 allergen records due to error")


def populate_disease_relations(db: Session):
    """Populate food_disease_relations based on nutritional properties"""
    logger.info("Populating food-disease relations...")
    
    foods = db.query(FoodItem).all()
    count = 0
    
    for food in foods:
        food_name_lower = food.food_name.lower()
        
        # Check for diabetes
        # Avoid high sugar foods
        for keyword in DISEASE_AVOID_KEYWORDS["diabetes"]:
            if keyword in food_name_lower:
                existing = db.query(FoodDiseaseRelation).filter(
                    FoodDiseaseRelation.food_id == food.id,
                    FoodDiseaseRelation.disease_condition == "diabetes"
                ).first()
                if not existing:
                    db.add(FoodDiseaseRelation(
                        food_id=food.id,
                        disease_condition="diabetes",
                        relationship="avoid",
                        reason="High sugar content",
                        severity=5
                    ))
                    count += 1
                break
        
        # Beneficial for diabetes
        for keyword in DISEASE_BENEFICIAL_KEYWORDS["diabetes"]:
            if keyword in food_name_lower:
                existing = db.query(FoodDiseaseRelation).filter(
                    FoodDiseaseRelation.food_id == food.id,
                    FoodDiseaseRelation.disease_condition == "diabetes"
                ).first()
                if not existing:
                    db.add(FoodDiseaseRelation(
                        food_id=food.id,
                        disease_condition="diabetes",
                        relationship="beneficial",
                        reason="Helps manage blood sugar",
                        severity=4
                    ))
                    count += 1
                break
        
        # Check for hypertension
        for keyword in DISEASE_AVOID_KEYWORDS["hypertension"]:
            if keyword in food_name_lower:
                existing = db.query(FoodDiseaseRelation).filter(
                    FoodDiseaseRelation.food_id == food.id,
                    FoodDiseaseRelation.disease_condition == "hypertension"
                ).first()
                if not existing:
                    db.add(FoodDiseaseRelation(
                        food_id=food.id,
                        disease_condition="hypertension",
                        relationship="avoid",
                        reason="High sodium content",
                        severity=4
                    ))
                    count += 1
                break
        
        # Beneficial for hypertension
        for keyword in DISEASE_BENEFICIAL_KEYWORDS["hypertension"]:
            if keyword in food_name_lower:
                existing = db.query(FoodDiseaseRelation).filter(
                    FoodDiseaseRelation.food_id == food.id,
                    FoodDiseaseRelation.disease_condition == "hypertension"
                ).first()
                if not existing:
                    db.add(FoodDiseaseRelation(
                        food_id=food.id,
                        disease_condition="hypertension",
                        relationship="beneficial",
                        reason="Helps lower blood pressure",
                        severity=3
                    ))
                    count += 1
                break
    
    db.commit()
    logger.info(f"Created {count} disease relation records")


def populate_goal_scores(db: Session):
    """Populate food_goal_scores based on nutritional analysis"""
    logger.info("Populating food goal scores...")
    
    foods = db.query(FoodItem).all()
    count = 0
    
    health_goals = ["weight_loss", "muscle_gain", "diabetes_management", "heart_health", "digestive_health", "energy_boost"]
    
    for food in foods:
        for goal in health_goals:
            # Calculate score based on nutrition
            score = calculate_goal_score(food, goal)
            
            # Only add if score is meaningful (not exactly 50)
            if score != 50:
                existing = db.query(FoodGoalScore).filter(
                    FoodGoalScore.food_id == food.id,
                    FoodGoalScore.health_goal == goal
                ).first()
                
                if not existing:
                    db.add(FoodGoalScore(
                        food_id=food.id,
                        health_goal=goal,
                        score=score,
                        reason=get_score_reason(food, goal, score)
                    ))
                    count += 1
    
    db.commit()
    logger.info(f"Created {count} goal score records")


def calculate_goal_score(food: FoodItem, goal: str) -> int:
    """Calculate how well a food supports a specific goal"""
    
    # Weight Loss - prefer low calorie, high fiber, high protein
    if goal == "weight_loss":
        score = 50
        if food.energy_kcal:
            if food.energy_kcal < 150:
                score += 20
            elif food.energy_kcal > 400:
                score -= 20
        
        if food.protein_g and food.protein_g > 10:
            score += 15
        
        if food.fat_g:
            if food.fat_g < 3:
                score += 15
            elif food.fat_g > 15:
                score -= 15
        
        return max(0, min(100, score))
    
    # Muscle Gain - prefer high protein, moderate carbs
    elif goal == "muscle_gain":
        score = 50
        if food.protein_g:
            if food.protein_g > 20:
                score += 40
            elif food.protein_g > 10:
                score += 25
            elif food.protein_g > 5:
                score += 10
        
        if food.carbs_g and food.carbs_g > 30:
            score += 10
        
        return max(0, min(100, score))
    
    # Diabetes Management - prefer low GI, low sugar, high fiber
    elif goal == "diabetes_management":
        score = 50
        food_name_lower = food.food_name.lower()
        
        # Avoid sugary foods
        if any(word in food_name_lower for word in ["sugar", "jaggery", "honey", "sweet"]):
            score = 20
        
        # Prefer high fiber
        if food.carbs_g:
            if food.carbs_g < 30:
                score += 20
            elif food.carbs_g > 60:
                score -= 20
        
        if food.protein_g and food.protein_g > 10:
            score += 15
        
        return max(0, min(100, score))
    
    # Heart Health - prefer low fat, high fiber
    elif goal == "heart_health":
        score = 50
        if food.fat_g:
            if food.fat_g < 5:
                score += 25
            elif food.fat_g > 15:
                score -= 25
        
        if food.protein_g and food.protein_g > 8:
            score += 15
        
        return max(0, min(100, score))
    
    # Digestive Health - prefer high fiber, easy to digest
    elif goal == "digestive_health":
        score = 50
        food_name_lower = food.food_name.lower()
        
        # Good for digestion
        if any(word in food_name_lower for word in ["dal", "moong", "khichdi", "curd", "buttermilk"]):
            score += 30
        
        # Heavy foods
        if any(word in food_name_lower for word in ["fried", "heavy", "rich"]):
            score -= 20
        
        return max(0, min(100, score))
    
    # Energy Boost - prefer moderate-high calories, good carbs
    elif goal == "energy_boost":
        score = 50
        if food.energy_kcal:
            if 200 < food.energy_kcal < 400:
                score += 25
        
        if food.carbs_g and 30 < food.carbs_g < 70:
            score += 20
        
        return max(0, min(100, score))
    
    return 50


def get_score_reason(food: FoodItem, goal: str, score: int) -> str:
    """Generate reason for the score"""
    if goal == "weight_loss":
        if score > 70:
            return f"Low calorie ({food.energy_kcal} kcal), good for weight management"
        elif score < 40:
            return f"High calorie ({food.energy_kcal} kcal), not ideal for weight loss"
    
    elif goal == "muscle_gain":
        if score > 70:
            return f"High protein ({food.protein_g}g), excellent for muscle building"
        elif score < 40:
            return f"Low protein ({food.protein_g}g), limited benefit"
    
    elif goal == "diabetes_management":
        if score > 70:
            return "Low glycemic impact, helps manage blood sugar"
        elif score < 40:
            return "High sugar/carbs, not recommended for diabetes"
    
    return "Moderate compatibility with this goal"


def main():
    """Main population function"""
    logger.info("=" * 80)
    logger.info("ENHANCED FOOD KB POPULATION SCRIPT")
    logger.info("=" * 80)
    
    db = SessionLocal()
    
    try:
        # Check if tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        required_tables = ['food_dosha_effects', 'food_disease_relations', 'food_allergens', 'food_goal_scores']
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            logger.error(f"Missing tables: {missing_tables}")
            logger.error("Run migration first: alembic upgrade head")
            return
        
        # Get food count
        food_count = db.query(FoodItem).count()
        logger.info(f"Found {food_count} food items in database")
        
        if food_count == 0:
            logger.error("No foods in database. Run load_food_database.py first")
            return
        
        # Populate each table
        logger.info("\n1. Populating Dosha Effects...")
        populate_dosha_effects(db)
        
        logger.info("\n2. Populating Allergens...")
        populate_allergens(db)
        
        logger.info("\n3. Populating Disease Relations...")
        populate_disease_relations(db)
        
        logger.info("\n4. Populating Goal Scores...")
        populate_goal_scores(db)
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("POPULATION COMPLETE!")
        logger.info("=" * 80)
        
        dosha_count = db.query(FoodDoshaEffect).count()
        allergen_count = db.query(FoodAllergen).count()
        disease_count = db.query(FoodDiseaseRelation).count()
        goal_count = db.query(FoodGoalScore).count()
        
        logger.info(f"Dosha Effects: {dosha_count} records")
        logger.info(f"Allergens: {allergen_count} records")
        logger.info(f"Disease Relations: {disease_count} records")
        logger.info(f"Goal Scores: {goal_count} records")
        
        logger.info("\nEnhanced KB is ready for use!")
        logger.info("Test with: python scripts/test_smart_food_retrieval.py")
        
    except Exception as e:
        logger.error(f"Error populating KB: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()

