"""Appointment model."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Appointment(Base):
    """Appointment model for scheduling client visits."""
    
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    appointment_date = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=30)
    status = Column(String, default="scheduled")  # scheduled, completed, cancelled, no-show
    reason = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = relationship("Client", back_populates="appointments")
    doctor = relationship("User", foreign_keys=[doctor_id])
    
    def __repr__(self):
        return f"<Appointment {self.id} - {self.appointment_date}>"

