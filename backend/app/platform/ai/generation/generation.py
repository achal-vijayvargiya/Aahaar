"""
AI Generation Module.
Meal plan narration and text generation.
"""
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod


class MealPlanNarrator(ABC):
    """
    Meal Plan Narrator Interface.
    
    Responsibility:
    - Generate narrative descriptions of meal plans
    - Create human-readable meal descriptions
    - Generate cooking instructions and preparation notes
    - Create engaging meal plan presentations
    
    Safety Constraints:
    - ONLY generates narratives for FINALIZED structured meal plans
    - Does NOT modify the meal plan or foods
    - Does NOT add foods not in the original plan
    - Does NOT change portions or nutrition values
    - All narratives must accurately reflect the structured plan
    - No hallucination of foods or ingredients
    
    Inputs:
    - Finalized meal plan (structured)
    - Food information from knowledge base
    - Client preferences (for tone/style)
    
    Outputs:
    - Narrative meal descriptions
    - Cooking instructions
    - Preparation notes
    - No plan modifications
    """
    
    @abstractmethod
    def narrate_meal_plan(
        self,
        meal_plan: Dict[str, Any],
        food_kb_data: Dict[str, Any],
        client_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate narrative description of meal plan.
        
        Args:
            meal_plan: Finalized structured meal plan
            food_kb_data: Food information from knowledge base
            client_preferences: Optional client preferences for narration style
            
        Returns:
            Dictionary containing:
            - meal_narratives: Narrative descriptions for each meal
            - cooking_instructions: Cooking/preparation instructions
            - shopping_list_narrative: Shopping list description
            - daily_summary: Daily meal plan summary
            
        Note:
            This method ONLY narrates the finalized plan.
            Does NOT modify foods, portions, or nutrition values.
            All foods must be from the original plan - no hallucination.
        """
        pass
    
    @abstractmethod
    def narrate_meal(
        self,
        meal: Dict[str, Any],
        food_kb_data: Dict[str, Any]
    ) -> str:
        """
        Generate narrative description for a single meal.
        
        Args:
            meal: Structured meal data
            food_kb_data: Food information from knowledge base
            
        Returns:
            Narrative description of the meal
            
        Note:
            Description must accurately reflect the meal structure.
            No addition of foods or ingredients not in the meal.
        """
        pass
    
    @abstractmethod
    def generate_cooking_instructions(
        self,
        meal: Dict[str, Any],
        food_kb_data: Dict[str, Any]
    ) -> str:
        """
        Generate cooking instructions for a meal.
        
        Args:
            meal: Structured meal data
            food_kb_data: Food information from knowledge base
            
        Returns:
            Cooking/preparation instructions
            
        Note:
            Instructions must be based on foods in the meal only.
            No hallucination of preparation methods.
        """
        pass


class TextGenerator(ABC):
    """
    Text Generator Interface.
    
    Responsibility:
    - Generate various text content for the platform
    - Create user-facing messages and descriptions
    - Generate educational content
    
    Safety Constraints:
    - ONLY generates text for FINALIZED structured data
    - Does NOT modify structured outputs
    - Does NOT make medical or nutrition decisions
    - All generated text must be factually accurate
    - No medical advice beyond explaining existing data
    """
    
    @abstractmethod
    def generate_text(
        self,
        content_type: str,
        structured_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate text content.
        
        Args:
            content_type: Type of content to generate
            structured_data: Finalized structured data
            context: Optional context for generation
            
        Returns:
            Generated text content
            
        Note:
            Text generation only - no modifications to structured data.
            All content must be factually accurate to the input data.
        """
        pass


class GenerationService:
    """
    Generation Service.
    
    Coordinates text generation and narration operations.
    Provides unified interface for all generation needs.
    
    Safety Constraints:
    - All generation is for finalized structured outputs only
    - No modifications to plans or constraints
    - No hallucination of foods or ingredients
    """
    
    def __init__(
        self,
        meal_narrator: Optional[MealPlanNarrator] = None,
        text_generator: Optional[TextGenerator] = None
    ):
        """
        Initialize generation service.
        
        Args:
            meal_narrator: Optional meal plan narrator implementation
            text_generator: Optional text generator implementation
        """
        self.meal_narrator = meal_narrator
        self.text_generator = text_generator
    
    def narrate_meal_plan(
        self,
        meal_plan: Dict[str, Any],
        food_kb_data: Dict[str, Any],
        client_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate narrative description of meal plan.
        
        Args:
            meal_plan: Finalized meal plan
            food_kb_data: Food knowledge base data
            client_preferences: Optional client preferences
            
        Returns:
            Narrative meal plan description
            
        Note:
            Delegates to meal narrator. No plan modifications.
        """
        if not self.meal_narrator:
            raise NotImplementedError("Meal narrator not configured")
        return self.meal_narrator.narrate_meal_plan(
            meal_plan, food_kb_data, client_preferences
        )
    
    def generate_text(
        self,
        content_type: str,
        structured_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate text content.
        
        Args:
            content_type: Type of content
            structured_data: Structured data
            context: Optional context
            
        Returns:
            Generated text
            
        Note:
            Delegates to text generator. No data modifications.
        """
        if not self.text_generator:
            raise NotImplementedError("Text generator not configured")
        return self.text_generator.generate_text(
            content_type, structured_data, context
        )

