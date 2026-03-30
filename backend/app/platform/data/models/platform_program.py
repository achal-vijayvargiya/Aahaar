"""
Platform Program ORM model.
Tracks multi-week diet programs and links weekly plans.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class PlatformProgram(Base):
    """
    Platform program model.

    Tracks a multi-week diet program (e.g. 12-week weight loss).
    Links to assessment and weekly diet plans via program_id + week_index.
    """
    __tablename__ = "platform_programs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("platform_clients.id"), nullable=False)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("platform_assessments.id"), nullable=False)
    duration_weeks = Column(Integer, nullable=False)  # e.g. 12
    current_week = Column(Integer, nullable=False, default=1)  # 1-based week index
    goal = Column(JSONB, nullable=True)  # e.g. {"type": "weight_loss", "target_kg": 5, "timeframe_weeks": 12}
    status = Column(String, nullable=True)  # active | completed | paused
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("PlatformClient", backref="programs")
    assessment = relationship("PlatformAssessment", backref="programs")

    def __repr__(self):
        return f"<PlatformProgram {self.id}>"
