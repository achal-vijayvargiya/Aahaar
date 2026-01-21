"""
Platform MNT Constraint ORM model.
Stores Medical Nutrition Therapy constraints.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class PlatformMNTConstraint(Base):
    """
    Platform MNT constraint model.
    
    Stores Medical Nutrition Therapy constraints including macro/micro constraints
    and food exclusions with rule references.
    """
    
    __tablename__ = "platform_mnt_constraints"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("platform_assessments.id"), nullable=False)
    rule_id = Column(String, nullable=True)  # references MNT KB
    priority = Column(Integer, nullable=True)
    macro_constraints = Column(JSONB, nullable=True)
    micro_constraints = Column(JSONB, nullable=True)
    food_exclusions = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    assessment = relationship("PlatformAssessment", backref="mnt_constraints")
    
    def __repr__(self):
        return f"<PlatformMNTConstraint {self.id}>"

