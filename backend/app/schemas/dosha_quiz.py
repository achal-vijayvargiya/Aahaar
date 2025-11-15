"""Dosha Quiz schemas for request/response validation."""
from __future__ import annotations
from typing import Optional, Dict
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class DoshaQuizBase(BaseModel):
    """Base dosha quiz schema."""
    q1_body_frame: str = Field(..., description="Body Frame & Build: A (Vata), B (Pitta), C (Kapha)")
    q2_skin_type: str = Field(..., description="Skin Type: A (Vata), B (Pitta), C (Kapha)")
    q3_hair_type: str = Field(..., description="Hair Type: A (Vata), B (Pitta), C (Kapha)")
    q4_appetite: str = Field(..., description="Appetite & Digestion: A (Vata), B (Pitta), C (Kapha)")
    q5_sleep: str = Field(..., description="Sleep Pattern: A (Vata), B (Pitta), C (Kapha)")
    q6_personality: str = Field(..., description="Personality & Temperament: A (Vata), B (Pitta), C (Kapha)")
    q7_stress: str = Field(..., description="Response to Stress: A (Vata), B (Pitta), C (Kapha)")
    q8_climate: str = Field(..., description="Climate Preference: A (Vata), B (Pitta), C (Kapha)")
    q9_energy: str = Field(..., description="Energy Levels: A (Vata), B (Pitta), C (Kapha)")
    q10_mind: str = Field(..., description="Mind & Focus: A (Vata), B (Pitta), C (Kapha)")
    notes: Optional[str] = Field(None, description="Optional notes from practitioner")
    
    @field_validator(
        'q1_body_frame', 'q2_skin_type', 'q3_hair_type', 'q4_appetite', 
        'q5_sleep', 'q6_personality', 'q7_stress', 'q8_climate', 
        'q9_energy', 'q10_mind'
    )
    @classmethod
    def validate_answer(cls, v):
        """Validate that answer is A, B, or C."""
        if v is not None:
            v = v.upper()
            if v not in ['A', 'B', 'C']:
                raise ValueError("Answer must be 'A', 'B', or 'C'")
            return v
        return v


class DoshaQuizCreate(DoshaQuizBase):
    """Schema for creating a dosha quiz."""
    client_id: int = Field(..., description="Client ID this quiz belongs to")


class DoshaQuizUpdate(BaseModel):
    """Schema for updating a dosha quiz."""
    q1_body_frame: Optional[str] = None
    q2_skin_type: Optional[str] = None
    q3_hair_type: Optional[str] = None
    q4_appetite: Optional[str] = None
    q5_sleep: Optional[str] = None
    q6_personality: Optional[str] = None
    q7_stress: Optional[str] = None
    q8_climate: Optional[str] = None
    q9_energy: Optional[str] = None
    q10_mind: Optional[str] = None
    notes: Optional[str] = None
    
    @field_validator(
        'q1_body_frame', 'q2_skin_type', 'q3_hair_type', 'q4_appetite', 
        'q5_sleep', 'q6_personality', 'q7_stress', 'q8_climate', 
        'q9_energy', 'q10_mind'
    )
    @classmethod
    def validate_answer(cls, v):
        """Validate that answer is A, B, or C."""
        if v is not None:
            v = v.upper()
            if v not in ['A', 'B', 'C']:
                raise ValueError("Answer must be 'A', 'B', or 'C'")
            return v
        return v


class DoshaQuiz(DoshaQuizBase):
    """Schema for dosha quiz response."""
    id: int
    client_id: int
    vata_score: int = Field(..., description="Number of Vata answers")
    pitta_score: int = Field(..., description="Number of Pitta answers")
    kapha_score: int = Field(..., description="Number of Kapha answers")
    dominant_dosha: str = Field(..., description="Dominant dosha or combination")
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class DoshaQuizWithClient(DoshaQuiz):
    """Schema for dosha quiz response with client details."""
    # client: Optional['app.schemas.client.Client'] = None  # Temporarily disabled to avoid circular import
    
    model_config = ConfigDict(from_attributes=True)


class DoshaQuizResult(BaseModel):
    """Schema for dosha quiz result with analysis."""
    id: int
    client_id: int
    dominant_dosha: str
    vata_score: int
    pitta_score: int
    kapha_score: int
    dosha_percentage: Dict[str, float] = Field(..., description="Percentage distribution of doshas")
    quiz_responses: Dict[str, str] = Field(..., description="All quiz responses")
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class DoshaQuizQuestions(BaseModel):
    """Schema for quiz questions and options."""
    question_id: str
    question: str
    option_a: str
    option_b: str
    option_c: str
    dosha_a: str = "Vata"
    dosha_b: str = "Pitta"
    dosha_c: str = "Kapha"

