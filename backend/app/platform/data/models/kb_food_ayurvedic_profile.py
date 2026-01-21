"""
Knowledge Base Food Ayurvedic Profile ORM model.
Ayurvedic and traditional properties.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class KBFoodAyurvedicProfile(Base):
    """
    Knowledge base food Ayurvedic profile model.
    
    Stores Ayurvedic properties: dosha effects, guna, rasa, virya, vipaka,
    and digestion-related information.
    """
    
    __tablename__ = "kb_food_ayurvedic_profile"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    food_id = Column(String(100), ForeignKey("kb_food_master.food_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Dosha effects
    dosha_effects = Column(JSONB, nullable=True)
    
    # Basic properties
    guna = Column(String(50), nullable=True)
    rasa = Column(ARRAY(String), nullable=True)
    virya = Column(String(50), nullable=True)
    vipaka = Column(String(50), nullable=True)
    
    # Digestion
    agni_effect = Column(String(50), nullable=True)
    digestive_load = Column(String(50), nullable=True)
    
    # Preferences
    food_temperature_preference = Column(String(50), nullable=True)
    cooking_method_preference = Column(ARRAY(String), nullable=True)
    meal_timing_preference = Column(ARRAY(String), nullable=True)
    season_preference = Column(ARRAY(String), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship (food_id references kb_food_master.food_id)
    food = relationship("KBFoodMaster", back_populates="ayurvedic_profile", primaryjoin="KBFoodAyurvedicProfile.food_id == KBFoodMaster.food_id")
    
    __table_args__ = (
        Index('idx_food_ayurvedic_food_id', 'food_id', unique=True),
    )
    
    def __repr__(self):
        return f"<KBFoodAyurvedicProfile {self.food_id}>"

