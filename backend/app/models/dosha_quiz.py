"""Dosha Quiz model for Ayurvedic dosha assessment."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class DoshaQuiz(Base):
    """Dosha Quiz model to store user responses and calculated dosha."""
    
    __tablename__ = "dosha_quizzes"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    
    # Quiz Responses (Q1-Q10)
    # Each answer is stored as 'A' (Vata), 'B' (Pitta), or 'C' (Kapha)
    q1_body_frame = Column(String(1), nullable=False)  # Body Frame & Build
    q2_skin_type = Column(String(1), nullable=False)   # Skin Type
    q3_hair_type = Column(String(1), nullable=False)   # Hair Type
    q4_appetite = Column(String(1), nullable=False)    # Appetite & Digestion
    q5_sleep = Column(String(1), nullable=False)       # Sleep Pattern
    q6_personality = Column(String(1), nullable=False) # Personality & Temperament
    q7_stress = Column(String(1), nullable=False)      # Response to Stress
    q8_climate = Column(String(1), nullable=False)     # Climate Preference
    q9_energy = Column(String(1), nullable=False)      # Energy Levels
    q10_mind = Column(String(1), nullable=False)       # Mind & Focus
    
    # Calculated Results
    vata_score = Column(Integer, nullable=False)   # Count of 'A' answers
    pitta_score = Column(Integer, nullable=False)  # Count of 'B' answers
    kapha_score = Column(Integer, nullable=False)  # Count of 'C' answers
    
    # Dominant dosha(s) - can be single or dual dosha
    # Examples: "Vata", "Pitta", "Kapha", "Vata-Pitta", "Pitta-Kapha", "Vata-Kapha", "Tridosha"
    dominant_dosha = Column(String(50), nullable=False)
    
    # Optional notes from practitioner
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = relationship("Client", backref="dosha_quizzes")
    
    def __repr__(self):
        return f"<DoshaQuiz client_id={self.client_id} dosha={self.dominant_dosha}>"
    
    def calculate_dosha(self):
        """Calculate dosha scores and determine dominant dosha(s)."""
        answers = [
            self.q1_body_frame,
            self.q2_skin_type,
            self.q3_hair_type,
            self.q4_appetite,
            self.q5_sleep,
            self.q6_personality,
            self.q7_stress,
            self.q8_climate,
            self.q9_energy,
            self.q10_mind
        ]
        
        # Count each dosha
        self.vata_score = sum(1 for ans in answers if ans == 'A')
        self.pitta_score = sum(1 for ans in answers if ans == 'B')
        self.kapha_score = sum(1 for ans in answers if ans == 'C')
        
        # Determine dominant dosha(s)
        scores = {
            'Vata': self.vata_score,
            'Pitta': self.pitta_score,
            'Kapha': self.kapha_score
        }
        
        max_score = max(scores.values())
        dominant = [dosha for dosha, score in scores.items() if score == max_score]
        
        # Check for tridosha (all three balanced within 1 point)
        if max(scores.values()) - min(scores.values()) <= 1:
            self.dominant_dosha = "Tridosha"
        elif len(dominant) > 1:
            # Dual dosha - sort alphabetically for consistency
            self.dominant_dosha = "-".join(sorted(dominant))
        else:
            self.dominant_dosha = dominant[0]
        
        return self.dominant_dosha
    
    def get_dosha_percentage(self):
        """Get percentage distribution of each dosha."""
        total = self.vata_score + self.pitta_score + self.kapha_score
        if total == 0:
            return {"Vata": 0, "Pitta": 0, "Kapha": 0}
        
        return {
            "Vata": round((self.vata_score / total) * 100, 1),
            "Pitta": round((self.pitta_score / total) * 100, 1),
            "Kapha": round((self.kapha_score / total) * 100, 1)
        }
    
    def get_quiz_responses(self):
        """Get all quiz responses as a dictionary."""
        return {
            "q1_body_frame": self.q1_body_frame,
            "q2_skin_type": self.q2_skin_type,
            "q3_hair_type": self.q3_hair_type,
            "q4_appetite": self.q4_appetite,
            "q5_sleep": self.q5_sleep,
            "q6_personality": self.q6_personality,
            "q7_stress": self.q7_stress,
            "q8_climate": self.q8_climate,
            "q9_energy": self.q9_energy,
            "q10_mind": self.q10_mind
        }

