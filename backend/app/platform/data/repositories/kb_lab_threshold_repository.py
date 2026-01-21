"""
Knowledge Base Lab Threshold Repository.
CRUD and query operations for KB lab thresholds.
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_


from app.platform.data.models.kb_lab_threshold import KBLabThreshold


class KBLabThresholdRepository:
    """
    Repository for KB lab threshold operations.
    
    Provides CRUD and query methods for lab value thresholds.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, threshold_data: dict):
        """
        Create a new KB lab threshold.
        
        Args:
            threshold_data: Dictionary with threshold fields
            
        Returns:
            Created KBLabThreshold instance
        """
        threshold = KBLabThreshold(**threshold_data)
        self.db.add(threshold)
        self.db.commit()
        self.db.refresh(threshold)
        return threshold
    
    def get_by_id(self, threshold_id: UUID):
        """
        Get KB lab threshold by UUID.
        
        Args:
            threshold_id: Threshold UUID
            
        Returns:
            KBLabThreshold instance or None
        """
        return self.db.query(KBLabThreshold).filter(
            KBLabThreshold.id == threshold_id
        ).first()
    
    def get_by_lab_name(self, lab_name: str, active_only: bool = True):
        """
        Get KB lab threshold by lab name.
        
        Args:
            lab_name: Lab name (e.g., "HbA1c", "FBS")
            active_only: If True, only return active thresholds
            
        Returns:
            KBLabThreshold instance or None
        """
        if KBLabThreshold is None:
            raise ImportError("KBLabThreshold model not yet created")
        query = self.db.query(KBLabThreshold).filter(
            KBLabThreshold.lab_name == lab_name
        )
        if active_only:
            query = query.filter(KBLabThreshold.status == 'active')
        return query.first()
    
    def get_all(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> List:
        """
        Get all KB lab thresholds with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            active_only: If True, only return active thresholds
            
        Returns:
            List of KBLabThreshold instances
        """
        if KBLabThreshold is None:
            raise ImportError("KBLabThreshold model not yet created")
        query = self.db.query(KBLabThreshold)
        if active_only:
            query = query.filter(KBLabThreshold.status == 'active')
        return query.offset(skip).limit(limit).all()
    
    def find_threshold_range(self, lab_name: str, value: float) -> Optional[Dict[str, Any]]:
        """
        Find which threshold range a lab value falls into.
        
        Args:
            lab_name: Lab name
            value: Lab value
            
        Returns:
            Dictionary with:
            - range_type: "normal", "mild", "moderate", "severe", or None
            - threshold: Threshold information
            - unit: Unit of measurement
        """
        threshold = self.get_by_lab_name(lab_name)
        if not threshold:
            return None
        
        # Check abnormal ranges first (most specific)
        if threshold.abnormal_ranges:
            # Check severe
            if "severe" in threshold.abnormal_ranges:
                severe = threshold.abnormal_ranges["severe"]
                if self._value_in_range(value, severe):
                    return {
                        "range_type": "severe",
                        "threshold": severe,
                        "unit": severe.get("unit")
                    }
            
            # Check moderate
            if "moderate" in threshold.abnormal_ranges:
                moderate = threshold.abnormal_ranges["moderate"]
                if self._value_in_range(value, moderate):
                    return {
                        "range_type": "moderate",
                        "threshold": moderate,
                        "unit": moderate.get("unit")
                    }
            
            # Check mild
            if "mild" in threshold.abnormal_ranges:
                mild = threshold.abnormal_ranges["mild"]
                if self._value_in_range(value, mild):
                    return {
                        "range_type": "mild",
                        "threshold": mild,
                        "unit": mild.get("unit")
                    }
        
        # Check normal range
        if threshold.normal_range:
            if self._value_in_range(value, threshold.normal_range):
                return {
                    "range_type": "normal",
                    "threshold": threshold.normal_range,
                    "unit": threshold.normal_range.get("unit")
                }
        
        return None
    
    def _value_in_range(self, value: float, range_dict: Dict[str, Any]) -> bool:
        """
        Check if value is within a range.
        
        Args:
            value: Value to check
            range_dict: Range dictionary with min/max
            
        Returns:
            True if value is in range
        """
        min_val = range_dict.get("min")
        max_val = range_dict.get("max")
        
        if min_val is not None and value < min_val:
            return False
        if max_val is not None and value > max_val:
            return False
        
        return True
    
    def convert_unit(self, lab_name: str, value: float, from_unit: str, to_unit: str) -> Optional[float]:
        """
        Convert lab value from one unit to another.
        
        Args:
            lab_name: Lab name
            value: Value to convert
            from_unit: Source unit
            to_unit: Target unit
            
        Returns:
            Converted value or None if conversion not available
        """
        threshold = self.get_by_lab_name(lab_name)
        if not threshold or not threshold.conversion_factors:
            return None
        
        factors = threshold.conversion_factors
        if from_unit not in factors or to_unit not in factors:
            return None
        
        # Convert to base unit first, then to target unit
        from_factor = factors[from_unit]
        to_factor = factors[to_unit]
        
        base_value = value / from_factor
        converted_value = base_value * to_factor
        
        return converted_value
    
    def update(self, threshold_id: UUID, threshold_data: dict):
        """
        Update KB lab threshold.
        
        Args:
            threshold_id: Threshold UUID
            threshold_data: Dictionary with fields to update
            
        Returns:
            Updated KBLabThreshold instance or None
        """
        threshold = self.get_by_id(threshold_id)
        if threshold:
            for key, value in threshold_data.items():
                setattr(threshold, key, value)
            self.db.commit()
            self.db.refresh(threshold)
        return threshold
    
    def update_by_lab_name(self, lab_name: str, threshold_data: dict):
        """
        Update KB lab threshold by lab name.
        
        Args:
            lab_name: Lab name
            threshold_data: Dictionary with fields to update
            
        Returns:
            Updated KBLabThreshold instance or None
        """
        threshold = self.get_by_lab_name(lab_name, active_only=False)
        if threshold:
            for key, value in threshold_data.items():
                setattr(threshold, key, value)
            self.db.commit()
            self.db.refresh(threshold)
        return threshold
    
    def delete(self, threshold_id: UUID) -> bool:
        """
        Delete KB lab threshold.
        
        Args:
            threshold_id: Threshold UUID
            
        Returns:
            True if deleted, False if not found
        """
        threshold = self.get_by_id(threshold_id)
        if threshold:
            self.db.delete(threshold)
            self.db.commit()
            return True
        return False

