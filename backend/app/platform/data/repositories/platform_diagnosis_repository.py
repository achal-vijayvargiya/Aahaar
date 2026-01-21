"""
Platform Diagnosis Repository.
CRUD operations for platform diagnoses.
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from app.platform.data.models.platform_diagnosis import PlatformDiagnosis


class PlatformDiagnosisRepository:
    """
    Repository for platform diagnosis operations.
    
    Provides CRUD and basic query methods for platform diagnoses.
    No business logic - data access only.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, diagnosis_data: dict) -> PlatformDiagnosis:
        """
        Create a new platform diagnosis.
        
        Args:
            diagnosis_data: Dictionary with diagnosis fields
            
        Returns:
            Created PlatformDiagnosis instance
        """
        diagnosis = PlatformDiagnosis(**diagnosis_data)
        self.db.add(diagnosis)
        self.db.commit()
        self.db.refresh(diagnosis)
        return diagnosis
    
    def get_by_id(self, diagnosis_id: UUID) -> Optional[PlatformDiagnosis]:
        """
        Get platform diagnosis by ID.
        
        Args:
            diagnosis_id: Diagnosis UUID
            
        Returns:
            PlatformDiagnosis instance or None
        """
        return self.db.query(PlatformDiagnosis).filter(
            PlatformDiagnosis.id == diagnosis_id
        ).first()
    
    def get_by_assessment_id(self, assessment_id: UUID) -> List[PlatformDiagnosis]:
        """
        Get all diagnoses for an assessment.
        
        Args:
            assessment_id: Assessment UUID
            
        Returns:
            List of PlatformDiagnosis instances
        """
        return self.db.query(PlatformDiagnosis).filter(
            PlatformDiagnosis.assessment_id == assessment_id
        ).all()
    
    def get_by_type(self, diagnosis_type: str) -> List[PlatformDiagnosis]:
        """
        Get diagnoses by type.
        
        Args:
            diagnosis_type: Diagnosis type (medical | nutrition)
            
        Returns:
            List of PlatformDiagnosis instances
        """
        return self.db.query(PlatformDiagnosis).filter(
            PlatformDiagnosis.diagnosis_type == diagnosis_type
        ).all()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[PlatformDiagnosis]:
        """
        Get all platform diagnoses with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of PlatformDiagnosis instances
        """
        return self.db.query(PlatformDiagnosis).offset(skip).limit(limit).all()
    
    def update(self, diagnosis_id: UUID, diagnosis_data: dict) -> Optional[PlatformDiagnosis]:
        """
        Update platform diagnosis.
        
        Args:
            diagnosis_id: Diagnosis UUID
            diagnosis_data: Dictionary with fields to update
            
        Returns:
            Updated PlatformDiagnosis instance or None
        """
        diagnosis = self.get_by_id(diagnosis_id)
        if diagnosis:
            for key, value in diagnosis_data.items():
                setattr(diagnosis, key, value)
            self.db.commit()
            self.db.refresh(diagnosis)
        return diagnosis
    
    def delete(self, diagnosis_id: UUID) -> bool:
        """
        Delete platform diagnosis.
        
        Args:
            diagnosis_id: Diagnosis UUID
            
        Returns:
            True if deleted, False if not found
        """
        diagnosis = self.get_by_id(diagnosis_id)
        if diagnosis:
            self.db.delete(diagnosis)
            self.db.commit()
            return True
        return False

