"""
Platform Diagnosis ORM model.
Stores both medical and nutrition diagnoses.
"""
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class PlatformDiagnosis(Base):
    """
    Platform diagnosis model.
    
    Stores both medical and nutrition diagnoses with references to knowledge base.
    """
    
    __tablename__ = "platform_diagnoses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("platform_assessments.id"), nullable=False)
    diagnosis_type = Column(String, nullable=True)  # medical | nutrition
    diagnosis_id = Column(String, nullable=True)  # references KB
    severity_score = Column(Numeric, nullable=True)
    evidence = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    assessment = relationship("PlatformAssessment", backref="diagnoses")
    
    def __repr__(self):
        return f"<PlatformDiagnosis {self.id}>"

