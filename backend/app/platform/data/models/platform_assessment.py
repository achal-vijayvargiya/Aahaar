"""
Platform Assessment ORM model.
Stores assessment snapshots and status.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class PlatformAssessment(Base):
    """
    Platform assessment model.
    
    Stores assessment snapshots and status for the NCP process.
    """
    
    __tablename__ = "platform_assessments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("platform_clients.id"), nullable=False)
    intake_id = Column(UUID(as_uuid=True), ForeignKey("platform_intakes.id"), nullable=True)
    assessment_snapshot = Column(JSONB, nullable=True)
    assessment_status = Column(String, nullable=True)  # draft | finalized
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    client = relationship("PlatformClient", backref="assessments")
    intake = relationship("PlatformIntake", backref="assessments")
    
    def __repr__(self):
        return f"<PlatformAssessment {self.id}>"

