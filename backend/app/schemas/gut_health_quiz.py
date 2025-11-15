"""Gut Health Quiz schemas for request/response validation."""
from __future__ import annotations
from typing import Optional, Dict
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class GutHealthQuizBase(BaseModel):
    """Base gut health quiz schema."""
    gq1_appetite: str = Field(..., description="How regular is your appetite: A (Balanced), B (Weak), C (Overactive)")
    gq2_digestion: str = Field(..., description="After meals digestion: A (Balanced), B (Weak), C (Overactive)")
    gq3_bowel: str = Field(..., description="Bowel movement frequency: A (Balanced), B (Weak), C (Overactive)")
    gq4_post_meal: str = Field(..., description="Feel 1 hour after eating: A (Balanced), B (Weak), C (Overactive)")
    gq5_food_reaction: str = Field(..., description="Reaction to new/heavy foods: A (Balanced), B (Weak), C (Overactive)")
    gq6_tongue_breath: str = Field(..., description="Tongue coating/breath: A (Balanced), B (Weak), C (Overactive)")
    gq7_sleep: str = Field(..., description="Sleep quality: A (Balanced), B (Weak), C (Overactive)")
    gq8_eating_habit: str = Field(..., description="How you eat meals: A (Balanced), B (Weak), C (Overactive)")
    gq9_bloating: str = Field(..., description="When you feel bloated: A (Balanced), B (Weak), C (Overactive)")
    gq10_immunity: str = Field(..., description="Immunity strength: A (Balanced), B (Weak), C (Overactive)")
    notes: Optional[str] = Field(None, description="Optional notes from practitioner")
    
    @field_validator(
        'gq1_appetite', 'gq2_digestion', 'gq3_bowel', 'gq4_post_meal',
        'gq5_food_reaction', 'gq6_tongue_breath', 'gq7_sleep', 'gq8_eating_habit',
        'gq9_bloating', 'gq10_immunity'
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


class GutHealthQuizCreate(GutHealthQuizBase):
    """Schema for creating a gut health quiz."""
    client_id: int = Field(..., description="Client ID this quiz belongs to")


class GutHealthQuizUpdate(BaseModel):
    """Schema for updating a gut health quiz."""
    gq1_appetite: Optional[str] = None
    gq2_digestion: Optional[str] = None
    gq3_bowel: Optional[str] = None
    gq4_post_meal: Optional[str] = None
    gq5_food_reaction: Optional[str] = None
    gq6_tongue_breath: Optional[str] = None
    gq7_sleep: Optional[str] = None
    gq8_eating_habit: Optional[str] = None
    gq9_bloating: Optional[str] = None
    gq10_immunity: Optional[str] = None
    notes: Optional[str] = None
    
    @field_validator(
        'gq1_appetite', 'gq2_digestion', 'gq3_bowel', 'gq4_post_meal',
        'gq5_food_reaction', 'gq6_tongue_breath', 'gq7_sleep', 'gq8_eating_habit',
        'gq9_bloating', 'gq10_immunity'
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


class GutHealthQuiz(GutHealthQuizBase):
    """Schema for gut health quiz response."""
    id: int
    client_id: int
    balanced_score: int = Field(..., description="Number of Balanced answers")
    weak_score: int = Field(..., description="Number of Weak answers")
    overactive_score: int = Field(..., description="Number of Overactive answers")
    gut_health_state: str = Field(..., description="Dominant gut health state")
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class GutHealthQuizWithClient(GutHealthQuiz):
    """Schema for gut health quiz response with client details."""
    # client: Optional['app.schemas.client.Client'] = None  # Temporarily disabled to avoid circular import
    
    model_config = ConfigDict(from_attributes=True)


class GutHealthQuizResult(BaseModel):
    """Schema for gut health quiz result with analysis."""
    id: int
    client_id: int
    gut_health_state: str
    balanced_score: int
    weak_score: int
    overactive_score: int
    percentage: Dict[str, float] = Field(..., description="Percentage distribution")
    quiz_responses: Dict[str, str] = Field(..., description="All quiz responses")
    recommendations: Dict[str, str] = Field(..., description="Health recommendations")
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class GutHealthQuizQuestions(BaseModel):
    """Schema for quiz questions and options."""
    question_id: str
    question: str
    option_a: str
    option_b: str
    option_c: str
    state_a: str = "Balanced Gut"
    state_b: str = "Weak Gut"
    state_c: str = "Overactive Gut"

