"""
Platform Food Allocation Approval ORM model.
Stores approval status for food allocations per meal per day.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class PlatformFoodAllocationApproval(Base):
    """
    Platform food allocation approval model.
    
    Stores approval status for food allocations generated in Phase 1.
    Each record represents approval status for a specific meal on a specific day.
    """
    
    __tablename__ = "platform_food_allocation_approvals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("platform_assessments.id"), nullable=False, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("platform_diet_plans.id"), nullable=True, index=True)
    day_number = Column(String, nullable=False)  # "day_1", "day_2", etc.
    meal_name = Column(String, nullable=False)  # "breakfast", "lunch", etc.
    is_approved = Column(Boolean, default=False, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(UUID(as_uuid=True), nullable=True)  # User ID who approved
    notes = Column(JSONB, nullable=True)  # Optional notes or comments
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    assessment = relationship("PlatformAssessment", backref="food_allocation_approvals")
    plan = relationship("PlatformDietPlan", backref="food_allocation_approvals")
    
    def __repr__(self):
        return f"<PlatformFoodAllocationApproval {self.id} - {self.day_number}/{self.meal_name}: {self.is_approved}>"
