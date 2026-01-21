"""
Platform Quiz Questions API Routes.
Read-only endpoints for quiz questions used by frontend.
"""
from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/quizzes", tags=["Platform Quizzes"])


# Response Schemas
class QuizQuestion(BaseModel):
    """Quiz question schema with optional dosha/state fields."""
    id: str  # question_id
    question_text: str  # question
    option_a: str
    option_b: str
    option_c: Optional[str] = None  # Optional for multi-select questions
    dosha_a: Optional[str] = None
    dosha_b: Optional[str] = None
    dosha_c: Optional[str] = None
    state_a: Optional[str] = None
    state_b: Optional[str] = None
    state_c: Optional[str] = None
    question_type: Optional[str] = "radio"  # "radio" or "checkbox" for multi-select


class QuestionnaireSection(BaseModel):
    """Section of the Ayurveda assessment questionnaire."""
    section_id: str
    section_title: str
    section_description: Optional[str] = None
    questions: List[QuizQuestion]


class AyurvedaAssessmentQuestionsResponse(BaseModel):
    """Response schema for comprehensive Ayurveda assessment questionnaire."""
    sections: List[QuestionnaireSection]


class GutHealthQuizQuestionsResponse(BaseModel):
    """Response schema for gut health quiz questions."""
    questions: List[QuizQuestion]


# Ayurveda Assessment Questionnaire Structure
# Based on the comprehensive questionnaire document
# Note: Section 0 demographics (age, gender, height, weight) are collected in intake, so excluded here

AYURVEDA_ASSESSMENT_QUESTIONS = {
    "section_0": {
        "section_id": "section_0",
        "section_title": "Client Context",
        "section_description": "Additional context information",
        "questions": [
            {
                "question_id": "0.1_location_climate",
                "question": "Location / Climate",
                "option_a": "Cold",
                "option_b": "Moderate",
                "option_c": "Hot / Humid",
                "dosha_a": "Vata",  # Cold aggravates Vata
                "dosha_b": "Balanced",  # Moderate is neutral
                "dosha_c": "Pitta"  # Hot aggravates Pitta
            },
            {
                "question_id": "0.2_daily_physical_activity",
                "question": "Daily physical activity",
                "option_a": "None",
                "option_b": "Light (walking, yoga)",
                "option_c": "Moderate to Intense (gym, sports)",
                "dosha_a": "Kapha",  # No activity = Kapha
                "dosha_b": "Vata",  # Light activity = Vata
                "dosha_c": "Pitta"  # Intense activity = Pitta
            }
        ]
    },
    "section_1": {
        "section_id": "section_1",
        "section_title": "Physical Constitution (Prakriti Indicators)",
        "section_description": "Assess your physical constitution traits",
        "questions": [
            {
                "question_id": "1.1_body_structure",
                "question": "Body frame",
                "option_a": "Thin / lean, difficulty gaining weight",
                "option_b": "Medium, proportionate",
                "option_c": "Broad / heavy, gains weight easily",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"
            },
            {
                "question_id": "1.2_weight_pattern",
                "question": "Weight changes over time",
                "option_a": "Fluctuates easily",
                "option_b": "Stable",
                "option_c": "Increases easily, difficult to lose",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"
            },
            {
                "question_id": "1.3_skin",
                "question": "Skin type",
                "option_a": "Dry, rough, cracked",
                "option_b": "Warm, sensitive, acne-prone",
                "option_c": "Thick, oily, smooth",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"
            },
            {
                "question_id": "1.4_hair",
                "question": "Hair quality",
                "option_a": "Dry, frizzy, brittle",
                "option_b": "Fine, premature greying or thinning",
                "option_c": "Thick, oily, strong",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"
            },
            {
                "question_id": "1.5_sweating",
                "question": "Sweating tendency",
                "option_a": "Minimal",
                "option_b": "Moderate to heavy",
                "option_c": "Low but sticky",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"
            }
        ]
    },
    "section_2": {
        "section_id": "section_2",
        "section_title": "Appetite & Digestion (Agni Assessment)",
        "section_description": "Assess your digestive fire (Agni)",
        "questions": [
            {
                "question_id": "2.1_hunger_pattern",
                "question": "Hunger timing",
                "option_a": "Irregular, unpredictable",
                "option_b": "Strong and sharp",
                "option_c": "Mild, delayed",
                "dosha_a": "Vata",  # Vishama Agni
                "dosha_b": "Pitta",  # Tikshna Agni
                "dosha_c": "Kapha"  # Manda Agni
            },
            {
                "question_id": "2.2_appetite_strength",
                "question": "When hungry, you feel",
                "option_a": "Nervous or shaky",
                "option_b": "Irritable or angry",
                "option_c": "Comfortable but slow",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"
            },
            {
                "question_id": "2.3_digestive_comfort",
                "question": "After meals you feel",
                "option_a": "Gas, bloating, discomfort",
                "option_b": "Burning, acidity, heaviness in chest",
                "option_c": "Heaviness, lethargy",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"
            },
            {
                "question_id": "2.4_bowel_movements",
                "question": "Stool consistency",
                "option_a": "Dry, hard, constipated",
                "option_b": "Loose or frequent",
                "option_c": "Sticky, oily, sluggish",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"
            }
        ]
    },
    "section_3": {
        "section_id": "section_3",
        "section_title": "Ama (Toxin) Indicators",
        "section_description": "Assess presence of toxins (Ama) in your system",
        "questions": [
            {
                "question_id": "3.1_tongue",
                "question": "Tongue appearance (morning)",
                "option_a": "Clean, pink",
                "option_b": "Yellowish coating",
                "option_c": "Thick white coating",
                "dosha_a": "None",  # No Ama
                "dosha_b": "Pitta",  # Pitta-related Ama
                "dosha_c": "Kapha"  # Kapha-related Ama (high Ama)
            },
            {
                "question_id": "3.2_energy_levels",
                "question": "Daily energy",
                "option_a": "Fluctuates, crashes easily",
                "option_b": "Intense but burns out",
                "option_c": "Low but steady",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"
            },
            {
                "question_id": "3.3_mental_clarity",
                "question": "You experience",
                "option_a": "Racing thoughts",
                "option_b": "Sharp focus but irritability",
                "option_c": "Brain fog or dullness",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"  # High Ama indicator
            },
            {
                "question_id": "3.4_post_meal_feeling",
                "question": "After eating you often feel",
                "option_a": "Light but unsettled",
                "option_b": "Hot or acidic",
                "option_c": "Heavy and sleepy",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"  # High Ama indicator
            }
        ]
    },
    "section_4": {
        "section_id": "section_4",
        "section_title": "Mental & Emotional Traits",
        "section_description": "Assess your mental and emotional patterns",
        "questions": [
            {
                "question_id": "4.1_thinking_style",
                "question": "You tend to think",
                "option_a": "Quickly, many ideas",
                "option_b": "Focused and analytical",
                "option_c": "Slowly and deeply",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"
            },
            {
                "question_id": "4.2_stress_response",
                "question": "Under stress you become",
                "option_a": "Anxious or fearful",
                "option_b": "Irritable or angry",
                "option_c": "Withdrawn or resistant",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"
            },
            {
                "question_id": "4.3_memory",
                "question": "Memory type",
                "option_a": "Quick to learn, quick to forget",
                "option_b": "Sharp and precise",
                "option_c": "Slow to learn, strong retention",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"
            }
        ]
    },
    "section_5": {
        "section_id": "section_5",
        "section_title": "Sleep Patterns",
        "section_description": "Assess your sleep patterns",
        "questions": [
            {
                "question_id": "5.1_sleep_duration",
                "question": "Average sleep",
                "option_a": "Less than 6 hours",
                "option_b": "6–8 hours",
                "option_c": "More than 8 hours",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"
            },
            {
                "question_id": "5.2_sleep_quality",
                "question": "Sleep feels",
                "option_a": "Light, interrupted",
                "option_b": "Moderate, refreshing",
                "option_c": "Deep, heavy",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"
            },
            {
                "question_id": "5.3_sleep_timing",
                "question": "Bedtime",
                "option_a": "Late night",
                "option_b": "Around 10–11 PM",
                "option_c": "Early but prolonged",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"
            }
        ]
    },
    "section_6": {
        "section_id": "section_6",
        "section_title": "Food Preferences & Cravings",
        "section_description": "Assess your food preferences and cravings",
        "questions": [
            {
                "question_id": "6.1_taste_preference",
                "question": "You crave mostly",
                "option_a": "Sweet, sour, salty",
                "option_b": "Spicy, pungent, fried",
                "option_c": "Sweet, creamy, heavy foods",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"
            },
            {
                "question_id": "6.2_temperature_preference",
                "question": "You prefer food that is",
                "option_a": "Warm",
                "option_b": "Hot",
                "option_c": "Cool or room temperature",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Pitta"  # Pitta prefers cool
            },
            {
                "question_id": "6.3_raw_foods",
                "question": "Raw foods (salads, smoothies)",
                "option_a": "Cause discomfort",
                "option_b": "Are tolerable",
                "option_c": "Feel heavy or increase mucus",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"
            }
        ]
    },
    "section_7": {
        "section_id": "section_7",
        "section_title": "Lifestyle Tendencies",
        "section_description": "Assess your lifestyle patterns",
        "questions": [
            {
                "question_id": "7.1_daily_routine",
                "question": "Routine consistency",
                "option_a": "Irregular",
                "option_b": "Mostly consistent",
                "option_c": "Very stable",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"
            },
            {
                "question_id": "7.2_meal_timing",
                "question": "Meal schedule",
                "option_a": "Skipped or delayed meals",
                "option_b": "Mostly on time",
                "option_c": "Fixed and predictable",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"
            },
            {
                "question_id": "7.3_exercise_preference",
                "question": "Exercise feels best when",
                "option_a": "Gentle and grounding",
                "option_b": "Challenging and intense",
                "option_c": "Slow and steady",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"
            }
        ]
    },
    "section_8": {
        "section_id": "section_8",
        "section_title": "Current Complaints (Vikriti Signals)",
        "section_description": "Select all current complaints that apply (indicates current imbalances)",
        "questions": [
            {
                "question_id": "8.1_dryness",
                "question": "Dryness",
                "option_a": "Yes",
                "option_b": "No",
                "dosha_a": "Vata",
                "question_type": "checkbox"
            },
            {
                "question_id": "8.2_gas_bloating",
                "question": "Gas / bloating",
                "option_a": "Yes",
                "option_b": "No",
                "dosha_a": "Vata",
                "question_type": "checkbox"
            },
            {
                "question_id": "8.3_acidity_heartburn",
                "question": "Acidity / heartburn",
                "option_a": "Yes",
                "option_b": "No",
                "dosha_a": "Pitta",
                "question_type": "checkbox"
            },
            {
                "question_id": "8.4_inflammation",
                "question": "Inflammation",
                "option_a": "Yes",
                "option_b": "No",
                "dosha_a": "Pitta",
                "question_type": "checkbox"
            },
            {
                "question_id": "8.5_weight_gain",
                "question": "Weight gain",
                "option_a": "Yes",
                "option_b": "No",
                "dosha_a": "Kapha",
                "question_type": "checkbox"
            },
            {
                "question_id": "8.6_lethargy",
                "question": "Lethargy",
                "option_a": "Yes",
                "option_b": "No",
                "dosha_a": "Kapha",
                "question_type": "checkbox"
            },
            {
                "question_id": "8.7_anxiety",
                "question": "Anxiety",
                "option_a": "Yes",
                "option_b": "No",
                "dosha_a": "Vata",
                "question_type": "checkbox"
            },
            {
                "question_id": "8.8_anger",
                "question": "Anger",
                "option_a": "Yes",
                "option_b": "No",
                "dosha_a": "Pitta",
                "question_type": "checkbox"
            },
            {
                "question_id": "8.9_mucus_congestion",
                "question": "Mucus / congestion",
                "option_a": "Yes",
                "option_b": "No",
                "dosha_a": "Kapha",
                "question_type": "checkbox"
            }
        ]
    },
    "section_9": {
        "section_id": "section_9",
        "section_title": "Season & Environment",
        "section_description": "Assess seasonal and environmental factors",
        "questions": [
            {
                "question_id": "9.1_current_season",
                "question": "Current season",
                "option_a": "Summer",
                "option_b": "Winter",
                "option_c": "Rainy / humid",
                "dosha_a": "Pitta",  # Summer aggravates Pitta
                "dosha_b": "Vata",  # Winter aggravates Vata
                "dosha_c": "Kapha"  # Rainy/humid aggravates Kapha
            },
            {
                "question_id": "9.2_worst_weather",
                "question": "You feel worst during",
                "option_a": "Cold & dry weather",
                "option_b": "Hot weather",
                "option_c": "Damp / cloudy weather",
                "dosha_a": "Vata",
                "dosha_b": "Pitta",
                "dosha_c": "Kapha"
            }
        ]
    }
}

# Gut Health Quiz Questions
GUT_HEALTH_QUIZ_QUESTIONS = [
    {
        "question_id": "gq1_appetite",
        "question": "How regular is your appetite each day?",
        "option_a": "Regular appetite at consistent times",
        "option_b": "Low appetite, sometimes skip meals",
        "option_c": "Very strong appetite, get irritable if delayed",
        "state_a": "Balanced Gut",
        "state_b": "Weak Gut",
        "state_c": "Overactive Gut"
    },
    {
        "question_id": "gq2_digestion",
        "question": "After meals, how does your digestion feel?",
        "option_a": "Feel light and satisfied after eating",
        "option_b": "Feel bloated or heavy after meals",
        "option_c": "Experience acidity or burning after meals",
        "state_a": "Balanced Gut",
        "state_b": "Weak Gut",
        "state_c": "Overactive Gut"
    },
    {
        "question_id": "gq3_bowel",
        "question": "How often do you have bowel movements?",
        "option_a": "Once daily, well-formed stool",
        "option_b": "Irregular, sometimes constipated",
        "option_c": "Loose stools or frequent urges",
        "state_a": "Balanced Gut",
        "state_b": "Weak Gut",
        "state_c": "Overactive Gut"
    },
    {
        "question_id": "gq4_post_meal",
        "question": "How do you feel 1 hour after eating?",
        "option_a": "Energized and stable",
        "option_b": "Sleepy or tired after meals",
        "option_c": "Restless or anxious after meals",
        "state_a": "Balanced Gut",
        "state_b": "Weak Gut",
        "state_c": "Overactive Gut"
    },
    {
        "question_id": "gq5_food_reaction",
        "question": "How does your body react to new or heavy foods?",
        "option_a": "Tolerate most foods well",
        "option_b": "Feel bloated or uneasy after new foods",
        "option_c": "Get acidity or quick reactions after certain foods",
        "state_a": "Balanced Gut",
        "state_b": "Weak Gut",
        "state_c": "Overactive Gut"
    },
    {
        "question_id": "gq6_tongue_breath",
        "question": "Do you notice coating on your tongue or bad breath?",
        "option_a": "No coating, fresh breath",
        "option_b": "White coating, mild bad breath",
        "option_c": "Red tongue, sour or bitter taste",
        "state_a": "Balanced Gut",
        "state_b": "Weak Gut",
        "state_c": "Overactive Gut"
    },
    {
        "question_id": "gq7_sleep",
        "question": "How do you sleep at night?",
        "option_a": "Deep, restful sleep",
        "option_b": "Sleep long but feel tired in the morning",
        "option_c": "Light, disturbed sleep",
        "state_a": "Balanced Gut",
        "state_b": "Weak Gut",
        "state_c": "Overactive Gut"
    },
    {
        "question_id": "gq8_eating_habit",
        "question": "How do you usually eat your meals?",
        "option_a": "Eat mindfully without distractions",
        "option_b": "Eat quickly or while watching screens",
        "option_c": "Eat irregularly or skip meals often",
        "state_a": "Balanced Gut",
        "state_b": "Weak Gut",
        "state_c": "Overactive Gut"
    },
    {
        "question_id": "gq9_bloating",
        "question": "When do you feel most bloated during the day?",
        "option_a": "Rarely feel bloated",
        "option_b": "Bloating after lunch or dinner",
        "option_c": "Bloating in the morning or after spicy foods",
        "state_a": "Balanced Gut",
        "state_b": "Weak Gut",
        "state_c": "Overactive Gut"
    },
    {
        "question_id": "gq10_immunity",
        "question": "How strong is your immunity (how often do you fall sick)?",
        "option_a": "Strong immunity, rarely fall sick",
        "option_b": "Catch colds or infections easily",
        "option_c": "Occasionally get inflammation or skin breakouts",
        "state_a": "Balanced Gut",
        "state_b": "Weak Gut",
        "state_c": "Overactive Gut"
    }
]


def _map_question_to_schema(question_data: dict) -> QuizQuestion:
    """
    Map question data dictionary to QuizQuestion schema.
    
    Args:
        question_data: Dictionary with question fields
        
    Returns:
        QuizQuestion instance
    """
    return QuizQuestion(
        id=question_data["question_id"],
        question_text=question_data["question"],
        option_a=question_data["option_a"],
        option_b=question_data["option_b"],
        option_c=question_data.get("option_c"),
        dosha_a=question_data.get("dosha_a"),
        dosha_b=question_data.get("dosha_b"),
        dosha_c=question_data.get("dosha_c"),
        state_a=question_data.get("state_a"),
        state_b=question_data.get("state_b"),
        state_c=question_data.get("state_c"),
        question_type=question_data.get("question_type", "radio"),
    )


@router.get("/ayurveda-assessment/questions", response_model=AyurvedaAssessmentQuestionsResponse)
async def get_ayurveda_assessment_questions():
    """
    Get comprehensive Ayurveda assessment questionnaire.
    
    This questionnaire collects structured inputs for Prakriti, Vikriti, Agni, and Ama assessment.
    Note: Demographics (age, gender, height, weight) are collected in the intake step.
    
    Returns:
        Structured questionnaire with sections and questions for Ayurvedic assessment.
    """
    sections = []
    for section_key, section_data in AYURVEDA_ASSESSMENT_QUESTIONS.items():
        questions = [_map_question_to_schema(q) for q in section_data["questions"]]
        sections.append(QuestionnaireSection(
            section_id=section_data["section_id"],
            section_title=section_data["section_title"],
            section_description=section_data.get("section_description"),
            questions=questions
        ))
    return AyurvedaAssessmentQuestionsResponse(sections=sections)


@router.get("/gut-health/questions", response_model=GutHealthQuizQuestionsResponse)
async def get_gut_health_quiz_questions():
    """
    Get all gut health quiz questions.
    
    Returns:
        List of gut health quiz questions with state mapping for each option.
    """
    questions = [_map_question_to_schema(q) for q in GUT_HEALTH_QUIZ_QUESTIONS]
    return GutHealthQuizQuestionsResponse(questions=questions)

