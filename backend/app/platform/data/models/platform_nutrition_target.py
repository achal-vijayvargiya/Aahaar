"""
Platform Nutrition Target ORM model.
Stores calculated nutrition targets.
"""
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class PlatformNutritionTarget(Base):
    """
    Platform nutrition target model.
    
    Stores calculated nutrition targets including calories, macros, and key micros.
    """
    
    __tablename__ = "platform_nutrition_targets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("platform_assessments.id"), nullable=False)
    calories_target = Column(Numeric, nullable=True)
    macros = Column(JSONB, nullable=True)
    key_micros = Column(JSONB, nullable=True)
    calculation_source = Column(String, nullable=True)  # bmr | tdee | custom
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    assessment = relationship("PlatformAssessment", backref="nutrition_targets")
    
    def __repr__(self):
        return f"<PlatformNutritionTarget {self.id}>"

