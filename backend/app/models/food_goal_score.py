"""
Food Goal Score Model

Stores how well each food supports different health goals.
Enables intelligent ranking based on user's objectives.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship as orm_relationship
from app.database import Base


class FoodGoalScore(Base):
    """
    Model for storing food effectiveness for different health goals.
    
    Example:
    - Moong Dal + Weight Loss: 85/100 (low cal, high fiber, filling)
    - Moong Dal + Muscle Gain: 75/100 (good protein, moderate)
    - Avocado + Weight Loss: 40/100 (high calorie, high fat)
    - Avocado + Heart Health: 90/100 (healthy fats, nutrients)
    """
    __tablename__ = "food_goal_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    food_id = Column(Integer, ForeignKey("food_items.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Goal information
    health_goal = Column(String(100), nullable=False, index=True)  # weight_loss, muscle_gain, etc.
    score = Column(Integer, nullable=False)  # 0-100 scale
    reason = Column(Text)  # Why this score
    
    # Relationship
    food_item = orm_relationship("FoodItem", backref="goal_scores")
    
    __table_args__ = (
        UniqueConstraint('food_id', 'health_goal', name='unique_food_goal'),
    )
    
    def __repr__(self):
        return f"<FoodGoalScore({self.health_goal}: {self.score}/100)>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "food_id": self.food_id,
            "health_goal": self.health_goal,
            "score": self.score,
            "reason": self.reason
        }

