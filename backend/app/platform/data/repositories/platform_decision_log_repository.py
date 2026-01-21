"""
Platform Decision Log Repository.
CRUD operations for platform decision logs.
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from app.platform.data.models.platform_decision_log import PlatformDecisionLog


class PlatformDecisionLogRepository:
    """
    Repository for platform decision log operations.
    
    Provides CRUD and basic query methods for platform decision logs.
    No business logic - data access only.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, log_data: dict) -> PlatformDecisionLog:
        """
        Create a new platform decision log.
        
        Args:
            log_data: Dictionary with log fields
            
        Returns:
            Created PlatformDecisionLog instance
        """
        log = PlatformDecisionLog(**log_data)
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log
    
    def get_by_id(self, log_id: UUID) -> Optional[PlatformDecisionLog]:
        """
        Get platform decision log by ID.
        
        Args:
            log_id: Log UUID
            
        Returns:
            PlatformDecisionLog instance or None
        """
        return self.db.query(PlatformDecisionLog).filter(
            PlatformDecisionLog.id == log_id
        ).first()
    
    def get_by_entity(self, entity_type: str, entity_id: UUID) -> List[PlatformDecisionLog]:
        """
        Get decision logs for an entity.
        
        Args:
            entity_type: Entity type (diagnosis | mnt | plan)
            entity_id: Entity UUID
            
        Returns:
            List of PlatformDecisionLog instances
        """
        return self.db.query(PlatformDecisionLog).filter(
            PlatformDecisionLog.entity_type == entity_type,
            PlatformDecisionLog.entity_id == entity_id
        ).all()
    
    def get_by_entity_type(self, entity_type: str) -> List[PlatformDecisionLog]:
        """
        Get decision logs by entity type.
        
        Args:
            entity_type: Entity type (diagnosis | mnt | plan)
            
        Returns:
            List of PlatformDecisionLog instances
        """
        return self.db.query(PlatformDecisionLog).filter(
            PlatformDecisionLog.entity_type == entity_type
        ).all()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[PlatformDecisionLog]:
        """
        Get all platform decision logs with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of PlatformDecisionLog instances
        """
        return self.db.query(PlatformDecisionLog).offset(skip).limit(limit).all()
    
    def update(self, log_id: UUID, log_data: dict) -> Optional[PlatformDecisionLog]:
        """
        Update platform decision log.
        
        Args:
            log_id: Log UUID
            log_data: Dictionary with fields to update
            
        Returns:
            Updated PlatformDecisionLog instance or None
        """
        log = self.get_by_id(log_id)
        if log:
            for key, value in log_data.items():
                setattr(log, key, value)
            self.db.commit()
            self.db.refresh(log)
        return log
    
    def delete(self, log_id: UUID) -> bool:
        """
        Delete platform decision log.
        
        Args:
            log_id: Log UUID
            
        Returns:
            True if deleted, False if not found
        """
        log = self.get_by_id(log_id)
        if log:
            self.db.delete(log)
            self.db.commit()
            return True
        return False

