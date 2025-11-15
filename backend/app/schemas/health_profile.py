"""Health Profile schemas for request/response validation."""
from __future__ import annotations
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class HealthProfileBase(BaseModel):
    """Base health profile schema."""
    age: Optional[int] = Field(None, ge=0, le=150, description="Age in years")
    weight: Optional[float] = Field(None, ge=0, le=500, description="Weight in kg")
    height: Optional[float] = Field(None, ge=0, le=300, description="Height in cm")
    goals: Optional[str] = Field(None, description="Health/fitness goals")
    activity_level: Optional[str] = Field(
        None, 
        description="Activity level: sedentary, lightly_active, moderately_active, very_active, extremely_active"
    )
    disease: Optional[str] = Field(None, description="Current diseases or health conditions")
    allergies: Optional[str] = Field(None, description="Food and other allergies")
    supplements: Optional[str] = Field(None, description="Current supplements")
    medications: Optional[str] = Field(None, description="Current medications")
    diet_type: Optional[str] = Field(
        None,
        description="Diet type: veg, non_veg, vegan, eggetarian"
    )
    sleep_cycle: Optional[str] = Field(None, description="Sleep cycle (e.g., '11 PM - 7 AM')")
    
    @field_validator('activity_level')
    @classmethod
    def validate_activity_level(cls, v):
        """Validate activity level."""
        if v is not None:
            valid_levels = ['sedentary', 'lightly_active', 'moderately_active', 'very_active', 'extremely_active']
            if v.lower() not in valid_levels:
                raise ValueError(f"Activity level must be one of: {', '.join(valid_levels)}")
            return v.lower()
        return v
    
    @field_validator('diet_type')
    @classmethod
    def validate_diet_type(cls, v):
        """Validate diet type."""
        if v is not None:
            valid_types = ['veg', 'non_veg', 'vegan', 'eggetarian']
            if v.lower() not in valid_types:
                raise ValueError(f"Diet type must be one of: {', '.join(valid_types)}")
            return v.lower()
        return v


class HealthProfileCreate(HealthProfileBase):
    """Schema for creating a health profile."""
    client_id: int = Field(..., description="Client ID this profile belongs to")


class HealthProfileUpdate(HealthProfileBase):
    """Schema for updating a health profile."""
    pass


class HealthProfile(HealthProfileBase):
    """Schema for health profile response."""
    id: int
    client_id: int
    bmi: Optional[float] = Field(None, description="Body Mass Index (calculated)")
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class HealthProfileWithClient(HealthProfile):
    """Schema for health profile response with client details."""
    # client: Optional['app.schemas.client.Client'] = None  # Temporarily disabled to avoid circular import
    
    model_config = ConfigDict(from_attributes=True)

