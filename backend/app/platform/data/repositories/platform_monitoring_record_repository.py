"""
Platform Monitoring Record Repository.
CRUD operations for platform monitoring records.
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from app.platform.data.models.platform_monitoring_record import PlatformMonitoringRecord


class PlatformMonitoringRecordRepository:
    """
    Repository for platform monitoring record operations.
    
    Provides CRUD and basic query methods for platform monitoring records.
    No business logic - data access only.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, record_data: dict) -> PlatformMonitoringRecord:
        """
        Create a new platform monitoring record.
        
        Args:
            record_data: Dictionary with record fields
            
        Returns:
            Created PlatformMonitoringRecord instance
        """
        record = PlatformMonitoringRecord(**record_data)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
    
    def get_by_id(self, record_id: UUID) -> Optional[PlatformMonitoringRecord]:
        """
        Get platform monitoring record by ID.
        
        Args:
            record_id: Record UUID
            
        Returns:
            PlatformMonitoringRecord instance or None
        """
        return self.db.query(PlatformMonitoringRecord).filter(
            PlatformMonitoringRecord.id == record_id
        ).first()
    
    def get_by_client_id(self, client_id: UUID) -> List[PlatformMonitoringRecord]:
        """
        Get all monitoring records for a client.
        
        Args:
            client_id: Client UUID
            
        Returns:
            List of PlatformMonitoringRecord instances
        """
        return self.db.query(PlatformMonitoringRecord).filter(
            PlatformMonitoringRecord.client_id == client_id
        ).all()
    
    def get_by_plan_id(self, plan_id: UUID) -> List[PlatformMonitoringRecord]:
        """
        Get all monitoring records for a diet plan.
        
        Args:
            plan_id: Diet plan UUID
            
        Returns:
            List of PlatformMonitoringRecord instances
        """
        return self.db.query(PlatformMonitoringRecord).filter(
            PlatformMonitoringRecord.plan_id == plan_id
        ).all()
    
    def get_by_metric_type(self, metric_type: str) -> List[PlatformMonitoringRecord]:
        """
        Get monitoring records by metric type.
        
        Args:
            metric_type: Metric type (weight | lab | adherence | symptom)
            
        Returns:
            List of PlatformMonitoringRecord instances
        """
        return self.db.query(PlatformMonitoringRecord).filter(
            PlatformMonitoringRecord.metric_type == metric_type
        ).all()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[PlatformMonitoringRecord]:
        """
        Get all platform monitoring records with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of PlatformMonitoringRecord instances
        """
        return self.db.query(PlatformMonitoringRecord).offset(skip).limit(limit).all()
    
    def update(self, record_id: UUID, record_data: dict) -> Optional[PlatformMonitoringRecord]:
        """
        Update platform monitoring record.
        
        Args:
            record_id: Record UUID
            record_data: Dictionary with fields to update
            
        Returns:
            Updated PlatformMonitoringRecord instance or None
        """
        record = self.get_by_id(record_id)
        if record:
            for key, value in record_data.items():
                setattr(record, key, value)
            self.db.commit()
            self.db.refresh(record)
        return record
    
    def delete(self, record_id: UUID) -> bool:
        """
        Delete platform monitoring record.
        
        Args:
            record_id: Record UUID
            
        Returns:
            True if deleted, False if not found
        """
        record = self.get_by_id(record_id)
        if record:
            self.db.delete(record)
            self.db.commit()
            return True
        return False

