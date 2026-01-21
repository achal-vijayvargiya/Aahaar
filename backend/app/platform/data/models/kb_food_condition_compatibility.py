"""
Knowledge Base Food-Condition Compatibility ORM model.
Read-only reference table for food-condition compatibility.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.database import Base


class KBFoodConditionCompatibility(Base):
    """
    Knowledge base food-condition compatibility model.
    
    Defines which foods are safe, caution, avoid, or contraindicated for conditions.
    Read-only reference table for food-condition compatibility matrix.
    """
    
    __tablename__ = "kb_food_condition_compatibility"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Core identification
    food_id = Column(String(100), nullable=False, index=True)  # FK to Food KB
    condition_id = Column(String(100), nullable=False, index=True)  # FK to Medical Conditions KB
    
    # Compatibility
    compatibility = Column(String(50), nullable=False, index=True)  # safe, caution, avoid, contraindicated
    severity_modifier = Column(JSONB, nullable=True)  # { "mild": "safe", "moderate": "caution", "severe": "avoid" }
    
    # Restrictions
    portion_limit = Column(JSONB, nullable=True)  # { "max_g_per_day": 50, "max_g_per_meal": 25 }
    preparation_notes = Column(String(500), nullable=True)
    
    # Evidence
    evidence = Column(String(500), nullable=True)
    
    # Metadata
    source = Column(String(200), nullable=True)
    source_reference = Column(String(500), nullable=True)
    version = Column(String(20), default='1.0')
    status = Column(String(20), default='active', index=True)  # active, deprecated
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewed_by = Column(String(100), nullable=True)
    review_date = Column(DateTime, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_food_condition', 'food_id', 'condition_id', unique=True),
        Index('idx_food_id', 'food_id'),
        Index('idx_condition_id', 'condition_id'),
        Index('idx_compatibility', 'compatibility'),
        Index('idx_status', 'status'),
    )
    
    def __repr__(self):
        return f"<KBFoodConditionCompatibility {self.food_id}:{self.condition_id}>"

