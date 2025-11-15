"""
Diet Plan schemas for request/response validation.
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# ===========================
# Diet Plan Meal Schemas
# ===========================

class DietPlanMealBase(BaseModel):
    """Base schema for diet plan meal."""
    day_number: int = Field(..., ge=1, le=7, description="Day number (1-7)")
    meal_time: str = Field(..., description="Time of meal (e.g., '6:30 AM')")
    meal_type: str = Field(..., description="Type of meal (e.g., 'Breakfast', 'Lunch')")
    food_dish: str = Field(..., description="Name of food/dish")
    food_item_ids: Optional[str] = Field(None, description="Comma-separated food item IDs")
    healing_purpose: Optional[str] = Field(None, description="Healing purpose of this meal")
    portion: Optional[str] = Field(None, description="Portion size")
    dosha_notes: Optional[str] = Field(None, description="Dosha-related notes")
    notes: Optional[str] = Field(None, description="Additional notes")
    calories: Optional[float] = Field(None, ge=0)
    protein_g: Optional[float] = Field(None, ge=0)
    carbs_g: Optional[float] = Field(None, ge=0)
    fat_g: Optional[float] = Field(None, ge=0)
    order_in_day: Optional[int] = Field(0, description="Order within the day")


class DietPlanMealCreate(DietPlanMealBase):
    """Schema for creating a diet plan meal."""
    pass


class DietPlanMealUpdate(BaseModel):
    """Schema for updating a diet plan meal."""
    meal_time: Optional[str] = None
    meal_type: Optional[str] = None
    food_dish: Optional[str] = None
    food_item_ids: Optional[str] = None
    healing_purpose: Optional[str] = None
    portion: Optional[str] = None
    dosha_notes: Optional[str] = None
    notes: Optional[str] = None
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None


class DietPlanMeal(DietPlanMealBase):
    """Schema for diet plan meal response."""
    id: int
    diet_plan_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ===========================
# Diet Plan Schemas
# ===========================

class DietPlanBase(BaseModel):
    """Base schema for diet plan."""
    name: str = Field(..., description="Name of the diet plan")
    description: Optional[str] = Field(None, description="Plan description")
    duration_days: int = Field(7, ge=1, le=30, description="Duration in days")
    start_date: Optional[datetime] = Field(None, description="Start date")
    end_date: Optional[datetime] = Field(None, description="End date")
    health_goals: Optional[str] = Field(None, description="Health goals")
    dosha_type: Optional[str] = Field(None, description="Primary dosha type")
    diet_type: Optional[str] = Field(None, description="Diet type (veg, non_veg, vegan, eggetarian)")
    allergies: Optional[str] = Field(None, description="Allergies to avoid")
    target_calories: Optional[float] = Field(None, ge=0, description="Daily calorie target")
    target_protein_g: Optional[float] = Field(None, ge=0, description="Daily protein target (g)")
    target_carbs_g: Optional[float] = Field(None, ge=0, description="Daily carbs target (g)")
    target_fat_g: Optional[float] = Field(None, ge=0, description="Daily fat target (g)")
    status: Optional[str] = Field("draft", description="Plan status")


class DietPlanCreate(DietPlanBase):
    """Schema for creating a diet plan."""
    client_id: int = Field(..., description="Client ID")
    meals: Optional[List[DietPlanMealCreate]] = Field(None, description="Meals in the plan")


class DietPlanUpdate(BaseModel):
    """Schema for updating a diet plan."""
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = None
    target_calories: Optional[float] = None
    target_protein_g: Optional[float] = None
    target_carbs_g: Optional[float] = None
    target_fat_g: Optional[float] = None


class DietPlan(DietPlanBase):
    """Schema for diet plan response."""
    id: int
    client_id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class DietPlanWithMeals(DietPlan):
    """Schema for diet plan with meals."""
    meals: List[DietPlanMeal] = []
    
    model_config = ConfigDict(from_attributes=True)


class DietPlanWithClient(DietPlanWithMeals):
    """Schema for diet plan with client details."""
    # client: Optional['app.schemas.client.Client'] = None  # Temporarily disabled to avoid circular import
    
    model_config = ConfigDict(from_attributes=True)


# ===========================
# Diet Plan Generation Request
# ===========================

class DietPlanGenerateRequest(BaseModel):
    """Schema for AI-generated diet plan request."""
    client_id: int = Field(..., description="Client ID")
    name: Optional[str] = Field(None, description="Name for the diet plan")
    duration_days: int = Field(7, ge=1, le=30, description="Duration in days")
    start_date: Optional[datetime] = Field(None, description="Start date")
    
    # Optional overrides
    custom_goals: Optional[str] = Field(None, description="Custom goals (overrides health profile)")
    custom_diet_type: Optional[str] = Field(None, description="Custom diet type")
    custom_allergies: Optional[str] = Field(None, description="Custom allergies")
    
    # Preferences
    prefer_satvik: bool = Field(False, description="Prefer Satvik foods")
    include_regional_foods: Optional[str] = Field(None, description="Prefer foods from this region")
    meal_variety: str = Field("moderate", description="Variety level: low, moderate, high")
    
    model_config = ConfigDict(from_attributes=True)


class DietPlanAIStep2Request(BaseModel):
    """Schema for AI diet plan generation step 2 request."""
    client_id: int = Field(..., description="Client ID")
    session_id: Optional[str] = Field(None, description="Session ID from Step 1 (for unified flow)")
    user_feedback: Optional[str] = Field(None, description="User feedback on retrieved foods")
    modifications: Optional[dict] = Field(None, description="Any modifications requested by user")
    duration_days: int = Field(7, ge=1, le=30, description="Duration in days")
    name: Optional[str] = Field(None, description="Name for the diet plan")
    start_date: Optional[datetime] = Field(None, description="Start date for the plan")
    
    model_config = ConfigDict(from_attributes=True)


# ===========================
# Conversational Agent Schemas
# ===========================

class AgentChatRequest(BaseModel):
    """Schema for conversational agent chat request."""
    message: str = Field(..., description="User message to the agent")
    session_id: Optional[str] = Field(None, description="Session ID (if continuing conversation)")
    client_id: Optional[int] = Field(None, description="Client ID (required for new sessions)")
    
    model_config = ConfigDict(from_attributes=True)


class AgentChatResponse(BaseModel):
    """Schema for conversational agent chat response."""
    session_id: str = Field(..., description="Session ID for this conversation")
    client_id: int = Field(..., description="Client ID")
    message: str = Field(..., description="Agent's response message")
    context: Dict[str, Any] = Field(..., description="Current session context")
    intermediate_steps: Optional[List[Dict[str, Any]]] = Field(None, description="Tool calls made by agent")
    
    model_config = ConfigDict(from_attributes=True)


class AgentSessionInfo(BaseModel):
    """Schema for agent session information."""
    session_id: str
    client_id: int
    doctor_id: int
    status: str
    stage: str
    created_at: str
    updated_at: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
