"""
Knowledge Base Food Exchange Profile ORM model.
Exchange system mapping and portion logic.
"""
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class KBFoodExchangeProfile(Base):
    """
    Knowledge base food exchange profile model.
    
    Stores exchange category mapping and portion logic.
    Links foods to the Indian Exchange Lists (IET) system.
    """
    
    __tablename__ = "kb_food_exchange_profile"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    food_id = Column(String(100), ForeignKey("kb_food_master.food_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    exchange_category = Column(String(100), nullable=False, index=True)
    serving_size_per_exchange_g = Column(Numeric(10, 2), nullable=True)
    exchanges_per_common_serving = Column(Numeric(10, 2), nullable=True)
    notes = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship (food_id references kb_food_master.food_id)
    food = relationship("KBFoodMaster", back_populates="exchange_profile", primaryjoin="KBFoodExchangeProfile.food_id == KBFoodMaster.food_id")
    
    __table_args__ = (
        Index('idx_food_exchange_food_id', 'food_id', unique=True),
        Index('idx_food_exchange_category', 'exchange_category'),
    )
    
    def __repr__(self):
        return f"<KBFoodExchangeProfile {self.food_id}>"

