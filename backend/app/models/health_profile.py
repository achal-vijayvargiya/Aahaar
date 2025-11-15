"""Health Profile model for storing detailed client health information."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class HealthProfile(Base):
    """Health Profile model for comprehensive client health data."""
    
    __tablename__ = "health_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, unique=True)
    
    # Basic Information
    age = Column(Integer)
    weight = Column(Float)  # in kg
    height = Column(Float)  # in cm
    
    # Health and Lifestyle
    goals = Column(Text)  # Health/fitness goals
    activity_level = Column(String)  # sedentary, lightly_active, moderately_active, very_active, extremely_active
    disease = Column(Text)  # Current diseases or health conditions
    allergies = Column(Text)  # Food and other allergies
    supplements = Column(Text)  # Current supplements being taken
    medications = Column(Text)  # Current medications
    diet_type = Column(String)  # veg, non_veg, vegan, eggetarian
    sleep_cycle = Column(String)  # e.g., "11 PM - 7 AM" or description
    
    # Calculated fields (can be computed from weight and height)
    bmi = Column(Float)  # Body Mass Index
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = relationship("Client", backref="health_profile")
    
    def __repr__(self):
        return f"<HealthProfile client_id={self.client_id}>"
    
    def calculate_bmi(self):
        """Calculate BMI from weight (kg) and height (cm)."""
        if self.weight and self.height and self.height > 0:
            height_m = self.height / 100  # Convert cm to meters
            self.bmi = round(self.weight / (height_m ** 2), 2)
        return self.bmi

