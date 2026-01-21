"""
AI Extraction Module.
OCR, lab report extraction, and free-text intake normalization.
"""

from .extraction import (
    LabReportExtractor,
    IntakeTextNormalizer,
    ExtractionService,
)

__all__ = [
    "LabReportExtractor",
    "IntakeTextNormalizer",
    "ExtractionService",
]
