"""
Knowledge Base Nutrition Diagnosis ORM model.
Read-only reference table for nutrition diagnoses.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.database import Base


class KBNutritionDiagnosis(Base):
    """
    Knowledge base nutrition diagnosis model.
    
    Read-only reference table for nutrition diagnoses.
    Mirrors KB documents and is never modified at runtime.
    """
    
    __tablename__ = "kb_nutrition_diagnoses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Core identification
    diagnosis_id = Column(String(100), unique=True, nullable=True, index=True)
    problem_statement = Column(String(500), nullable=True)
    
    # Triggers
    trigger_conditions = Column(JSONB, nullable=True)  # ["type_2_diabetes", "prediabetes"]
    trigger_labs = Column(JSONB, nullable=True)  # { "HbA1c": { "min": 7.0, "unit": "%" } }
    trigger_anthropometry = Column(JSONB, nullable=True)  # { "bmi": { "min": 30 } }
    trigger_diet_history = Column(JSONB, nullable=True)  # { "carb_intake_percent": { "min": 50 } }
    
    # Assessment
    severity_logic = Column(String(100), nullable=True)  # "distance_from_threshold", etc.
    evidence_types = Column(JSONB, nullable=True)  # ["lab", "anthropometry", "diet_history"]
    
    # Impact
    affected_domains = Column(JSONB, nullable=True)  # ["macros", "micros", "food_selection", "meal_timing"]
    linked_conditions = Column(JSONB, nullable=True)  # ["type_2_diabetes", "prediabetes"]
    
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
        Index('idx_diagnosis_id', 'diagnosis_id'),
        Index('idx_status', 'status'),
    )
    
    def __repr__(self):
        return f"<KBNutritionDiagnosis {self.diagnosis_id or self.id}>"

