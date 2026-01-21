"""
Platform Monitoring Record ORM model.
Stores monitoring and feedback data.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class PlatformMonitoringRecord(Base):
    """
    Platform monitoring record model.
    
    Stores monitoring records for weight, labs, adherence, and symptoms.
    """
    
    __tablename__ = "platform_monitoring_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("platform_clients.id"), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("platform_diet_plans.id"), nullable=True)
    metric_type = Column(String, nullable=True)  # weight | lab | adherence | symptom
    metric_value = Column(JSONB, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    client = relationship("PlatformClient", backref="monitoring_records")
    plan = relationship("PlatformDietPlan", backref="monitoring_records")
    
    def __repr__(self):
        return f"<PlatformMonitoringRecord {self.id}>"

