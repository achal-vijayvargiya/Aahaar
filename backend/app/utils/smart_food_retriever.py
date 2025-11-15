"""
Smart Food Retrieval System

Retrieves top foods per category based on user profile with:
- Dosha balancing
- Disease safety filtering
- Allergen exclusion
- Goal optimization
- Intelligent ranking
"""
from typing import Dict, List, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, not_, func

from app.models.food_item import FoodItem
from app.models.food_dosha_effect import FoodDoshaEffect
from app.models.food_disease_relation import FoodDiseaseRelation
from app.models.food_allergen import FoodAllergen
from app.models.food_goal_score import FoodGoalScore
from app.models.dosha_quiz import DoshaQuiz
from app.knowledge_base.food_retriever import FoodRetriever
from app.utils.logger import logger


# Standard food categories to retrieve (matching actual DB category names)
FOOD_CATEGORIES = [
    "Cereal",              # Grains/Cereals
    "Pulse/Legume",        # Pulses & Legumes
    "Vegetable",           # Vegetables
    "Fruit",               # Fruits
    "Nuts & Seeds",        # Nuts & Seeds
    "Dairy",               # Dairy products
    "Herbs & Spices",      # Herbs & Spices
    "Beverage",            # Beverages
    "Fat & Oil"            # Healthy oils
]

# Health goal normalization
GOAL_MAPPINGS = {
    "lose weight": "weight_loss",
    "weight loss": "weight_loss",
    "fat loss": "weight_loss",
    "gain weight": "weight_gain",
    "weight gain": "weight_gain",
    "muscle": "muscle_gain",
    "muscle gain": "muscle_gain",
    "build muscle": "muscle_gain",
    "diabetes": "diabetes_management",
    "blood sugar": "diabetes_management",
    "digestion": "digestive_health",
    "gut health": "digestive_health",
    "energy": "energy_boost",
    "heart": "heart_health",
    "immunity": "immunity_boost"
}


class SmartFoodRetriever:
    """
    Intelligent food retrieval that gets top foods per category
    based on comprehensive user profile analysis.
    """
    
    def __init__(self, db: Session):
        """Initialize with database session"""
        self.db = db
        self.food_retriever = FoodRetriever()  # Fallback to FAISS if needed
        logger.info("SmartFoodRetriever initialized")
    
    def get_foods_by_category_for_user(
        self,
        client_id: int,
        goals: Optional[str] = None,
        dosha_type: Optional[str] = None,
        diet_type: str = "veg",
        allergies: Optional[str] = None,
        medical_conditions: Optional[str] = None,
        top_k_per_category: int = 8,
        categories: Optional[List[str]] = None
    ) -> Dict[str, List[Dict]]:
        """
        Get top K foods for each category based on user profile.
        
        Args:
            client_id: Client database ID
            goals: Health goals (comma-separated)
            dosha_type: Primary dosha to balance
            diet_type: veg, vegan, non-veg
            allergies: Comma-separated allergens
            medical_conditions: Comma-separated conditions
            top_k_per_category: Number of foods to return per category
            categories: Specific categories to retrieve (None = all)
        
        Returns:
            Dict mapping category name to list of food dicts
        """
        logger.info(f"Smart food retrieval for client {client_id}")
        
        # Get dosha if not provided
        if not dosha_type:
            dosha_type = self._get_primary_dosha(client_id)
        
        # Parse user constraints
        allergy_list = self._parse_list(allergies)
        disease_list = self._parse_list(medical_conditions)
        goal_list = self._normalize_goals(goals)
        
        # Determine categories to retrieve
        categories_to_use = categories or FOOD_CATEGORIES
        
        # Retrieve foods for each category
        results = {}
        
        for category in categories_to_use:
            logger.info(f"Retrieving top {top_k_per_category} foods for category: {category}")
            
            foods = self._get_category_foods(
                category=category,
                dosha_type=dosha_type,
                primary_goal=goal_list[0] if goal_list else None,
                allergies=allergy_list,
                diseases=disease_list,
                diet_type=diet_type,
                top_k=top_k_per_category
            )
            
            if foods:
                results[category] = foods
                logger.info(f"Found {len(foods)} foods for {category}")
            else:
                logger.warning(f"No foods found for {category}")
        
        total_foods = sum(len(foods) for foods in results.values())
        logger.info(f"Total foods retrieved: {total_foods} across {len(results)} categories")
        
        return results
    
    def _get_category_foods(
        self,
        category: str,
        dosha_type: Optional[str],
        primary_goal: Optional[str],
        allergies: List[str],
        diseases: List[str],
        diet_type: str,
        top_k: int
    ) -> List[Dict]:
        """Get top foods for a specific category with smart filtering and ranking"""
        
        # Start with base query
        query = self.db.query(FoodItem).filter(FoodItem.category == category)
        
        # 1. EXCLUDE ALLERGENS
        if allergies:
            allergen_food_ids = self.db.query(FoodAllergen.food_id).filter(
                FoodAllergen.allergen.in_(allergies)
            ).distinct()
            query = query.filter(~FoodItem.id.in_(allergen_food_ids))
        
        # 2. EXCLUDE DISEASE CONTRAINDICATIONS
        if diseases:
            avoid_food_ids = self.db.query(FoodDiseaseRelation.food_id).filter(
                FoodDiseaseRelation.disease_condition.in_(diseases),
                FoodDiseaseRelation.relationship == 'avoid'
            ).distinct()
            query = query.filter(~FoodItem.id.in_(avoid_food_ids))
        
        # 3. DIET TYPE FILTERING
        if diet_type in ["veg", "vegetarian", "vegan"]:
            # Exclude non-veg items by name patterns
            query = query.filter(
                ~FoodItem.food_name.ilike('%chicken%'),
                ~FoodItem.food_name.ilike('%fish%'),
                ~FoodItem.food_name.ilike('%meat%'),
                ~FoodItem.food_name.ilike('%mutton%'),
                ~FoodItem.food_name.ilike('%egg%')
            )
        
        if diet_type == "vegan":
            # Also exclude dairy
            vegan_allergens = ['dairy', 'milk', 'ghee', 'honey']
            vegan_food_ids = self.db.query(FoodAllergen.food_id).filter(
                FoodAllergen.allergen.in_(vegan_allergens)
            ).distinct()
            query = query.filter(~FoodItem.id.in_(vegan_food_ids))
        
        # Get all qualifying foods
        foods = query.all()
        
        if not foods:
            logger.warning(f"No foods found for {category} after filtering")
            return []
        
        # 4. CALCULATE COMPOSITE SCORE FOR EACH FOOD
        scored_foods = []
        
        for food in foods:
            score = self._calculate_composite_score(
                food=food,
                dosha_type=dosha_type,
                primary_goal=primary_goal,
                diseases=diseases
            )
            
            food_dict = food.to_dict()
            food_dict['composite_score'] = score
            food_dict['score_breakdown'] = score  # Can add detailed breakdown later
            
            # Add dosha effect info
            dosha_effects = self._get_dosha_effects_for_food(food.id)
            food_dict['dosha_effects_detailed'] = dosha_effects
            
            scored_foods.append(food_dict)
        
        # 5. SORT BY SCORE AND RETURN TOP K
        scored_foods.sort(key=lambda x: x['composite_score'], reverse=True)
        
        return scored_foods[:top_k]
    
    def _calculate_composite_score(
        self,
        food: FoodItem,
        dosha_type: Optional[str],
        primary_goal: Optional[str],
        diseases: List[str]
    ) -> float:
        """
        Calculate composite score for a food based on multiple factors.
        
        Score = 40% Goal + 25% Dosha + 20% Health + 15% Disease Benefit
        """
        score = 0.0
        
        # 1. GOAL COMPATIBILITY (40%)
        if primary_goal:
            goal_score = self.db.query(FoodGoalScore.score).filter(
                FoodGoalScore.food_id == food.id,
                FoodGoalScore.health_goal == primary_goal
            ).scalar()
            
            if goal_score:
                score += goal_score * 0.40
            else:
                # Default goal score based on nutrition
                default_score = self._calculate_default_goal_score(food, primary_goal)
                score += default_score * 0.40
        else:
            score += 50 * 0.40  # Neutral if no goal
        
        # 2. DOSHA BALANCE (25%)
        if dosha_type:
            dosha_effect = self.db.query(FoodDoshaEffect).filter(
                FoodDoshaEffect.food_id == food.id,
                FoodDoshaEffect.dosha_type == dosha_type
            ).first()
            
            if dosha_effect:
                if dosha_effect.effect == "decrease":
                    # Good - decreases elevated dosha
                    score += (dosha_effect.intensity * 20) * 0.25  # Max 100 * 0.25
                elif dosha_effect.effect == "increase":
                    # Bad - increases elevated dosha
                    score += (20) * 0.25  # Low score
                else:
                    # Neutral
                    score += 50 * 0.25
            else:
                score += 50 * 0.25  # Neutral if no data
        else:
            score += 50 * 0.25  # Neutral if no dosha
        
        # 3. OVERALL HEALTH SCORE (20%)
        health_score = getattr(food, 'overall_health_score', None) or 50
        score += health_score * 0.20
        
        # 4. DISEASE BENEFIT (15%)
        if diseases:
            # Check if food is beneficial for any of user's conditions
            beneficial_count = self.db.query(func.count(FoodDiseaseRelation.id)).filter(
                FoodDiseaseRelation.food_id == food.id,
                FoodDiseaseRelation.disease_condition.in_(diseases),
                FoodDiseaseRelation.relationship == 'beneficial'
            ).scalar()
            
            if beneficial_count > 0:
                score += 80 * 0.15  # Bonus for being beneficial
            else:
                score += 50 * 0.15  # Neutral
        else:
            score += 50 * 0.15  # Neutral if no diseases
        
        return round(score, 2)
    
    def _calculate_default_goal_score(self, food: FoodItem, goal: str) -> float:
        """Calculate default goal score based on nutrition when no explicit score exists"""
        
        # Weight loss - prefer low calorie, high fiber, high protein
        if goal == "weight_loss":
            score = 50
            if food.energy_kcal and food.energy_kcal < 200:
                score += 20
            if food.protein_g and food.protein_g > 10:
                score += 15
            if food.fat_g and food.fat_g < 5:
                score += 15
            return min(score, 100)
        
        # Muscle gain - prefer high protein
        elif goal == "muscle_gain":
            score = 50
            if food.protein_g:
                if food.protein_g > 20:
                    score += 40
                elif food.protein_g > 10:
                    score += 25
            return min(score, 100)
        
        # Diabetes - prefer low GI (if available)
        elif goal == "diabetes_management":
            score = 50
            if hasattr(food, 'glycemic_index') and food.glycemic_index:
                if food.glycemic_index < 40:
                    score += 30
                elif food.glycemic_index < 55:
                    score += 20
            if food.carbs_g and food.carbs_g < 30:
                score += 20
            return min(score, 100)
        
        # Heart health - prefer low fat, high fiber
        elif goal == "heart_health":
            score = 50
            if food.fat_g and food.fat_g < 5:
                score += 30
            if hasattr(food, 'fiber_g') and food.fiber_g and food.fiber_g > 5:
                score += 20
            return min(score, 100)
        
        return 50  # Default neutral score
    
    def _get_dosha_effects_for_food(self, food_id: int) -> Dict[str, str]:
        """Get dosha effects for a food in readable format"""
        effects = self.db.query(FoodDoshaEffect).filter(
            FoodDoshaEffect.food_id == food_id
        ).all()
        
        result = {}
        for effect in effects:
            arrow = "↑" if effect.effect == "increase" else "↓" if effect.effect == "decrease" else "="
            result[effect.dosha_type] = f"{arrow} (intensity: {effect.intensity})"
        
        return result
    
    def _get_primary_dosha(self, client_id: int) -> Optional[str]:
        """Get primary dosha from quiz results"""
        quiz_result = self.db.query(DoshaQuiz).filter(
            DoshaQuiz.client_id == client_id
        ).order_by(DoshaQuiz.created_at.desc()).first()
        
        if not quiz_result:
            return None
        
        doshas = {
            "Vata": quiz_result.vata_score or 0,
            "Pitta": quiz_result.pitta_score or 0,
            "Kapha": quiz_result.kapha_score or 0
        }
        primary = max(doshas, key=doshas.get)
        logger.info(f"Primary dosha for client {client_id}: {primary}")
        return primary
    
    def _parse_list(self, text: Optional[str]) -> List[str]:
        """Parse comma-separated text into list"""
        if not text:
            return []
        return [item.strip().lower() for item in text.split(",") if item.strip()]
    
    def _normalize_goals(self, goals: Optional[str]) -> List[str]:
        """Normalize health goals to standard format"""
        if not goals:
            return []
        
        goals_lower = goals.lower()
        normalized = []
        
        for key, value in GOAL_MAPPINGS.items():
            if key in goals_lower and value not in normalized:
                normalized.append(value)
        
        # If no matches, add as-is
        if not normalized:
            normalized.append(goals.replace(" ", "_").lower())
        
        return normalized
    
    def get_category_summary(self) -> Dict[str, int]:
        """Get count of foods in each category"""
        categories = self.db.query(
            FoodItem.category,
            func.count(FoodItem.id)
        ).group_by(FoodItem.category).all()
        
        return {cat: count for cat, count in categories}
    
    def get_allergen_affected_foods(self, allergen: str) -> List[Dict]:
        """Get all foods containing a specific allergen"""
        allergen_records = self.db.query(FoodAllergen).filter(
            FoodAllergen.allergen.ilike(f"%{allergen}%")
        ).all()
        
        food_ids = [rec.food_id for rec in allergen_records]
        foods = self.db.query(FoodItem).filter(FoodItem.id.in_(food_ids)).all()
        
        return [food.to_dict() for food in foods]
    
    def get_disease_safe_foods(self, disease: str, category: Optional[str] = None) -> List[Dict]:
        """Get foods that are safe/beneficial for a disease"""
        # Get beneficial foods
        beneficial = self.db.query(FoodDiseaseRelation.food_id).filter(
            FoodDiseaseRelation.disease_condition.ilike(f"%{disease}%"),
            FoodDiseaseRelation.relationship.in_(['beneficial', 'neutral'])
        ).distinct()
        
        # Get foods to avoid
        avoid = self.db.query(FoodDiseaseRelation.food_id).filter(
            FoodDiseaseRelation.disease_condition.ilike(f"%{disease}%"),
            FoodDiseaseRelation.relationship == 'avoid'
        ).distinct()
        
        # Build query
        query = self.db.query(FoodItem)
        
        if category:
            query = query.filter(FoodItem.category == category)
        
        # Include beneficial, exclude avoid
        query = query.filter(
            or_(
                FoodItem.id.in_(beneficial),
                ~FoodItem.id.in_(avoid)
            )
        )
        
        foods = query.limit(20).all()
        return [food.to_dict() for food in foods]
    
    def get_dosha_balancing_foods(
        self,
        dosha_type: str,
        category: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict]:
        """Get foods that decrease/balance a specific dosha"""
        
        # Get food IDs that decrease this dosha
        balancing_effects = self.db.query(FoodDoshaEffect).filter(
            FoodDoshaEffect.dosha_type == dosha_type,
            FoodDoshaEffect.effect == 'decrease'
        ).order_by(FoodDoshaEffect.intensity.desc()).all()
        
        food_ids = [effect.food_id for effect in balancing_effects]
        
        # Get foods
        query = self.db.query(FoodItem).filter(FoodItem.id.in_(food_ids))
        
        if category:
            query = query.filter(FoodItem.category == category)
        
        foods = query.limit(top_k).all()
        
        # Add dosha effect info
        results = []
        for food in foods:
            food_dict = food.to_dict()
            effect = next((e for e in balancing_effects if e.food_id == food.id), None)
            if effect:
                food_dict['dosha_balancing_intensity'] = effect.intensity
            results.append(food_dict)
        
        return results

