"""
Platform Meal Structure ORM model.
Stores meal structure skeleton (no food items).
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class PlatformMealStructure(Base):
    """
    Platform meal structure model.
    
    Stores structural meal plan skeleton (no food items).
    Defines the shape of the day - number of meals, timing windows,
    calorie allocation, protein distribution, and macro guardrails.
    """
    
    __tablename__ = "platform_meal_structures"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("platform_assessments.id"), nullable=False, unique=True)
    meal_count = Column(Integer, nullable=False)
    meals = Column(JSONB, nullable=False)  # List of meal names ["breakfast", "lunch", "snack", "dinner"]
    timing_windows = Column(JSONB, nullable=False)  # {"breakfast": ["07:30", "09:00"]}
    energy_weight = Column(JSONB, nullable=True)  # {"breakfast": 0.225, ...} - Relative allocation weights (sum = 1.0)
    macro_intent = Column(JSONB, nullable=True)  # {"breakfast": {"carbs": "medium", "fat": "low"}, ...} - Qualitative guidance
    flags = Column(JSONB, nullable=True)  # List of validation flags
    # Legacy fields (deprecated, kept for backward compatibility)
    calorie_split = Column(JSONB, nullable=True)  # {"breakfast": 500, ...} - DEPRECATED
    protein_split = Column(JSONB, nullable=True)  # {"breakfast": 20, ...} - DEPRECATED
    macro_guardrails = Column(JSONB, nullable=True)  # {"breakfast": {"carb_pct": [40, 55]}} - DEPRECATED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    assessment = relationship("PlatformAssessment", backref="meal_structures")
    
    def __repr__(self):
        return f"<PlatformMealStructure {self.id}>"

