"""
Platform Intake ORM model.
Stores raw and normalized intake data.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class PlatformIntake(Base):
    """
    Platform intake model.
    
    Stores raw and normalized intake data from various sources.
    """
    
    __tablename__ = "platform_intakes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("platform_clients.id"), nullable=False)
    raw_input = Column(JSONB, nullable=True)
    normalized_input = Column(JSONB, nullable=True)
    source = Column(String, nullable=True)  # manual | upload | ai_extracted
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    client = relationship("PlatformClient", backref="intakes")
    
    def __repr__(self):
        return f"<PlatformIntake {self.id}>"

