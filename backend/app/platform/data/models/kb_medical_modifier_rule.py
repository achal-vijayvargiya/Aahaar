"""
Knowledge Base Medical Modifier Rule ORM model.
Read-only reference table for medical modifier rules.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.database import Base


class KBMedicalModifierRule(Base):
    """
    Knowledge base medical modifier rule model.
    
    Defines how medical conditions modify exchange allocation and meal structure.
    Read-only reference table for medical modifier rules.
    """
    
    __tablename__ = "kb_medical_modifier_rules"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Core identification
    modifier_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Application
    condition_id = Column(String(100), nullable=False, index=True)  # FK to Medical Conditions KB
    category_id = Column(String(100), nullable=True, index=True)  # Exchange category (optional)
    
    # Modification type
    modification_type = Column(String(50), nullable=False)  # restrict, increase, replace, adjust_timing
    modification_value = Column(JSONB, nullable=False)  # { "percent_change": -20 } or { "absolute_change": 2 }
    
    # Scope
    applies_to_meals = Column(JSONB, nullable=True)  # ["breakfast", "lunch", "dinner"] or null for all
    applies_to_exchange_categories = Column(JSONB, nullable=True)  # ["cereal", "pulse"] or null for all
    
    # Priority
    priority = Column(Integer, nullable=False, index=True)  # For conflict resolution
    
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
        Index('idx_modifier_id', 'modifier_id'),
        Index('idx_condition_id', 'condition_id'),
        Index('idx_priority', 'priority'),
        Index('idx_status', 'status'),
    )
    
    def __repr__(self):
        return f"<KBMedicalModifierRule {self.modifier_id}>"

