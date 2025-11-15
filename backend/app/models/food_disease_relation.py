"""
Food Disease Relation Model

Stores relationships between foods and medical conditions.
Enables safe food recommendations based on user's health conditions.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship as orm_relationship
from app.database import Base


class FoodDiseaseRelation(Base):
    """
    Model for storing how foods relate to medical conditions.
    
    Example:
    - Moong Dal + Diabetes: beneficial (helps manage blood sugar)
    - White Sugar + Diabetes: avoid (spikes blood sugar)
    - Banana + Kidney Disease: caution (high potassium)
    """
    __tablename__ = "food_disease_relations"
    
    id = Column(Integer, primary_key=True, index=True)
    food_id = Column(Integer, ForeignKey("food_items.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Disease information
    disease_condition = Column(String(100), nullable=False, index=True)
    relationship = Column(String(20), nullable=False)  # beneficial, avoid, neutral, caution
    reason = Column(Text)
    severity = Column(Integer, default=1)  # 1-5 scale (how important this is)
    
    # Relationship
    food_item = orm_relationship("FoodItem", backref="disease_relations")
    
    __table_args__ = (
        UniqueConstraint('food_id', 'disease_condition', name='unique_food_disease'),
    )
    
    def __repr__(self):
        return f"<FoodDiseaseRelation({self.disease_condition}: {self.relationship})>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "food_id": self.food_id,
            "disease_condition": self.disease_condition,
            "relationship": self.relationship,
            "reason": self.reason,
            "severity": self.severity
        }

