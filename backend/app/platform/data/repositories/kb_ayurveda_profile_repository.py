"""
Knowledge Base Ayurveda Profile Repository.
CRUD operations for KB Ayurveda profiles.
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from app.platform.data.models.kb_ayurveda_profile import KBAyurvedaProfile


class KBAyurvedaProfileRepository:
    """
    Repository for KB Ayurveda profile operations.
    
    Provides CRUD and basic query methods for KB Ayurveda profiles.
    No business logic - data access only.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, profile_data: dict) -> KBAyurvedaProfile:
        """
        Create a new KB Ayurveda profile.
        
        Args:
            profile_data: Dictionary with profile fields
            
        Returns:
            Created KBAyurvedaProfile instance
        """
        profile = KBAyurvedaProfile(**profile_data)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile
    
    def get_by_id(self, profile_id: UUID) -> Optional[KBAyurvedaProfile]:
        """
        Get KB Ayurveda profile by ID.
        
        Args:
            profile_id: Profile UUID
            
        Returns:
            KBAyurvedaProfile instance or None
        """
        return self.db.query(KBAyurvedaProfile).filter(
            KBAyurvedaProfile.id == profile_id
        ).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[KBAyurvedaProfile]:
        """
        Get all KB Ayurveda profiles with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of KBAyurvedaProfile instances
        """
        return self.db.query(KBAyurvedaProfile).offset(skip).limit(limit).all()
    
    def update(self, profile_id: UUID, profile_data: dict) -> Optional[KBAyurvedaProfile]:
        """
        Update KB Ayurveda profile.
        
        Args:
            profile_id: Profile UUID
            profile_data: Dictionary with fields to update
            
        Returns:
            Updated KBAyurvedaProfile instance or None
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
        Delete KB Ayurveda profile.
        
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

