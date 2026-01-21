"""
Knowledge Base MNT Rule ORM model.
Read-only reference table for MNT rules.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.database import Base


class KBMNTRule(Base):
    """
    Knowledge base MNT rule model.
    
    Read-only reference table for Medical Nutrition Therapy rules.
    Mirrors KB documents and is never modified at runtime.
    """
    
    __tablename__ = "kb_mnt_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Core identification
    rule_id = Column(String(100), unique=True, nullable=True, index=True)
    
    # Application
    applies_to_diagnoses = Column(JSONB, nullable=True)  # ["type_2_diabetes", "excess_carbohydrate_intake"]
    
    # Priority
    priority_level = Column(Integer, nullable=True, index=True)  # 1-4 (critical=4, high=3, medium=2, low=1)
    priority_label = Column(String(20), nullable=True)  # critical, high, medium, low
    
    # Constraints
    macro_constraints = Column(JSONB, nullable=True)  # { "carbohydrates_percent": { "max": 45 } }
    micro_constraints = Column(JSONB, nullable=True)  # { "fiber_g": { "min": 25 } }
    food_exclusions = Column(JSONB, nullable=True)  # ["refined_sugar", "white_flour"]
    food_inclusions = Column(JSONB, nullable=True)  # ["whole_grains", "fiber_rich"]
    
    # Meal distribution
    meal_distribution = Column(JSONB, nullable=True)  # { "carb_spread": "even" }
    
    # Override and conflict
    override_allowed = Column(Boolean, default=False)
    conflict_resolution = Column(String(200), nullable=True)
    
    # Evidence
    evidence_level = Column(String(10), nullable=True)  # A, B, C, D
    
    # Metadata
    source = Column(String(200), nullable=True)
    source_reference = Column(String(500), nullable=True)
    version = Column(String(20), default='1.0')
    status = Column(String(20), default='active', index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_reviewed = Column(DateTime, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    review_date = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_rule_id', 'rule_id'),
        Index('idx_priority_level', 'priority_level'),
        Index('idx_status', 'status'),
    )
    
    def __repr__(self):
        return f"<KBMNTRule {self.rule_id or self.id}>"

