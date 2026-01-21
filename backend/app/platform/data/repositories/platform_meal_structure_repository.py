"""
Platform Meal Structure Repository.
CRUD operations for platform meal structures.
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from app.platform.data.models.platform_meal_structure import PlatformMealStructure


class PlatformMealStructureRepository:
    """
    Repository for platform meal structure operations.
    
    Provides CRUD and basic query methods for platform meal structures.
    No business logic - data access only.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, structure_data: dict) -> PlatformMealStructure:
        """
        Create a new platform meal structure.
        
        Args:
            structure_data: Dictionary with structure fields
            
        Returns:
            Created PlatformMealStructure instance
        """
        structure = PlatformMealStructure(**structure_data)
        self.db.add(structure)
        self.db.commit()
        self.db.refresh(structure)
        return structure
    
    def get_by_id(self, structure_id: UUID) -> Optional[PlatformMealStructure]:
        """
        Get platform meal structure by ID.
        
        Args:
            structure_id: Structure UUID
            
        Returns:
            PlatformMealStructure instance or None
        """
        return self.db.query(PlatformMealStructure).filter(
            PlatformMealStructure.id == structure_id
        ).first()
    
    def get_by_assessment_id(self, assessment_id: UUID) -> Optional[PlatformMealStructure]:
        """
        Get meal structure for an assessment.
        
        Args:
            assessment_id: Assessment UUID
            
        Returns:
            PlatformMealStructure instance or None
        """
        return self.db.query(PlatformMealStructure).filter(
            PlatformMealStructure.assessment_id == assessment_id
        ).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[PlatformMealStructure]:
        """
        Get all platform meal structures with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of PlatformMealStructure instances
        """
        return self.db.query(PlatformMealStructure).offset(skip).limit(limit).all()
    
    def update(self, structure_id: UUID, structure_data: dict) -> Optional[PlatformMealStructure]:
        """
        Update platform meal structure.
        
        Args:
            structure_id: Structure UUID
            structure_data: Dictionary with fields to update
            
        Returns:
            Updated PlatformMealStructure instance or None
        """
        structure = self.get_by_id(structure_id)
        if structure:
            for key, value in structure_data.items():
                setattr(structure, key, value)
            self.db.commit()
            self.db.refresh(structure)
        return structure
    
    def update_by_assessment_id(self, assessment_id: UUID, structure_data: dict) -> Optional[PlatformMealStructure]:
        """
        Update platform meal structure by assessment ID.
        
        Args:
            assessment_id: Assessment UUID
            structure_data: Dictionary with fields to update
            
        Returns:
            Updated PlatformMealStructure instance or None
        """
        structure = self.get_by_assessment_id(assessment_id)
        if structure:
            for key, value in structure_data.items():
                setattr(structure, key, value)
            self.db.commit()
            self.db.refresh(structure)
        return structure
    
    def delete(self, structure_id: UUID) -> bool:
        """
        Delete platform meal structure.
        
        Args:
            structure_id: Structure UUID
            
        Returns:
            True if deleted, False if not found
        """
        structure = self.get_by_id(structure_id)
        if structure:
            self.db.delete(structure)
            self.db.commit()
            return True
        return False

