"""
Ayurveda Engine.
Comprehensive Ayurvedic assessment: Prakriti, Vikriti, Agni, and Ama evaluation.
Deterministic, rule-based assessment engine.
"""
from typing import Dict, List, Any, Optional
from uuid import UUID

from app.platform.core.context import TargetContext, AyurvedaContext, MNTContext
from app.platform.engines.ayurveda_engine.kb_ayurveda_profiles import get_profile
from app.platform.engines.ayurveda_engine.assessment_scorer import (
    calculate_prakriti_scores,
    calculate_vikriti_scores,
    determine_agni_type,
    determine_ama_level,
    determine_dosha_primary_secondary,
)
from app.platform.engines.ayurveda_engine.constraints_generator import (
    generate_ayurvedic_constraints,
)


class AyurvedaEngine:
    """
    Ayurveda Engine.
    
    Responsibility:
    - Assess dosha (primary and secondary)
    - Generate lifestyle optimization guidelines
    - Provide Ayurveda-aligned food preferences
    
    Inputs:
    - Client profile
    - MNT constraints (must comply with)
    - Target context
    
    Outputs:
    - Dosha assessment (primary, secondary)
    - Vikriti notes
    - Lifestyle guidelines
    - Food preferences (advisory, modifiable)
    
    Rules:
    - Ayurveda suggestions are ADVISORY ONLY
    - Must comply with MNT output
    - Cannot override macro/micro constraints
    - Cannot override medical exclusions
    - All suggestions tagged as "modifiable"
    """
    
    def __init__(self):
        """Initialize Ayurveda engine."""
        pass
    
    def process_ayurveda_assessment(
        self,
        client_profile: Dict[str, Any],
        mnt_context: MNTContext,
        target_context: TargetContext
    ) -> AyurvedaContext:
        """
        Process Ayurveda assessment and generate advisory guidelines.
        
        Args:
            client_profile: Client profile data
            mnt_context: MNT context (must comply with)
            target_context: Target context with nutrition targets
            
        Returns:
            AyurvedaContext with dosha assessment and lifestyle guidelines
            
        Note:
            This method:
            1. Assesses dosha (primary and secondary)
            2. Generates lifestyle optimization guidelines
            3. Provides food preferences that comply with MNT constraints
            All outputs are advisory and modifiable.
        """
        intake_data = client_profile.get("intake_data") if client_profile else None

        # Require questionnaire by default (mandatory for proper assessment)
        dosha_assessment = self.assess_dosha(
            client_profile, 
            intake_data=intake_data,
            require_questionnaire=True  # Make questionnaire mandatory for production
        )
        lifestyle_guidelines = self.generate_lifestyle_guidelines(dosha_assessment, mnt_context)
        food_preferences = self.generate_food_preferences(dosha_assessment, mnt_context)

        # Build comprehensive vikriti_notes with full assessment
        vikriti_notes = {
            "prakriti": dosha_assessment.get("prakriti"),
            "vikriti": dosha_assessment.get("vikriti"),
            "agni": dosha_assessment.get("agni"),
            "ama": dosha_assessment.get("ama"),
            "ayurvedic_constraints": dosha_assessment.get("ayurvedic_constraints"),
            # Backward compatibility
            "dosha_scores": dosha_assessment.get("dosha_scores"),
            "source": dosha_assessment.get("source", "rule_based"),
            "advisory": True,
            "modifiable": True,
            "food_preferences": food_preferences,
        }

        return AyurvedaContext(
            assessment_id=mnt_context.assessment_id,
            dosha_primary=dosha_assessment.get("dosha_primary"),
            dosha_secondary=dosha_assessment.get("dosha_secondary"),
            vikriti_notes=vikriti_notes,
            lifestyle_guidelines=lifestyle_guidelines,
        )
    
    def assess_dosha(
        self,
        client_profile: Dict[str, Any],
        intake_data: Optional[Dict[str, Any]] = None,
        require_questionnaire: bool = True
    ) -> Dict[str, Any]:
        """
        Comprehensive Ayurvedic assessment: Prakriti, Vikriti, Agni, and Ama.
        
        Args:
            client_profile: Client profile data
            intake_data: Optional intake/quiz data for dosha assessment
            require_questionnaire: If True, raises error if questionnaire data is missing
            
        Returns:
            Dictionary containing:
            - prakriti: Constitution assessment with primary/secondary dosha and scores
            - vikriti: Current imbalance assessment
            - agni: Digestive fire type
            - ama: Toxin level
            - dosha_primary: Primary dosha (for backward compatibility)
            - dosha_secondary: Secondary dosha (for backward compatibility)
            - dosha_scores: Scores for each dosha (for backward compatibility)
            - ayurvedic_constraints: Food qualities and lifestyle constraints
            
        Raises:
            ValueError: If require_questionnaire=True and questionnaire data is missing
            
        Note:
            Uses structured questionnaire responses from ayurveda_assessment.
            Falls back to heuristics only if require_questionnaire=False (not recommended for production).
        """
        intake_data = intake_data or {}
        
        # Extract questionnaire responses
        ayurveda_data = intake_data.get("ayurveda_assessment") or {}
        
        # Validate questionnaire data exists
        if require_questionnaire:
            if not ayurveda_data or not isinstance(ayurveda_data, dict) or len(ayurveda_data) == 0:
                raise ValueError(
                    "Ayurveda questionnaire assessment is required. "
                    "Please complete the Ayurveda assessment questionnaire before generating a plan. "
                    "The questionnaire provides structured inputs needed for proper Prakriti, Vikriti, Agni, and Ama assessment."
                )
        
        # If we have questionnaire responses, use the comprehensive assessment
        if ayurveda_data and isinstance(ayurveda_data, dict) and len(ayurveda_data) > 0:
            return self._assess_from_questionnaire(ayurveda_data)
        
        # Fallback: only if require_questionnaire=False (for backward compatibility/testing)
        if not require_questionnaire:
            return self._assess_from_heuristics(client_profile, intake_data)
        
        # Should not reach here if require_questionnaire=True
        raise ValueError("Ayurveda questionnaire assessment is required but not provided.")
    
    def _assess_from_questionnaire(self, responses: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess from structured questionnaire responses.
        
        Args:
            responses: Dictionary of question_id -> answer mappings
            
        Returns:
            Complete assessment dictionary
        """
        # Calculate Prakriti (constitution)
        prakriti_scores = calculate_prakriti_scores(responses)
        prakriti_doshas = determine_dosha_primary_secondary(prakriti_scores)
        
        # Calculate Vikriti (imbalance)
        vikriti_result = calculate_vikriti_scores(responses, prakriti_scores)
        
        # Determine Agni
        agni = determine_agni_type(responses)
        
        # Determine Ama
        ama = determine_ama_level(responses)
        
        # Generate constraints
        ayurvedic_constraints = generate_ayurvedic_constraints(
            prakriti=prakriti_doshas,
            vikriti=vikriti_result,
            agni=agni,
            ama=ama,
        )
        
        # Convert scores to lowercase for backward compatibility
        dosha_scores_lower = {
            k.lower(): v for k, v in prakriti_scores.items()
        }
        
        return {
            "prakriti": {
                "primary": prakriti_doshas.get("primary"),
                "secondary": prakriti_doshas.get("secondary"),
                "scores": prakriti_scores,
            },
            "vikriti": {
                "imbalanced_doshas": vikriti_result.get("imbalanced_doshas", []),
                "severity": vikriti_result.get("severity", "none"),
                "scores": vikriti_result.get("scores", {}),
            },
            "agni": agni,
            "ama": ama,
            "ayurvedic_constraints": ayurvedic_constraints,
            # Backward compatibility fields
            "dosha_primary": prakriti_doshas.get("primary"),
            "dosha_secondary": prakriti_doshas.get("secondary"),
            "dosha_scores": dosha_scores_lower,
            "source": "rule_based",
        }
    
    def _assess_from_heuristics(
        self,
        client_profile: Dict[str, Any],
        intake_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fallback assessment using heuristics (for backward compatibility).
        
        Args:
            client_profile: Client profile data
            intake_data: Intake data dictionary
            
        Returns:
            Basic assessment dictionary
        """
        scores = {"vata": 0, "pitta": 0, "kapha": 0}

        # Try to get old format quiz scores
        quiz = intake_data.get("ayurveda_quiz") or {}
        quiz_scores = quiz.get("dosha_scores")
        if isinstance(quiz_scores, dict):
            for k, v in quiz_scores.items():
                if k.lower() in scores and isinstance(v, (int, float)):
                    scores[k.lower()] = float(v)

        # Heuristic fallbacks
        symptoms = (intake_data.get("symptoms") or []) + (intake_data.get("complaints") or [])
        symptoms_lower = [s.lower() for s in symptoms if isinstance(s, str)]

        # Compute BMI if available
        bmi = None
        weight = client_profile.get("weight_kg")
        height_cm = client_profile.get("height_cm")
        if weight and height_cm:
            height_m = height_cm / 100
            if height_m > 0:
                bmi = weight / (height_m ** 2)

        # Pitta indicators
        if "acidity" in symptoms_lower or "heat" in symptoms_lower:
            scores["pitta"] += 1
        # Kapha indicators
        if "lethargy" in symptoms_lower or (bmi and bmi > 27):
            scores["kapha"] += 1
        # Vata indicators
        if "bloating" in symptoms_lower or (bmi and bmi < 19):
            scores["vata"] += 1

        # Determine primary/secondary
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        dosha_primary = sorted_scores[0][0] if sorted_scores and sorted_scores[0][1] > 0 else None
        dosha_secondary = None
        if len(sorted_scores) > 1 and sorted_scores[1][1] > 0:
            dosha_secondary = sorted_scores[1][0]

        # Build basic prakriti structure
        prakriti_doshas = {
            "primary": dosha_primary,
            "secondary": dosha_secondary,
        }
        prakriti = {
            "primary": dosha_primary,
            "secondary": dosha_secondary,
            "scores": {k.capitalize(): v for k, v in scores.items()},
        }

        # Build vikriti structure (neutral when using heuristics - no questionnaire data)
        vikriti_result = {
            "imbalanced_doshas": [],
            "severity": "none",
            "scores": {k.capitalize(): v for k, v in scores.items()},
        }

        # Generate constraints (even from heuristics, constraints can be generated)
        from .constraints_generator import generate_ayurvedic_constraints
        ayurvedic_constraints = generate_ayurvedic_constraints(
            prakriti=prakriti_doshas,
            vikriti=vikriti_result,
            agni="normal",  # Default when unknown
            ama="none",  # Default when unknown
        )

        # Return structure consistent with questionnaire-based assessment
        return {
            "prakriti": prakriti,
            "vikriti": vikriti_result,
            "agni": "normal",  # Default when unknown
            "ama": "none",  # Default when unknown
            "ayurvedic_constraints": ayurvedic_constraints,
            "dosha_primary": dosha_primary,
            "dosha_secondary": dosha_secondary,
            "dosha_scores": scores,
            "source": "heuristic",
        }
    
    def generate_lifestyle_guidelines(
        self,
        dosha_assessment: Dict[str, Any],
        mnt_context: MNTContext
    ) -> Dict[str, Any]:
        """
        Generate lifestyle optimization guidelines.
        
        Args:
            dosha_assessment: Dosha assessment results
            mnt_context: MNT context (guidelines must comply with)
            
        Returns:
            Dictionary containing lifestyle guidelines:
            - meal_timing: Recommended meal timing
            - food_temperature: Preferred food temperatures
            - spices: Recommended spices
            - lifestyle_practices: General lifestyle recommendations
            
        Note:
            Guidelines are advisory only and must not conflict with MNT constraints.
        """
        dosha_primary = (dosha_assessment or {}).get("dosha_primary")
        profile = get_profile(dosha_primary) or {}

        food_exclusions = set(mnt_context.food_exclusions or [])
        macro_constraints = mnt_context.macro_constraints or {}
        micro_constraints = mnt_context.micro_constraints or {}

        spices = profile.get("favor_spices", []) or profile.get("favor", []) or []
        # Filter out excluded spices/foods
        spices = [s for s in spices if s not in food_exclusions]

        meal_timing = profile.get("meal_timing") or "regular_meals"
        food_temperature = profile.get("food_temperature") or "warm"
        lifestyle = profile.get("lifestyle") or []

        # Add caution if sodium constrained
        sodium_constraint = micro_constraints.get("sodium_mg", {}).get("max")
        notes = []
        if sodium_constraint is not None:
            notes.append(f"Limit salty condiments; sodium max {sodium_constraint} mg.")

        # Add caution if calorie deficit
        calorie_deficit = macro_constraints.get("calories", {}).get("deficit_percent")
        if calorie_deficit:
            notes.append(f"Respect calorie deficit of {calorie_deficit}% (no high-calorie additions).")

        guidelines = {
            "meal_timing": {
                "recommendation": meal_timing,
                "advisory": True,
                "modifiable": True,
                "source": "ayurveda_rule",
            },
            "food_temperature": {
                "recommendation": food_temperature,
                "advisory": True,
                "modifiable": True,
                "source": "ayurveda_rule",
            },
            "spices": {
                "recommendation": spices,
                "advisory": True,
                "modifiable": True,
                "source": "ayurveda_rule",
            },
            "lifestyle_practices": {
                "recommendation": lifestyle,
                "advisory": True,
                "modifiable": True,
                "source": "ayurveda_rule",
            },
        }
        if notes:
            guidelines["notes"] = notes

        return guidelines
    
    def generate_food_preferences(
        self,
        dosha_assessment: Dict[str, Any],
        mnt_context: MNTContext
    ) -> List[Dict[str, Any]]:
        """
        Generate Ayurveda-aligned food preferences.
        
        Args:
            dosha_assessment: Dosha assessment results
            mnt_context: MNT context (preferences must comply with)
            
        Returns:
            List of food preferences, each containing:
            - food_id: Food knowledge base ID
            - preference_type: preferred | avoid | neutral
            - reason: Ayurveda reasoning
            - modifiable: True (all preferences are modifiable)
            
        Note:
            Preferences are advisory only.
            Must not include foods in MNT exclusions.
            Cannot override macro/micro constraints.
        """
        dosha_primary = (dosha_assessment or {}).get("dosha_primary")
        profile = get_profile(dosha_primary) or {}
        food_exclusions = set(mnt_context.food_exclusions or [])

        preferences: List[Dict[str, Any]] = []

        # Favor lists
        favor_list = profile.get("favor_spices") or profile.get("favor") or []
        for food in favor_list:
            if food in food_exclusions:
                continue
            preferences.append({
                "food_id": food,
                "preference_type": "prefer",
                "reason": f"ayurveda_{dosha_primary}_favor",
                "modifiable": True,
            })

        # Avoid lists
        avoid_list = profile.get("avoid") or []
        for food in avoid_list:
            if food in food_exclusions:
                continue  # already excluded by MNT
            preferences.append({
                "food_id": food,
                "preference_type": "avoid",
                "reason": f"ayurveda_{dosha_primary}_avoid",
                "modifiable": True,
            })

        return preferences

