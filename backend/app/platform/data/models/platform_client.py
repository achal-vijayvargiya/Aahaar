"""
Platform Client ORM model.
Stores client/patient information for the platform.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.database import Base


class PlatformClient(Base):
    """
    Platform client model.
    
    Stores basic client information for the holistic nutrition platform.
    """
    
    __tablename__ = "platform_clients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    external_client_id = Column(String, nullable=True)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    location = Column(String, nullable=True)
    wake_time = Column(String, nullable=True)  # Format: "HH:MM" (24-hour)
    sleep_time = Column(String, nullable=True)  # Format: "HH:MM" (24-hour)
    work_schedule_start = Column(String, nullable=True)  # Format: "HH:MM"
    work_schedule_end = Column(String, nullable=True)  # Format: "HH:MM"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<PlatformClient {self.name}>"

