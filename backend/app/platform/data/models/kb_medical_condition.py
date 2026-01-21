"""
Knowledge Base Medical Condition ORM model.
Read-only reference table for medical conditions.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.database import Base


class KBMedicalCondition(Base):
    """
    Knowledge base medical condition model.
    
    Read-only reference table for medical conditions.
    Mirrors KB documents and is never modified at runtime.
    """
    
    __tablename__ = "kb_medical_conditions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Core identification
    condition_id = Column(String(100), unique=True, nullable=True, index=True)
    display_name = Column(String(200), nullable=True)
    category = Column(String(50), nullable=True, index=True)  # metabolic, cardiovascular, etc.
    description = Column(String(1000), nullable=True)
    
    # Lab thresholds and severity
    critical_labs = Column(JSONB, nullable=True)  # ["HbA1c", "FBS"]
    severity_thresholds = Column(JSONB, nullable=True)  # { "HbA1c": { "mild": {...}, "moderate": {...} } }
    
    # Clinical information
    associated_risks = Column(JSONB, nullable=True)  # ["insulin_resistance", "cardiovascular_risk"]
    nutrition_focus_areas = Column(JSONB, nullable=True)  # ["carbohydrate_control", "fiber_intake"]
    red_flags = Column(JSONB, nullable=True)  # ["hypoglycemia", "very_high_glucose"]
    
    # Metadata
    source = Column(String(200), nullable=True)
    source_reference = Column(String(500), nullable=True)
    version = Column(String(20), default='1.0')
    status = Column(String(20), default='active', index=True)  # active, deprecated
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_reviewed = Column(DateTime, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    review_date = Column(DateTime, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_condition_id', 'condition_id'),
        Index('idx_category', 'category'),
        Index('idx_status', 'status'),
    )
    
    def __repr__(self):
        return f"<KBMedicalCondition {self.condition_id or self.id}>"

