"""
Food Dosha Effect Model

Stores the relationship between foods and their effects on doshas.
Replaces text-based "Vata ↓, Kapha ↑" with structured data.
"""
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship as orm_relationship
from app.database import Base


class FoodDoshaEffect(Base):
    """
    Model for storing how foods affect different doshas.
    
    Example:
    - Moong Dal: Vata ↓ (intensity: 3), Pitta ↓ (intensity: 2), Kapha ↓ (intensity: 4)
    - Paneer: Vata ↓ (intensity: 4), Pitta ↑ (intensity: 2), Kapha ↑ (intensity: 5)
    """
    __tablename__ = "food_dosha_effects"
    
    id = Column(Integer, primary_key=True, index=True)
    food_id = Column(Integer, ForeignKey("food_items.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Dosha information
    dosha_type = Column(String(20), nullable=False)  # Vata, Pitta, Kapha
    effect = Column(String(20), nullable=False)      # increase, decrease, neutral
    intensity = Column(Integer, default=1)           # 1-5 scale (how strong the effect)
    
    # Optional notes
    notes = Column(String(500))
    
    # Relationship
    food_item = orm_relationship("FoodItem", backref="dosha_effects")
    
    __table_args__ = (
        UniqueConstraint('food_id', 'dosha_type', name='unique_food_dosha'),
    )
    
    def __repr__(self):
        arrow = "↑" if self.effect == "increase" else "↓" if self.effect == "decrease" else "="
        return f"<FoodDoshaEffect({self.dosha_type} {arrow} intensity:{self.intensity})>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "food_id": self.food_id,
            "dosha_type": self.dosha_type,
            "effect": self.effect,
            "intensity": self.intensity,
            "notes": self.notes
        }
    
    @staticmethod
    def parse_dosha_impact_text(text: str) -> list:
        """
        Parse old format "Vata ↓, Pitta =, Kapha ↓" into structured data
        
        Returns: [
            {"dosha_type": "Vata", "effect": "decrease", "intensity": 3},
            {"dosha_type": "Pitta", "effect": "neutral", "intensity": 1},
            {"dosha_type": "Kapha", "effect": "decrease", "intensity": 3}
        ]
        """
        if not text:
            return []
        
        results = []
        parts = [p.strip() for p in text.split(",")]
        
        for part in parts:
            if "↓" in part:
                dosha = part.split("↓")[0].strip()
                results.append({"dosha_type": dosha, "effect": "decrease", "intensity": 3})
            elif "↑" in part:
                dosha = part.split("↑")[0].strip()
                results.append({"dosha_type": dosha, "effect": "increase", "intensity": 3})
            elif "=" in part:
                dosha = part.split("=")[0].strip()
                results.append({"dosha_type": dosha, "effect": "neutral", "intensity": 1})
        
        return results

