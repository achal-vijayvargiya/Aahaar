"""
Diet Plan models for storing personalized meal plans.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.database import Base


class DietPlan(Base):
    """
    Diet Plan model for storing personalized 7-day meal plans.
    """
    __tablename__ = "diet_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)  # e.g., "Weight Loss Plan - Week 1"
    description = Column(Text)  # Overall plan description
    
    # Planning parameters
    duration_days = Column(Integer, default=7)  # Usually 7 days
    start_date = Column(DateTime)  # When to start the plan
    end_date = Column(DateTime)  # When the plan ends
    
    # Health context (snapshot at time of creation)
    health_goals = Column(Text)  # Goals from health profile
    dosha_type = Column(String(50))  # Primary dosha to balance
    diet_type = Column(String(50))  # veg, non_veg, vegan, eggetarian
    allergies = Column(Text)  # Allergies to avoid
    
    # Nutritional targets (daily)
    target_calories = Column(Float)
    target_protein_g = Column(Float)
    target_carbs_g = Column(Float)
    target_fat_g = Column(Float)
    
    # Status
    status = Column(String(50), default="draft")  # draft, active, completed, archived
    
    # Metadata
    created_by_id = Column(Integer, ForeignKey("users.id"))  # Nutritionist/doctor who created it
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = relationship("Client", backref="diet_plans")
    created_by = relationship("User", foreign_keys=[created_by_id])
    meals = relationship("DietPlanMeal", back_populates="diet_plan", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<DietPlan id={self.id} client_id={self.client_id} name='{self.name}'>"


class DietPlanMeal(Base):
    """
    Individual meal entries in a diet plan.
    
    Each meal represents one row in the 7-day plan template.
    """
    __tablename__ = "diet_plan_meals"
    
    id = Column(Integer, primary_key=True, index=True)
    diet_plan_id = Column(Integer, ForeignKey("diet_plans.id"), nullable=False, index=True)
    
    # Meal scheduling
    day_number = Column(Integer, nullable=False)  # 1-7
    meal_time = Column(String(20), nullable=False)  # e.g., "6:30 AM"
    meal_type = Column(String(50), nullable=False)  # Morning Cleanse, Breakfast, Mid Snack, Lunch, Evening Snack, Dinner, Sleep Tonic
    
    # Meal details
    food_dish = Column(Text, nullable=False)  # Name of the food/dish
    food_item_ids = Column(Text)  # Comma-separated IDs of food items from food_items table
    healing_purpose = Column(Text)  # Why this food is chosen (e.g., "Reduces inflammation")
    portion = Column(String(100))  # Portion size (e.g., "1 cup", "150g")
    dosha_notes = Column(Text)  # Dosha-specific notes
    notes = Column(Text)  # General notes or instructions
    
    # Nutritional info for this meal
    calories = Column(Float)
    protein_g = Column(Float)
    carbs_g = Column(Float)
    fat_g = Column(Float)
    
    # Ordering
    order_in_day = Column(Integer, default=0)  # For sorting meals within a day
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    diet_plan = relationship("DietPlan", back_populates="meals")
    
    def __repr__(self):
        return f"<DietPlanMeal day={self.day_number} type='{self.meal_type}' food='{self.food_dish}'>"
    
    def to_dict(self):
        """Convert meal to dictionary"""
        return {
            "id": self.id,
            "day_number": self.day_number,
            "meal_time": self.meal_time,
            "meal_type": self.meal_type,
            "food_dish": self.food_dish,
            "healing_purpose": self.healing_purpose,
            "portion": self.portion,
            "dosha_notes": self.dosha_notes,
            "notes": self.notes,
            "calories": self.calories,
            "protein_g": self.protein_g,
            "carbs_g": self.carbs_g,
            "fat_g": self.fat_g,
            "food_item_ids": self.food_item_ids
        }

