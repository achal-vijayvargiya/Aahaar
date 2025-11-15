"""Appointment management routes."""
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.appointment import Appointment
from app.models.user import User
from app.schemas.appointment import Appointment as AppointmentSchema, AppointmentCreate, AppointmentUpdate
from app.utils.logger import logger
from app.routers.auth import get_current_active_user

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("/", response_model=List[AppointmentSchema])
async def read_appointments(
    skip: int = 0,
    limit: int = 100,
    client_id: int = Query(None, description="Filter by client ID"),
    doctor_id: int = Query(None, description="Filter by doctor ID"),
    status: str = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get list of appointments with optional filters."""
    query = db.query(Appointment)
    
    if client_id:
        query = query.filter(Appointment.client_id == client_id)
    if doctor_id:
        query = query.filter(Appointment.doctor_id == doctor_id)
    if status:
        query = query.filter(Appointment.status == status)
    
    appointments = query.order_by(Appointment.appointment_date.desc()).offset(skip).limit(limit).all()
    logger.info(f"User {current_user.username} retrieved {len(appointments)} appointments")
    return appointments


@router.get("/{appointment_id}", response_model=AppointmentSchema)
async def read_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get appointment by ID."""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


@router.post("/", response_model=AppointmentSchema, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_in: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create new appointment."""
    # Create new appointment
    appointment = Appointment(**appointment_in.model_dump())
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    
    logger.info(f"User {current_user.username} created new appointment: {appointment.id}")
    return appointment


@router.put("/{appointment_id}", response_model=AppointmentSchema)
async def update_appointment(
    appointment_id: int,
    appointment_in: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update appointment."""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Update fields
    update_data = appointment_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(appointment, field, value)
    
    db.commit()
    db.refresh(appointment)
    
    logger.info(f"User {current_user.username} updated appointment: {appointment.id}")
    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete appointment."""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    db.delete(appointment)
    db.commit()
    
    logger.info(f"User {current_user.username} deleted appointment: {appointment.id}")
    return None

