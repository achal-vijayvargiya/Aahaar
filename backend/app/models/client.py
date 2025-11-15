"""Client/Patient model."""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Date, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Client(Base):
    """Client/Patient model."""
    
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    date_of_birth = Column(Date)
    gender = Column(String)
    address = Column(Text)
    medical_history = Column(Text)
    notes = Column(Text)
    assigned_doctor_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    assigned_doctor = relationship("User", foreign_keys=[assigned_doctor_id])
    appointments = relationship("Appointment", back_populates="client", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Client {self.first_name} {self.last_name}>"

