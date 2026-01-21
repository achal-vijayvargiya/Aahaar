"""
Platform Decision Log ORM model.
Stores explainability and audit support data.
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.database import Base


class PlatformDecisionLog(Base):
    """
    Platform decision log model.
    
    Stores decision logs for explainability and audit support, tracking rule IDs used.
    """
    
    __tablename__ = "platform_decision_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    entity_type = Column(String, nullable=True)  # diagnosis | mnt | plan
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    rule_ids_used = Column(JSONB, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<PlatformDecisionLog {self.id}>"

