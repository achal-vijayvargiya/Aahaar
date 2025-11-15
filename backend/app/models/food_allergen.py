"""
Food Allergen Model

Tags foods with their allergen content for safe filtering.
"""
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship as orm_relationship
from app.database import Base


class FoodAllergen(Base):
    """
    Model for tagging foods with allergen content.
    
    Example:
    - Paneer: dairy (major), lactose (major)
    - Peanut Butter: peanuts (major), nuts (major)
    - Wheat Bread: gluten (major), wheat (major)
    """
    __tablename__ = "food_allergens"
    
    id = Column(Integer, primary_key=True, index=True)
    food_id = Column(Integer, ForeignKey("food_items.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Allergen information
    allergen = Column(String(100), nullable=False, index=True)  # dairy, nuts, gluten, etc.
    allergen_category = Column(String(50))  # protein, grain, legume
    severity = Column(String(20), default="major")  # major, minor, trace
    
    # Relationship
    food_item = orm_relationship("FoodItem", backref="allergens")
    
    __table_args__ = (
        UniqueConstraint('food_id', 'allergen', name='unique_food_allergen'),
    )
    
    def __repr__(self):
        return f"<FoodAllergen({self.allergen}: {self.severity})>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "food_id": self.food_id,
            "allergen": self.allergen,
            "allergen_category": self.allergen_category,
            "severity": self.severity
        }

