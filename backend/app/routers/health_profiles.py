"""Health Profile management routes."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.health_profile import HealthProfile
from app.models.client import Client
from app.models.user import User
from app.schemas.health_profile import (
    HealthProfile as HealthProfileSchema,
    HealthProfileCreate,
    HealthProfileUpdate,
    HealthProfileWithClient
)
from app.utils.logger import logger
from app.routers.auth import get_current_active_user

router = APIRouter(prefix="/health-profiles", tags=["Health Profiles"])


@router.get("/", response_model=List[HealthProfileSchema])
async def read_health_profiles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get list of all health profiles."""
    profiles = db.query(HealthProfile).offset(skip).limit(limit).all()
    logger.info(f"User {current_user.username} retrieved {len(profiles)} health profiles")
    return profiles


@router.get("/{profile_id}", response_model=HealthProfileWithClient)
async def read_health_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get health profile by ID."""
    profile = db.query(HealthProfile).filter(HealthProfile.id == profile_id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Health profile not found")
    return profile


@router.get("/client/{client_id}", response_model=HealthProfileWithClient)
async def read_health_profile_by_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get health profile by client ID."""
    profile = db.query(HealthProfile).filter(HealthProfile.client_id == client_id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Health profile not found for this client")
    return profile


@router.post("/", response_model=HealthProfileSchema, status_code=status.HTTP_201_CREATED)
async def create_health_profile(
    profile_in: HealthProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create new health profile for a client."""
    # Check if client exists
    client = db.query(Client).filter(Client.id == profile_in.client_id).first()
    if not client:
        raise HTTPException(
            status_code=404,
            detail=f"Client with id {profile_in.client_id} not found"
        )
    
    # Check if health profile already exists for this client
    existing_profile = db.query(HealthProfile).filter(
        HealthProfile.client_id == profile_in.client_id
    ).first()
    if existing_profile:
        raise HTTPException(
            status_code=400,
            detail="Health profile already exists for this client. Use PUT to update."
        )
    
    # Create new health profile
    profile = HealthProfile(**profile_in.model_dump())
    
    # Calculate BMI if weight and height are provided
    if profile.weight and profile.height:
        profile.calculate_bmi()
    
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    logger.info(f"User {current_user.username} created health profile for client_id: {profile.client_id}")
    return profile


@router.put("/{profile_id}", response_model=HealthProfileSchema)
async def update_health_profile(
    profile_id: int,
    profile_in: HealthProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update health profile."""
    profile = db.query(HealthProfile).filter(HealthProfile.id == profile_id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Health profile not found")
    
    # Update fields
    update_data = profile_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    # Recalculate BMI if weight or height changed
    if 'weight' in update_data or 'height' in update_data:
        profile.calculate_bmi()
    
    db.commit()
    db.refresh(profile)
    
    logger.info(f"User {current_user.username} updated health profile id: {profile.id}")
    return profile


@router.put("/client/{client_id}", response_model=HealthProfileSchema)
async def update_health_profile_by_client(
    client_id: int,
    profile_in: HealthProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update health profile by client ID."""
    profile = db.query(HealthProfile).filter(HealthProfile.client_id == client_id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Health profile not found for this client")
    
    # Update fields
    update_data = profile_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    # Recalculate BMI if weight or height changed
    if 'weight' in update_data or 'height' in update_data:
        profile.calculate_bmi()
    
    db.commit()
    db.refresh(profile)
    
    logger.info(f"User {current_user.username} updated health profile for client_id: {client_id}")
    return profile


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_health_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete health profile."""
    profile = db.query(HealthProfile).filter(HealthProfile.id == profile_id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Health profile not found")
    
    db.delete(profile)
    db.commit()
    
    logger.info(f"User {current_user.username} deleted health profile id: {profile.id}")
    return None


# Helper function for programmatic use
def create_or_update_health_profile(
    client_id: int,
    profile_data: dict,
    db: Session
) -> HealthProfile:
    """
    Create or update a health profile for a client.
    This is a helper function for programmatic use.
    
    Args:
        client_id: The ID of the client
        profile_data: Dictionary containing health profile data
        db: Database session
    
    Returns:
        HealthProfile: The created or updated health profile
    """
    # Check if profile exists
    profile = db.query(HealthProfile).filter(HealthProfile.client_id == client_id).first()
    
    if profile:
        # Update existing profile
        for field, value in profile_data.items():
            if hasattr(profile, field) and value is not None:
                setattr(profile, field, value)
    else:
        # Create new profile
        profile_data['client_id'] = client_id
        profile = HealthProfile(**profile_data)
        db.add(profile)
    
    # Calculate BMI
    if profile.weight and profile.height:
        profile.calculate_bmi()
    
    db.commit()
    db.refresh(profile)
    
    return profile


def get_health_profile_by_client_id(client_id: int, db: Session) -> HealthProfile:
    """
    Get health profile by client ID.
    Helper function for programmatic use.
    
    Args:
        client_id: The ID of the client
        db: Database session
    
    Returns:
        HealthProfile: The health profile or None if not found
    """
    return db.query(HealthProfile).filter(HealthProfile.client_id == client_id).first()

