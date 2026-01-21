"""
Platform Ayurveda Profile ORM model.
Stores Ayurveda advisory information.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class PlatformAyurvedaProfile(Base):
    """
    Platform Ayurveda profile model.
    
    Stores Ayurveda dosha assessment and lifestyle guidelines (advisory only).
    """
    
    __tablename__ = "platform_ayurveda_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("platform_assessments.id"), nullable=False)
    dosha_primary = Column(String, nullable=True)
    dosha_secondary = Column(String, nullable=True)
    vikriti_notes = Column(JSONB, nullable=True)
    lifestyle_guidelines = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    assessment = relationship("PlatformAssessment", backref="ayurveda_profiles")
    
    def __repr__(self):
        return f"<PlatformAyurvedaProfile {self.id}>"

