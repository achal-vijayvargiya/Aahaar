"""
Food Item Model for Ahara Master Food Database
"""
from sqlalchemy import Column, Integer, String, Float, Text, Index
from sqlalchemy.dialects.postgresql import TSVECTOR
from app.database import Base


class FoodItem(Base):
    """
    Model for storing food items from Ahara Master Food Database
    
    Contains nutritional information, Ayurvedic properties, and classifications
    """
    __tablename__ = "food_items"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic Information
    food_name = Column(String(200), index=True, nullable=False)
    category = Column(String(100), index=True, nullable=False)
    serving_size = Column(String(50))
    region = Column(String(100))
    
    # Nutritional Values (per 100g)
    energy_kcal = Column(Float)
    protein_g = Column(Float, index=True)
    fat_g = Column(Float)
    carbs_g = Column(Float)
    
    # Additional Nutrients
    key_micronutrients = Column(Text)
    fiber_g = Column(Float)
    glycemic_index = Column(Integer)
    glycemic_load = Column(Float)
    
    # Ayurvedic Properties
    dosha_impact = Column(String(100), index=True)
    satvik_rajasik_tamasik = Column(String(50), index=True)
    gut_biotic_value = Column(String(50))
    rasa = Column(String(100))  # Taste
    virya = Column(String(50))  # Heating/Cooling
    season = Column(String(50))
    
    # Scoring (for smart retrieval)
    overall_health_score = Column(Integer, default=50)
    nutrient_density_score = Column(Integer, default=50)
    
    # Full-text search vector
    search_vector = Column(TSVECTOR)
    
    # Vector embedding reference (for FAISS)
    embedding_id = Column(String(50), unique=True, index=True)
    
    __table_args__ = (
        Index('idx_food_search', 'search_vector', postgresql_using='gin'),
        Index('idx_category_dosha', 'category', 'dosha_impact'),
        Index('idx_nutrition', 'protein_g', 'carbs_g', 'fat_g'),
    )
    
    def __repr__(self):
        return f"<FoodItem(id={self.id}, name='{self.food_name}', category='{self.category}')>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "food_name": self.food_name,
            "category": self.category,
            "serving_size": self.serving_size,
            "region": self.region,
            "energy_kcal": self.energy_kcal,
            "protein_g": self.protein_g,
            "fat_g": self.fat_g,
            "carbs_g": self.carbs_g,
            "key_micronutrients": self.key_micronutrients,
            "dosha_impact": self.dosha_impact,
            "satvik_rajasik_tamasik": self.satvik_rajasik_tamasik,
            "gut_biotic_value": self.gut_biotic_value,
        }
    
    def get_macros_summary(self):
        """Get formatted macronutrient summary"""
        return f"P:{self.protein_g}g, F:{self.fat_g}g, C:{self.carbs_g}g, E:{self.energy_kcal}kcal"

