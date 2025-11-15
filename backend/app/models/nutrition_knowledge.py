"""
Nutrition Knowledge Base Model
"""
from sqlalchemy import Column, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import TSVECTOR
from app.database import Base


class NutritionKnowledge(Base):
    """
    Model for storing holistic nutrition knowledge including:
    - Medical Nutrition Therapy (MNT)
    - Ayurvedic perspectives
    - Lifestyle guidance
    - Healing affirmations
    """
    __tablename__ = "nutrition_knowledge"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Main Classification
    category = Column(String(100), index=True, nullable=False)
    disorder_name = Column(String(200), index=True, nullable=False)
    
    # Clinical Information
    definition_etiology = Column(Text)
    clinical_goals = Column(Text)
    
    # Medical Nutrition Therapy (MNT)
    mnt_macronutrients = Column(Text)
    mnt_micronutrients = Column(Text)
    mnt_fluids_electrolytes = Column(Text)
    mnt_special_notes = Column(Text)
    
    # Ayurvedic & Holistic Approach
    ayurvedic_view = Column(Text)
    dosha_dominance = Column(String(100), index=True)
    lifestyle_yogic_guidance = Column(Text)
    healing_affirmation = Column(Text)
    
    # Full-text search vector
    search_vector = Column(TSVECTOR)
    
    # Vector embedding reference (for ChromaDB)
    embedding_id = Column(String(50), unique=True, index=True)
    
    __table_args__ = (
        Index('idx_nutrition_search', 'search_vector', postgresql_using='gin'),
        Index('idx_category_disorder', 'category', 'disorder_name'),
    )
    
    def __repr__(self):
        return f"<NutritionKnowledge(id={self.id}, disorder='{self.disorder_name}', category='{self.category}')>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "category": self.category,
            "disorder_name": self.disorder_name,
            "definition_etiology": self.definition_etiology,
            "clinical_goals": self.clinical_goals,
            "mnt_macronutrients": self.mnt_macronutrients,
            "mnt_micronutrients": self.mnt_micronutrients,
            "mnt_fluids_electrolytes": self.mnt_fluids_electrolytes,
            "mnt_special_notes": self.mnt_special_notes,
            "ayurvedic_view": self.ayurvedic_view,
            "dosha_dominance": self.dosha_dominance,
            "lifestyle_yogic_guidance": self.lifestyle_yogic_guidance,
            "healing_affirmation": self.healing_affirmation
        }

