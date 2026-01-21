"""
Knowledge Base Food Recipe Profile ORM model.
Recipe usage, pairing intelligence, and retrieval scoring.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class KBFoodRecipeProfile(Base):
    """
    Knowledge base food recipe profile model.
    
    Stores recipe compatibility, retrieval scoring, and dietary properties.
    Used for food selection and recipe generation.
    """
    
    __tablename__ = "kb_food_recipe_profile"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    food_id = Column(String(100), ForeignKey("kb_food_master.food_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Recipe compatibility
    recipe_compatibility = Column(JSONB, nullable=True)
    
    # Retrieval scoring
    retrieval_scoring = Column(JSONB, nullable=True)
    
    # Dietary properties
    dietary_properties = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship (food_id references kb_food_master.food_id)
    food = relationship("KBFoodMaster", back_populates="recipe_profile", primaryjoin="KBFoodRecipeProfile.food_id == KBFoodMaster.food_id")
    
    __table_args__ = (
        Index('idx_food_recipe_food_id', 'food_id', unique=True),
    )
    
    def __repr__(self):
        return f"<KBFoodRecipeProfile {self.food_id}>"

