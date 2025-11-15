"""Gut Health Quiz model for assessing digestive health."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class GutHealthQuiz(Base):
    """Gut Health Quiz model to store user responses and calculated gut health state."""
    
    __tablename__ = "gut_health_quizzes"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    
    # Quiz Responses (GQ1-GQ10)
    # Each answer is stored as 'A' (Balanced), 'B' (Weak), or 'C' (Overactive)
    gq1_appetite = Column(String(1), nullable=False)           # How regular is your appetite
    gq2_digestion = Column(String(1), nullable=False)          # After meals, how does digestion feel
    gq3_bowel = Column(String(1), nullable=False)              # How often do you have bowel movements
    gq4_post_meal = Column(String(1), nullable=False)          # How do you feel 1 hour after eating
    gq5_food_reaction = Column(String(1), nullable=False)      # Reaction to new or heavy foods
    gq6_tongue_breath = Column(String(1), nullable=False)      # Coating on tongue or bad breath
    gq7_sleep = Column(String(1), nullable=False)              # How do you sleep at night
    gq8_eating_habit = Column(String(1), nullable=False)       # How do you usually eat meals
    gq9_bloating = Column(String(1), nullable=False)           # When do you feel most bloated
    gq10_immunity = Column(String(1), nullable=False)          # How strong is your immunity
    
    # Calculated Results
    balanced_score = Column(Integer, nullable=False)    # Count of 'A' answers
    weak_score = Column(Integer, nullable=False)        # Count of 'B' answers
    overactive_score = Column(Integer, nullable=False)  # Count of 'C' answers
    
    # Dominant gut health state
    # Examples: "Balanced", "Weak", "Overactive", "Balanced-Weak", "Weak-Overactive", etc.
    gut_health_state = Column(String(50), nullable=False)
    
    # Optional notes from practitioner
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = relationship("Client", backref="gut_health_quizzes")
    
    def __repr__(self):
        return f"<GutHealthQuiz client_id={self.client_id} state={self.gut_health_state}>"
    
    def calculate_gut_health(self):
        """Calculate gut health scores and determine dominant state."""
        answers = [
            self.gq1_appetite,
            self.gq2_digestion,
            self.gq3_bowel,
            self.gq4_post_meal,
            self.gq5_food_reaction,
            self.gq6_tongue_breath,
            self.gq7_sleep,
            self.gq8_eating_habit,
            self.gq9_bloating,
            self.gq10_immunity
        ]
        
        # Count each state
        self.balanced_score = sum(1 for ans in answers if ans == 'A')
        self.weak_score = sum(1 for ans in answers if ans == 'B')
        self.overactive_score = sum(1 for ans in answers if ans == 'C')
        
        # Determine dominant gut health state
        scores = {
            'Balanced': self.balanced_score,
            'Weak': self.weak_score,
            'Overactive': self.overactive_score
        }
        
        max_score = max(scores.values())
        dominant = [state for state, score in scores.items() if score == max_score]
        
        # Check for mixed states (scores within 2 points)
        score_diff = max(scores.values()) - min(scores.values())
        
        if score_diff <= 2:
            # Mixed state - all scores relatively close
            self.gut_health_state = "Mixed"
        elif len(dominant) > 1:
            # Two states tied for highest - dual state
            self.gut_health_state = "-".join(sorted(dominant))
        else:
            # Single dominant state
            self.gut_health_state = dominant[0]
        
        return self.gut_health_state
    
    def get_percentage(self):
        """Get percentage distribution of each gut health state."""
        total = self.balanced_score + self.weak_score + self.overactive_score
        if total == 0:
            return {"Balanced": 0, "Weak": 0, "Overactive": 0}
        
        return {
            "Balanced": round((self.balanced_score / total) * 100, 1),
            "Weak": round((self.weak_score / total) * 100, 1),
            "Overactive": round((self.overactive_score / total) * 100, 1)
        }
    
    def get_quiz_responses(self):
        """Get all quiz responses as a dictionary."""
        return {
            "gq1_appetite": self.gq1_appetite,
            "gq2_digestion": self.gq2_digestion,
            "gq3_bowel": self.gq3_bowel,
            "gq4_post_meal": self.gq4_post_meal,
            "gq5_food_reaction": self.gq5_food_reaction,
            "gq6_tongue_breath": self.gq6_tongue_breath,
            "gq7_sleep": self.gq7_sleep,
            "gq8_eating_habit": self.gq8_eating_habit,
            "gq9_bloating": self.gq9_bloating,
            "gq10_immunity": self.gq10_immunity
        }
    
    def get_recommendations(self):
        """Get basic recommendations based on gut health state."""
        recommendations = {
            "Balanced": {
                "diet": "Maintain current healthy eating habits. Include variety of whole foods.",
                "lifestyle": "Continue mindful eating practices and regular routine.",
                "focus": "Prevention and maintenance of gut health."
            },
            "Weak": {
                "diet": "Easily digestible foods, warm cooked meals, avoid raw/cold foods.",
                "lifestyle": "Eat at regular times, rest after meals, improve digestive fire.",
                "focus": "Strengthening digestion and improving nutrient absorption."
            },
            "Overactive": {
                "diet": "Cooling foods, avoid spicy/fried/acidic foods, smaller portions.",
                "lifestyle": "Stress management, avoid irregular eating, calm environment.",
                "focus": "Reducing inflammation and calming digestive system."
            }
        }
        
        if self.gut_health_state in recommendations:
            return recommendations[self.gut_health_state]
        else:
            return {
                "diet": "Consult with practitioner for personalized recommendations.",
                "lifestyle": "Focus on regular eating habits and stress management.",
                "focus": "Addressing multiple gut health concerns."
            }

