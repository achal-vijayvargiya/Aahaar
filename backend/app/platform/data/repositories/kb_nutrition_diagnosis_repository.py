"""
Knowledge Base Nutrition Diagnosis Repository.
Enhanced CRUD and query operations for KB nutrition diagnoses.
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.platform.data.models.kb_nutrition_diagnosis import KBNutritionDiagnosis


class KBNutritionDiagnosisRepository:
    """
    Repository for KB nutrition diagnosis operations.
    
    Provides CRUD and enhanced query methods for KB nutrition diagnoses.
    Includes retrieval logic for finding diagnoses from assessment data.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, diagnosis_data: dict) -> KBNutritionDiagnosis:
        """
        Create a new KB nutrition diagnosis.
        
        Args:
            diagnosis_data: Dictionary with diagnosis fields
            
        Returns:
            Created KBNutritionDiagnosis instance
        """
        diagnosis = KBNutritionDiagnosis(**diagnosis_data)
        self.db.add(diagnosis)
        self.db.commit()
        self.db.refresh(diagnosis)
        return diagnosis
    
    def get_by_id(self, diagnosis_id: UUID) -> Optional[KBNutritionDiagnosis]:
        """
        Get KB nutrition diagnosis by UUID.
        
        Args:
            diagnosis_id: Diagnosis UUID
            
        Returns:
            KBNutritionDiagnosis instance or None
        """
        return self.db.query(KBNutritionDiagnosis).filter(
            KBNutritionDiagnosis.id == diagnosis_id
        ).first()
    
    def get_by_diagnosis_id(self, diagnosis_id: str) -> Optional[KBNutritionDiagnosis]:
        """
        Get KB nutrition diagnosis by diagnosis_id (string identifier).
        
        Args:
            diagnosis_id: Diagnosis string identifier (e.g., "excess_carbohydrate_intake")
            
        Returns:
            KBNutritionDiagnosis instance or None
        """
        return self.db.query(KBNutritionDiagnosis).filter(
            KBNutritionDiagnosis.diagnosis_id == diagnosis_id,
            KBNutritionDiagnosis.status == 'active'
        ).first()
    
    def get_all(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[KBNutritionDiagnosis]:
        """
        Get all KB nutrition diagnoses with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            active_only: If True, only return active diagnoses
            
        Returns:
            List of KBNutritionDiagnosis instances
        """
        query = self.db.query(KBNutritionDiagnosis)
        if active_only:
            query = query.filter(KBNutritionDiagnosis.status == 'active')
        return query.offset(skip).limit(limit).all()
    
    def get_by_condition(self, condition_id: str, active_only: bool = True) -> List[KBNutritionDiagnosis]:
        """
        Get nutrition diagnoses triggered by a medical condition.
        
        Args:
            condition_id: Medical condition ID
            active_only: If True, only return active diagnoses
            
        Returns:
            List of KBNutritionDiagnosis instances
        """
        query = self.db.query(KBNutritionDiagnosis).filter(
            KBNutritionDiagnosis.trigger_conditions.contains([condition_id])
        )
        if active_only:
            query = query.filter(KBNutritionDiagnosis.status == 'active')
        return query.all()
    
    def get_by_domain(self, domain: str, active_only: bool = True) -> List[KBNutritionDiagnosis]:
        """
        Get nutrition diagnoses affecting a specific domain.
        
        Args:
            domain: Affected domain (e.g., "macros", "food_selection", "meal_timing")
            active_only: If True, only return active diagnoses
            
        Returns:
            List of KBNutritionDiagnosis instances
        """
        query = self.db.query(KBNutritionDiagnosis).filter(
            KBNutritionDiagnosis.affected_domains.contains([domain])
        )
        if active_only:
            query = query.filter(KBNutritionDiagnosis.status == 'active')
        return query.all()
    
    def find_by_assessment_data(
        self,
        medical_conditions: Optional[List[str]] = None,
        labs: Optional[Dict[str, float]] = None,
        anthropometry: Optional[Dict[str, float]] = None,
        diet_history: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find nutrition diagnoses matching assessment data.
        
        Args:
            medical_conditions: List of medical condition IDs
            labs: Dictionary of lab_name -> lab_value
            anthropometry: Dictionary of anthropometry metrics -> values
            diet_history: Dictionary of diet history data
            
        Returns:
            List of dictionaries with:
            - diagnosis: KBNutritionDiagnosis instance
            - severity: Calculated severity
            - evidence: Supporting evidence
        """
        all_diagnoses = self.get_all(active_only=True)
        matches = []
        
        for diagnosis in all_diagnoses:
            evidence = {}
            matched = False
            
            # Check trigger conditions
            if medical_conditions and diagnosis.trigger_conditions:
                for condition_id in medical_conditions:
                    if condition_id in diagnosis.trigger_conditions:
                        evidence["trigger_condition"] = condition_id
                        matched = True
            
            # Check trigger labs
            if labs and diagnosis.trigger_labs:
                for lab_name, lab_value in labs.items():
                    if not isinstance(lab_value, (int, float)):
                        continue
                    if lab_name in diagnosis.trigger_labs:
                        threshold = diagnosis.trigger_labs[lab_name]
                        if self._check_threshold(lab_value, threshold):
                            evidence["trigger_lab"] = {lab_name: lab_value}
                            matched = True
            
            # Check trigger anthropometry
            if anthropometry and diagnosis.trigger_anthropometry:
                for metric, value in anthropometry.items():
                    if not isinstance(value, (int, float)):
                        continue
                    if metric in diagnosis.trigger_anthropometry:
                        threshold = diagnosis.trigger_anthropometry[metric]
                        if self._check_threshold(value, threshold):
                            evidence["trigger_anthropometry"] = {metric: value}
                            matched = True
            
            # Check trigger diet history
            if diet_history and diagnosis.trigger_diet_history:
                for key, value in diet_history.items():
                    if not isinstance(value, (int, float)):
                        continue
                    if key in diagnosis.trigger_diet_history:
                        threshold = diagnosis.trigger_diet_history[key]
                        if self._check_threshold(value, threshold):
                            evidence["trigger_diet_history"] = {key: value}
                            matched = True
            
            if matched:
                severity = self._calculate_severity(diagnosis, evidence)
                matches.append({
                    "diagnosis": diagnosis,
                    "severity": severity,
                    "evidence": evidence
                })
        
        return matches
    
    def _check_threshold(self, value: float, threshold: Dict[str, Any]) -> bool:
        """
        Check if value matches threshold.
        
        Args:
            value: Value to check
            threshold: Threshold dict with min/max
            
        Returns:
            True if value matches threshold
        """
        min_val = threshold.get("min")
        max_val = threshold.get("max")
        
        if min_val is not None and value < min_val:
            return False
        if max_val is not None and value > max_val:
            return False
        
        return True
    
    def _calculate_severity(self, diagnosis: KBNutritionDiagnosis, evidence: Dict[str, Any]) -> str:
        """
        Calculate severity based on diagnosis logic and evidence.
        
        Args:
            diagnosis: Diagnosis instance
            evidence: Evidence dictionary
            
        Returns:
            Severity string (mild/moderate/severe)
        """
        # Simple severity calculation - can be enhanced based on severity_logic field
        if diagnosis.severity_logic == "distance_from_threshold":
            # Calculate based on how far from threshold
            return "moderate"  # Default, can be enhanced
        elif diagnosis.severity_logic == "absolute_value":
            # Use absolute value ranges
            return "moderate"  # Default, can be enhanced
        
        return "moderate"  # Default
    
    def update(self, diagnosis_id: UUID, diagnosis_data: dict) -> Optional[KBNutritionDiagnosis]:
        """
        Update KB nutrition diagnosis.
        
        Args:
            diagnosis_id: Diagnosis UUID
            diagnosis_data: Dictionary with fields to update
            
        Returns:
            Updated KBNutritionDiagnosis instance or None
        """
        diagnosis = self.get_by_id(diagnosis_id)
        if diagnosis:
            for key, value in diagnosis_data.items():
                setattr(diagnosis, key, value)
            self.db.commit()
            self.db.refresh(diagnosis)
        return diagnosis
    
    def update_by_diagnosis_id(self, diagnosis_id: str, diagnosis_data: dict) -> Optional[KBNutritionDiagnosis]:
        """
        Update KB nutrition diagnosis by diagnosis_id string.
        
        Args:
            diagnosis_id: Diagnosis string identifier
            diagnosis_data: Dictionary with fields to update
            
        Returns:
            Updated KBNutritionDiagnosis instance or None
        """
        diagnosis = self.get_by_diagnosis_id(diagnosis_id)
        if diagnosis:
            for key, value in diagnosis_data.items():
                setattr(diagnosis, key, value)
            self.db.commit()
            self.db.refresh(diagnosis)
        return diagnosis
    
    def delete(self, diagnosis_id: UUID) -> bool:
        """
        Delete KB nutrition diagnosis.
        
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

