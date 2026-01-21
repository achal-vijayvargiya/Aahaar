"""
Knowledge Base Food ORM model.
Read-only reference table for foods.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.database import Base


class KBFood(Base):
    """
    Knowledge base food model.
    
    Read-only reference table for foods.
    Mirrors KB documents and is never modified at runtime.
    """
    
    __tablename__ = "kb_foods"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    version = Column(String, nullable=True)
    source = Column(String, nullable=True)
    last_reviewed = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<KBFood {self.id}>"

