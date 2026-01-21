"""
AI Explanation Module.
Diet plan explanation and lifestyle coaching text generation.
"""
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod


class PlanExplanationGenerator(ABC):
    """
    Plan Explanation Generator Interface.
    
    Responsibility:
    - Generate human-readable explanations for diet plans
    - Explain why specific foods were included/excluded
    - Explain how the plan addresses diagnoses and constraints
    - Generate educational content about nutrition choices
    
    Safety Constraints:
    - ONLY generates explanations for FINALIZED structured outputs
    - Does NOT modify the plan or constraints
    - Does NOT make medical recommendations
    - Does NOT override MNT constraints
    - Explanations must reference rule IDs and KB references
    - All explanations must be factually accurate to the plan
    
    Inputs:
    - Finalized diet plan (structured)
    - MNT constraints applied
    - Diagnoses and rule IDs used
    - Client context
    
    Outputs:
    - Plan explanations
    - Food inclusion/exclusion reasoning
    - Educational content
    - No plan modifications
    """
    
    @abstractmethod
    def generate_plan_explanation(
        self,
        meal_plan: Dict[str, Any],
        constraints: Dict[str, Any],
        diagnoses: Dict[str, Any],
        rule_ids_used: List[str]
    ) -> Dict[str, Any]:
        """
        Generate explanation for diet plan.
        
        Args:
            meal_plan: Finalized meal plan (structured)
            constraints: MNT constraints applied
            diagnoses: Medical and nutrition diagnoses
            rule_ids_used: List of rule IDs used in plan generation
            
        Returns:
            Dictionary containing:
            - overall_explanation: General plan explanation
            - meal_explanations: Per-meal explanations
            - food_reasoning: Why specific foods were included/excluded
            - educational_content: Educational information
            
        Note:
            This method ONLY explains finalized plans.
            Does NOT modify the plan or generate new recommendations.
            All explanations must reference rule IDs for traceability.
        """
        pass
    
    @abstractmethod
    def explain_food_choice(
        self,
        food_id: str,
        meal_plan: Dict[str, Any],
        constraints: Dict[str, Any],
        rule_ids_used: List[str]
    ) -> str:
        """
        Explain why a specific food was included in the plan.
        
        Args:
            food_id: Knowledge base food ID
            meal_plan: Finalized meal plan
            constraints: MNT constraints applied
            rule_ids_used: Rule IDs used in decision
            
        Returns:
            Explanation text for food choice
            
        Note:
            Explanation must reference rule IDs and constraints.
            No new recommendations or modifications.
        """
        pass
    
    @abstractmethod
    def explain_exclusion(
        self,
        food_id: str,
        exclusion_reason: str,
        rule_ids_used: List[str]
    ) -> str:
        """
        Explain why a food was excluded from the plan.
        
        Args:
            food_id: Knowledge base food ID
            exclusion_reason: Reason for exclusion (from rule engine)
            rule_ids_used: Rule IDs that led to exclusion
            
        Returns:
            Explanation text for exclusion
            
        Note:
            Explanation must reference rule IDs and medical reasons.
            No medical advice beyond explaining the exclusion.
        """
        pass


class LifestyleCoachGenerator(ABC):
    """
    Lifestyle Coach Generator Interface.
    
    Responsibility:
    - Generate lifestyle coaching text
    - Provide motivational and educational content
    - Generate meal timing and lifestyle practice suggestions
    
    Safety Constraints:
    - ONLY generates text for FINALIZED structured outputs
    - Does NOT modify nutrition targets or constraints
    - Ayurveda suggestions are advisory and modifiable
    - Does NOT override MNT constraints
    - All suggestions must comply with medical constraints
    
    Inputs:
    - Finalized diet plan
    - Ayurveda profile (advisory)
    - Client context
    
    Outputs:
    - Lifestyle coaching text
    - Meal timing suggestions
    - Lifestyle practice recommendations
    - No constraint modifications
    """
    
    @abstractmethod
    def generate_lifestyle_guidance(
        self,
        meal_plan: Dict[str, Any],
        ayurveda_profile: Optional[Dict[str, Any]] = None,
        client_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate lifestyle coaching guidance.
        
        Args:
            meal_plan: Finalized meal plan
            ayurveda_profile: Optional Ayurveda profile (advisory)
            client_context: Optional client context
            
        Returns:
            Dictionary containing:
            - meal_timing_guidance: Meal timing suggestions
            - lifestyle_practices: Lifestyle recommendations
            - motivational_content: Motivational text
            - educational_content: Educational information
            
        Note:
            All guidance is advisory and modifiable.
            Must comply with MNT constraints.
            Ayurveda suggestions are optimization only.
        """
        pass


class ExplanationService:
    """
    Explanation Service.
    
    Coordinates explanation generation for diet plans and lifestyle coaching.
    Provides unified interface for all explanation needs.
    
    Safety Constraints:
    - All explanations are for finalized structured outputs only
    - No plan modifications or constraint overrides
    - All explanations must be traceable to rule IDs
    """
    
    def __init__(
        self,
        plan_explainer: Optional[PlanExplanationGenerator] = None,
        lifestyle_coach: Optional[LifestyleCoachGenerator] = None
    ):
        """
        Initialize explanation service.
        
        Args:
            plan_explainer: Optional plan explanation generator implementation
            lifestyle_coach: Optional lifestyle coach generator implementation
        """
        self.plan_explainer = plan_explainer
        self.lifestyle_coach = lifestyle_coach
    
    def explain_plan(
        self,
        meal_plan: Dict[str, Any],
        constraints: Dict[str, Any],
        diagnoses: Dict[str, Any],
        rule_ids_used: List[str]
    ) -> Dict[str, Any]:
        """
        Generate explanation for diet plan.
        
        Args:
            meal_plan: Finalized meal plan
            constraints: MNT constraints applied
            diagnoses: Diagnoses
            rule_ids_used: Rule IDs used
            
        Returns:
            Plan explanations
            
        Note:
            Delegates to plan explainer. No plan modifications.
        """
        if not self.plan_explainer:
            raise NotImplementedError("Plan explainer not configured")
        return self.plan_explainer.generate_plan_explanation(
            meal_plan, constraints, diagnoses, rule_ids_used
        )
    
    def generate_lifestyle_guidance(
        self,
        meal_plan: Dict[str, Any],
        ayurveda_profile: Optional[Dict[str, Any]] = None,
        client_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate lifestyle coaching guidance.
        
        Args:
            meal_plan: Finalized meal plan
            ayurveda_profile: Optional Ayurveda profile
            client_context: Optional client context
            
        Returns:
            Lifestyle guidance
            
        Note:
            Delegates to lifestyle coach. No constraint modifications.
        """
        if not self.lifestyle_coach:
            raise NotImplementedError("Lifestyle coach not configured")
        return self.lifestyle_coach.generate_lifestyle_guidance(
            meal_plan, ayurveda_profile, client_context
        )

