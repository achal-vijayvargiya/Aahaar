"""
Platform Diet Plan ORM model.
Stores versioned diet plans.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class PlatformDietPlan(Base):
    """
    Platform diet plan model.
    
    Stores versioned diet plans with meal plans, explanations, and constraint snapshots.
    """
    
    __tablename__ = "platform_diet_plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("platform_clients.id"), nullable=False)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("platform_assessments.id"), nullable=False)
    plan_version = Column(Integer, nullable=True)
    status = Column(String, nullable=True)  # active | archived | draft
    meal_plan = Column(JSONB, nullable=True)
    explanations = Column(JSONB, nullable=True)
    constraints_snapshot = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    client = relationship("PlatformClient", backref="diet_plans")
    assessment = relationship("PlatformAssessment", backref="diet_plans")
    
    def __repr__(self):
        return f"<PlatformDietPlan {self.id}>"

