"""
Knowledge Base Food Nutrition Base ORM model.
Raw nutrient values per 100g (IFCT/USDA sourced).
"""
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class KBFoodNutritionBase(Base):
    """
    Knowledge base food nutrition base model.
    
    Stores raw nutrient values per 100g.
    Immutable ground truth data from IFCT/USDA sources.
    """
    
    __tablename__ = "kb_food_nutrition_base"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    food_id = Column(String(100), ForeignKey("kb_food_master.food_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Energy
    calories_kcal = Column(Numeric(10, 2), nullable=True)
    
    # Macros (JSONB for flexibility)
    macros = Column(JSONB, nullable=True)
    
    # Micros (JSONB for flexibility)
    micros = Column(JSONB, nullable=True)
    
    # Glycemic properties (JSONB for flexibility)
    glycemic_properties = Column(JSONB, nullable=True)
    
    # Density metrics
    calorie_density_kcal_per_g = Column(Numeric(10, 4), nullable=True)
    protein_density_g_per_100kcal = Column(Numeric(10, 4), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship (food_id references kb_food_master.food_id)
    food = relationship("KBFoodMaster", back_populates="nutrition", primaryjoin="KBFoodNutritionBase.food_id == KBFoodMaster.food_id")
    
    __table_args__ = (
        Index('idx_food_nutrition_food_id', 'food_id', unique=True),
    )
    
    def __repr__(self):
        return f"<KBFoodNutritionBase {self.food_id}>"

