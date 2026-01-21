"""
Knowledge Base Food MNT Profile ORM model.
Medical Nutrition Therapy compatibility (all fields derived).
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class KBFoodMNTProfile(Base):
    """
    Knowledge base food MNT profile model.
    
    Stores Medical Nutrition Therapy compatibility information.
    All fields are DERIVED (computed from nutrition data and MNT rules).
    Never manually edited.
    """
    
    __tablename__ = "kb_food_mnt_profile"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    food_id = Column(String(100), ForeignKey("kb_food_master.food_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Macro compliance flags
    macro_compliance = Column(JSONB, nullable=True)
    
    # Micro compliance flags
    micro_compliance = Column(JSONB, nullable=True)
    
    # Medical condition safety tags
    medical_tags = Column(JSONB, nullable=True)
    
    # Exclusion/inclusion tags
    food_exclusion_tags = Column(ARRAY(String), nullable=True)
    food_inclusion_tags = Column(ARRAY(String), nullable=True)
    
    # Contraindications and preferences
    contraindications = Column(ARRAY(String), nullable=True)
    preferred_conditions = Column(ARRAY(String), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship (food_id references kb_food_master.food_id)
    food = relationship("KBFoodMaster", back_populates="mnt_profile", primaryjoin="KBFoodMNTProfile.food_id == KBFoodMaster.food_id")
    
    __table_args__ = (
        Index('idx_food_mnt_food_id', 'food_id', unique=True),
    )
    
    def __repr__(self):
        return f"<KBFoodMNTProfile {self.food_id}>"

