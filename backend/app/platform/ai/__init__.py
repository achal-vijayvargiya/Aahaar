"""
Platform AI Module.
AI interfaces for extraction, explanation, and generation.
"""

from app.platform.ai.extraction import (
    LabReportExtractor,
    IntakeTextNormalizer,
    ExtractionService,
)
from app.platform.ai.explanation import (
    PlanExplanationGenerator,
    LifestyleCoachGenerator,
    ExplanationService,
)
from app.platform.ai.generation import (
    MealPlanNarrator,
    TextGenerator,
    GenerationService,
)

__all__ = [
    # Extraction
    "LabReportExtractor",
    "IntakeTextNormalizer",
    "ExtractionService",
    # Explanation
    "PlanExplanationGenerator",
    "LifestyleCoachGenerator",
    "ExplanationService",
    # Generation
    "MealPlanNarrator",
    "TextGenerator",
    "GenerationService",
]
