"""
Platform Client Repository.
CRUD operations for platform clients.
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from app.platform.data.models.platform_client import PlatformClient
from app.platform.data.models.platform_intake import PlatformIntake
from app.platform.data.models.platform_assessment import PlatformAssessment
from app.platform.data.models.platform_diet_plan import PlatformDietPlan
from app.platform.data.models.platform_monitoring_record import PlatformMonitoringRecord
from app.platform.data.models.platform_diagnosis import PlatformDiagnosis
from app.platform.data.models.platform_mnt_constraint import PlatformMNTConstraint
from app.platform.data.models.platform_nutrition_target import PlatformNutritionTarget
from app.platform.data.models.platform_ayurveda_profile import PlatformAyurvedaProfile
from app.platform.data.models.platform_meal_structure import PlatformMealStructure
from app.platform.data.models.platform_exchange_allocation import PlatformExchangeAllocation


class PlatformClientRepository:
    """
    Repository for platform client operations.
    
    Provides CRUD and basic query methods for platform clients.
    No business logic - data access only.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, client_data: dict) -> PlatformClient:
        """
        Create a new platform client.
        
        Args:
            client_data: Dictionary with client fields
            
        Returns:
            Created PlatformClient instance
        """
        client = PlatformClient(**client_data)
        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)
        return client
    
    def get_by_id(self, client_id: UUID) -> Optional[PlatformClient]:
        """
        Get platform client by ID.
        
        Args:
            client_id: Client UUID
            
        Returns:
            PlatformClient instance or None
        """
        return self.db.query(PlatformClient).filter(PlatformClient.id == client_id).first()
    
    def get_by_external_id(self, external_client_id: str) -> Optional[PlatformClient]:
        """
        Get platform client by external client ID.
        
        Args:
            external_client_id: External client identifier
            
        Returns:
            PlatformClient instance or None
        """
        return self.db.query(PlatformClient).filter(
            PlatformClient.external_client_id == external_client_id
        ).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[PlatformClient]:
        """
        Get all platform clients with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of PlatformClient instances
        """
        return self.db.query(PlatformClient).offset(skip).limit(limit).all()
    
    def update(self, client_id: UUID, client_data: dict) -> Optional[PlatformClient]:
        """
        Update platform client.
        
        Args:
            client_id: Client UUID
            client_data: Dictionary with fields to update
            
        Returns:
            Updated PlatformClient instance or None
        """
        client = self.get_by_id(client_id)
        if client:
            for key, value in client_data.items():
                setattr(client, key, value)
            self.db.commit()
            self.db.refresh(client)
        return client
    
    def delete(self, client_id: UUID) -> bool:
        """
        Delete platform client and all related records.
        
        Deletes in the correct order to respect foreign key constraints:
        1. Monitoring Records (references client_id and plan_id)
        2. Diet Plans (references client_id and assessment_id)
        3. Meal Structures, Exchange Allocations (references assessment_id)
        4. Diagnoses, MNT Constraints, Nutrition Targets, Ayurveda Profiles (references assessment_id)
        5. Assessments (references client_id and intake_id)
        6. Intakes (references client_id)
        7. Client
        
        Args:
            client_id: Client UUID
            
        Returns:
            True if deleted, False if not found
        """
        client = self.get_by_id(client_id)
        if not client:
            return False
        
        # Get all related records
        monitoring_records = self.db.query(PlatformMonitoringRecord).filter(
            PlatformMonitoringRecord.client_id == client_id
        ).all()
        
        diet_plans = self.db.query(PlatformDietPlan).filter(
            PlatformDietPlan.client_id == client_id
        ).all()
        
        assessments = self.db.query(PlatformAssessment).filter(
            PlatformAssessment.client_id == client_id
        ).all()
        
        intakes = self.db.query(PlatformIntake).filter(
            PlatformIntake.client_id == client_id
        ).all()
        
        # Get assessment IDs for deleting related records
        assessment_ids = [assessment.id for assessment in assessments]
        
        # Delete monitoring records
        for record in monitoring_records:
            self.db.delete(record)
        
        # Delete diet plans
        for plan in diet_plans:
            self.db.delete(plan)
        
        # Delete assessment-related records
        if assessment_ids:
            # Delete meal structures (references assessment_id)
            meal_structures = self.db.query(PlatformMealStructure).filter(
                PlatformMealStructure.assessment_id.in_(assessment_ids)
            ).all()
            for meal_structure in meal_structures:
                self.db.delete(meal_structure)
            
            # Delete exchange allocations (references assessment_id)
            exchange_allocations = self.db.query(PlatformExchangeAllocation).filter(
                PlatformExchangeAllocation.assessment_id.in_(assessment_ids)
            ).all()
            for exchange_allocation in exchange_allocations:
                self.db.delete(exchange_allocation)
            
            # Delete diagnoses
            diagnoses = self.db.query(PlatformDiagnosis).filter(
                PlatformDiagnosis.assessment_id.in_(assessment_ids)
            ).all()
            for diagnosis in diagnoses:
                self.db.delete(diagnosis)
            
            # Delete MNT constraints
            mnt_constraints = self.db.query(PlatformMNTConstraint).filter(
                PlatformMNTConstraint.assessment_id.in_(assessment_ids)
            ).all()
            for constraint in mnt_constraints:
                self.db.delete(constraint)
            
            # Delete nutrition targets
            nutrition_targets = self.db.query(PlatformNutritionTarget).filter(
                PlatformNutritionTarget.assessment_id.in_(assessment_ids)
            ).all()
            for target in nutrition_targets:
                self.db.delete(target)
            
            # Delete ayurveda profiles
            ayurveda_profiles = self.db.query(PlatformAyurvedaProfile).filter(
                PlatformAyurvedaProfile.assessment_id.in_(assessment_ids)
            ).all()
            for profile in ayurveda_profiles:
                self.db.delete(profile)
        
        # Delete assessments
        for assessment in assessments:
            self.db.delete(assessment)
        
        # Delete intakes
        for intake in intakes:
            self.db.delete(intake)
        
        # Finally, delete the client
        self.db.delete(client)
        self.db.commit()
        return True

