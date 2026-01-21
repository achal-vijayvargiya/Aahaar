"""
Platform Assessment Repository.
CRUD operations for platform assessments.
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from app.platform.data.models.platform_assessment import PlatformAssessment


class PlatformAssessmentRepository:
    """
    Repository for platform assessment operations.
    
    Provides CRUD and basic query methods for platform assessments.
    No business logic - data access only.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, assessment_data: dict) -> PlatformAssessment:
        """
        Create a new platform assessment.
        
        Args:
            assessment_data: Dictionary with assessment fields
            
        Returns:
            Created PlatformAssessment instance
        """
        assessment = PlatformAssessment(**assessment_data)
        self.db.add(assessment)
        self.db.commit()
        self.db.refresh(assessment)
        return assessment
    
    def get_by_id(self, assessment_id: UUID) -> Optional[PlatformAssessment]:
        """
        Get platform assessment by ID.
        
        Args:
            assessment_id: Assessment UUID
            
        Returns:
            PlatformAssessment instance or None
        """
        return self.db.query(PlatformAssessment).filter(
            PlatformAssessment.id == assessment_id
        ).first()
    
    def get_by_client_id(self, client_id: UUID) -> List[PlatformAssessment]:
        """
        Get all assessments for a client.
        
        Args:
            client_id: Client UUID
            
        Returns:
            List of PlatformAssessment instances
        """
        return self.db.query(PlatformAssessment).filter(
            PlatformAssessment.client_id == client_id
        ).all()
    
    def get_by_status(self, status: str) -> List[PlatformAssessment]:
        """
        Get assessments by status.
        
        Args:
            status: Assessment status (draft | finalized)
            
        Returns:
            List of PlatformAssessment instances
        """
        return self.db.query(PlatformAssessment).filter(
            PlatformAssessment.assessment_status == status
        ).all()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[PlatformAssessment]:
        """
        Get all platform assessments with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of PlatformAssessment instances
        """
        return self.db.query(PlatformAssessment).offset(skip).limit(limit).all()
    
    def update(self, assessment_id: UUID, assessment_data: dict) -> Optional[PlatformAssessment]:
        """
        Update platform assessment.
        
        Args:
            assessment_id: Assessment UUID
            assessment_data: Dictionary with fields to update
            
        Returns:
            Updated PlatformAssessment instance or None
        """
        assessment = self.get_by_id(assessment_id)
        if assessment:
            for key, value in assessment_data.items():
                setattr(assessment, key, value)
            self.db.commit()
            self.db.refresh(assessment)
        return assessment
    
    def delete(self, assessment_id: UUID) -> bool:
        """
        Delete platform assessment.
        
        Args:
            assessment_id: Assessment UUID
            
        Returns:
            True if deleted, False if not found
        """
        assessment = self.get_by_id(assessment_id)
        if assessment:
            self.db.delete(assessment)
            self.db.commit()
            return True
        return False

