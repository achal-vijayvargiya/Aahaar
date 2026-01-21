"""
Platform Ayurveda Profile Repository.
CRUD operations for platform Ayurveda profiles.
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from app.platform.data.models.platform_ayurveda_profile import PlatformAyurvedaProfile


class PlatformAyurvedaProfileRepository:
    """
    Repository for platform Ayurveda profile operations.
    
    Provides CRUD and basic query methods for platform Ayurveda profiles.
    No business logic - data access only.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, profile_data: dict) -> PlatformAyurvedaProfile:
        """
        Create a new platform Ayurveda profile.
        
        Args:
            profile_data: Dictionary with profile fields
            
        Returns:
            Created PlatformAyurvedaProfile instance
        """
        profile = PlatformAyurvedaProfile(**profile_data)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile
    
    def get_by_id(self, profile_id: UUID) -> Optional[PlatformAyurvedaProfile]:
        """
        Get platform Ayurveda profile by ID.
        
        Args:
            profile_id: Profile UUID
            
        Returns:
            PlatformAyurvedaProfile instance or None
        """
        return self.db.query(PlatformAyurvedaProfile).filter(
            PlatformAyurvedaProfile.id == profile_id
        ).first()
    
    def get_by_assessment_id(self, assessment_id: UUID) -> Optional[PlatformAyurvedaProfile]:
        """
        Get Ayurveda profile for an assessment.
        
        Args:
            assessment_id: Assessment UUID
            
        Returns:
            PlatformAyurvedaProfile instance or None
        """
        return self.db.query(PlatformAyurvedaProfile).filter(
            PlatformAyurvedaProfile.assessment_id == assessment_id
        ).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[PlatformAyurvedaProfile]:
        """
        Get all platform Ayurveda profiles with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of PlatformAyurvedaProfile instances
        """
        return self.db.query(PlatformAyurvedaProfile).offset(skip).limit(limit).all()
    
    def update(self, profile_id: UUID, profile_data: dict) -> Optional[PlatformAyurvedaProfile]:
        """
        Update platform Ayurveda profile.
        
        Args:
            profile_id: Profile UUID
            profile_data: Dictionary with fields to update
            
        Returns:
            Updated PlatformAyurvedaProfile instance or None
        """
        profile = self.get_by_id(profile_id)
        if profile:
            for key, value in profile_data.items():
                setattr(profile, key, value)
            self.db.commit()
            self.db.refresh(profile)
        return profile
    
    def delete(self, profile_id: UUID) -> bool:
        """
        Delete platform Ayurveda profile.
        
        Args:
            profile_id: Profile UUID
            
        Returns:
            True if deleted, False if not found
        """
        profile = self.get_by_id(profile_id)
        if profile:
            self.db.delete(profile)
            self.db.commit()
            return True
        return False

