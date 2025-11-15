"""Appointment schemas for request/response validation."""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AppointmentBase(BaseModel):
    """Base appointment schema."""
    client_id: int
    doctor_id: int
    appointment_date: datetime
    duration_minutes: int = 30
    status: str = "scheduled"
    reason: Optional[str] = None
    notes: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    """Schema for creating an appointment."""
    pass


class AppointmentUpdate(BaseModel):
    """Schema for updating an appointment."""
    appointment_date: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None


class Appointment(AppointmentBase):
    """Schema for appointment response."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

