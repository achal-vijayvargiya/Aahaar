"""
Knowledge Base Lab Threshold ORM model.
Read-only reference table for lab value thresholds.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.database import Base


class KBLabThreshold(Base):
    """
    Knowledge base lab threshold model.
    
    Stores standard reference ranges and abnormal thresholds for lab values.
    Read-only reference table for lab thresholds.
    """
    
    __tablename__ = "kb_lab_thresholds"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Core identification
    lab_name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    
    # Thresholds
    normal_range = Column(JSONB, nullable=True)  # { "min": 4.0, "max": 5.6, "unit": "%" }
    abnormal_ranges = Column(JSONB, nullable=True)  # { "mild": {...}, "moderate": {...}, "severe": {...} }
    
    # Units and conversions
    units = Column(JSONB, nullable=True)  # ["%", "mg/dL", "mmol/L"]
    conversion_factors = Column(JSONB, nullable=True)  # { "mg/dL": 1.0, "mmol/L": 0.0555 }
    
    # Metadata
    source = Column(String(200), nullable=True)
    source_reference = Column(String(500), nullable=True)
    version = Column(String(20), default='1.0')
    status = Column(String(20), default='active', index=True)  # active, deprecated
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_updated = Column(DateTime, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_lab_name', 'lab_name'),
        Index('idx_status', 'status'),
    )
    
    def __repr__(self):
        return f"<KBLabThreshold {self.lab_name}>"

