"""
Knowledge Base Food Repository.
CRUD operations for KB foods.
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from app.platform.data.models.kb_food import KBFood


class KBFoodRepository:
    """
    Repository for KB food operations.
    
    Provides CRUD and basic query methods for KB foods.
    No business logic - data access only.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, food_data: dict) -> KBFood:
        """
        Create a new KB food.
        
        Args:
            food_data: Dictionary with food fields
            
        Returns:
            Created KBFood instance
        """
        food = KBFood(**food_data)
        self.db.add(food)
        self.db.commit()
        self.db.refresh(food)
        return food
    
    def get_by_id(self, food_id: UUID) -> Optional[KBFood]:
        """
        Get KB food by ID.
        
        Args:
            food_id: Food UUID
            
        Returns:
            KBFood instance or None
        """
        return self.db.query(KBFood).filter(
            KBFood.id == food_id
        ).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[KBFood]:
        """
        Get all KB foods with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of KBFood instances
        """
        return self.db.query(KBFood).offset(skip).limit(limit).all()
    
    def update(self, food_id: UUID, food_data: dict) -> Optional[KBFood]:
        """
        Update KB food.
        
        Args:
            food_id: Food UUID
            food_data: Dictionary with fields to update
            
        Returns:
            Updated KBFood instance or None
        """
        food = self.get_by_id(food_id)
        if food:
            for key, value in food_data.items():
                setattr(food, key, value)
            self.db.commit()
            self.db.refresh(food)
        return food
    
    def delete(self, food_id: UUID) -> bool:
        """
        Delete KB food.
        
        Args:
            food_id: Food UUID
            
        Returns:
            True if deleted, False if not found
        """
        food = self.get_by_id(food_id)
        if food:
            self.db.delete(food)
            self.db.commit()
            return True
        return False

