"""
Knowledge Base Food Master ORM model.
Master table for food identity and metadata.
"""
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class KBFoodMaster(Base):
    """
    Knowledge base food master model.
    
    Stores food identity, basic information, and metadata.
    This is the primary table for foods, linked to by all other food tables.
    """
    
    __tablename__ = "kb_food_master"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    food_id = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    aliases = Column(ARRAY(String), nullable=True)
    category = Column(String(100), nullable=True, index=True)
    food_type = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    diet_type = Column(ARRAY(String), nullable=True)
    cooking_state = Column(String(50), nullable=True)
    common_serving_unit = Column(String(50), nullable=True)
    common_serving_size_g = Column(Numeric(10, 2), nullable=True)
    version = Column(String(20), default='1.0')
    status = Column(String(20), default='active', index=True)
    source = Column(String(200), nullable=True)
    source_reference = Column(String(500), nullable=True)
    last_reviewed = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    nutrition = relationship("KBFoodNutritionBase", back_populates="food", uselist=False, cascade="all, delete-orphan")
    exchange_profile = relationship("KBFoodExchangeProfile", back_populates="food", uselist=False, cascade="all, delete-orphan")
    mnt_profile = relationship("KBFoodMNTProfile", back_populates="food", uselist=False, cascade="all, delete-orphan")
    ayurvedic_profile = relationship("KBFoodAyurvedicProfile", back_populates="food", uselist=False, cascade="all, delete-orphan")
    recipe_profile = relationship("KBFoodRecipeProfile", back_populates="food", uselist=False, cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_food_master_food_id', 'food_id', unique=True),
        Index('idx_food_master_category', 'category'),
        Index('idx_food_master_status', 'status'),
    )
    
    def __repr__(self):
        return f"<KBFoodMaster {self.food_id}>"

