"""
AI Extraction Module.
OCR, lab report extraction, and free-text intake normalization.
"""
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod


class LabReportExtractor(ABC):
    """
    Lab Report Extractor Interface.
    
    Responsibility:
    - Extract structured data from lab report images/documents using OCR
    - Normalize lab values into structured format
    
    Safety Constraints:
    - ONLY extracts data - does NOT interpret or diagnose
    - Does NOT make medical decisions
    - Does NOT calculate thresholds or normal ranges
    - Output must be validated against knowledge base
    - All extracted values must be tagged with units and reference ranges from KB
    
    Inputs:
    - Lab report images (PDF, images)
    - Lab report text (if already extracted)
    
    Outputs:
    - Structured lab values with units
    - Test names and dates
    - No interpretations or diagnoses
    """
    
    @abstractmethod
    def extract_lab_values(self, lab_report: Any) -> Dict[str, Any]:
        """
        Extract lab values from report.
        
        Args:
            lab_report: Lab report (image, PDF, or text)
            
        Returns:
            Dictionary containing:
            - test_name: Test identifier
            - value: Numeric value
            - unit: Unit of measurement
            - date: Test date
            - reference_range: Reference range from KB (not calculated)
            
        Note:
            This method ONLY extracts data. No interpretation or diagnosis.
            All values must be validated against knowledge base.
        """
        pass
    
    @abstractmethod
    def normalize_lab_data(self, raw_extraction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize extracted lab data to standard format.
        
        Args:
            raw_extraction: Raw extracted lab data
            
        Returns:
            Normalized lab data in standard format
            
        Note:
            Normalization only - no interpretation or threshold checking.
        """
        pass


class IntakeTextNormalizer(ABC):
    """
    Intake Text Normalizer Interface.
    
    Responsibility:
    - Parse free-text intake data into structured format
    - Normalize dietary intake descriptions
    - Extract structured information from unstructured text
    
    Safety Constraints:
    - ONLY normalizes and structures data - does NOT make nutrition decisions
    - Does NOT calculate nutrition values
    - Does NOT apply rules or constraints
    - Output must be validated and processed by rule engines
    - All extracted foods must reference knowledge base food IDs
    
    Inputs:
    - Free-text intake descriptions
    - Unstructured dietary history
    
    Outputs:
    - Structured intake data
    - Normalized food references (KB IDs)
    - Meal timing information
    - No nutrition calculations or recommendations
    """
    
    @abstractmethod
    def normalize_intake_text(self, free_text: str) -> Dict[str, Any]:
        """
        Normalize free-text intake into structured format.
        
        Args:
            free_text: Free-text intake description
            
        Returns:
            Dictionary containing:
            - foods: List of food references (KB IDs)
            - meal_times: Meal timing information
            - quantities: Quantity estimates (to be validated)
            - raw_text: Original text for reference
            
        Note:
            This method ONLY normalizes text. No nutrition calculations.
            All foods must reference knowledge base food IDs.
        """
        pass
    
    @abstractmethod
    def extract_food_references(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract food references from text.
        
        Args:
            text: Text containing food references
            
        Returns:
            List of food references, each containing:
            - food_id: Knowledge base food ID (if matched)
            - food_name: Extracted food name
            - confidence: Matching confidence score
            - needs_review: Flag if manual review needed
            
        Note:
            Food matching must reference knowledge base only.
            No hallucination of foods not in KB.
        """
        pass


class ExtractionService:
    """
    Extraction Service.
    
    Coordinates extraction operations for lab reports and intake text.
    Provides unified interface for all extraction needs.
    
    Safety Constraints:
    - All extraction operations are data-only
    - No medical or nutrition decision-making
    - All outputs must be validated by rule engines
    """
    
    def __init__(
        self,
        lab_extractor: Optional[LabReportExtractor] = None,
        intake_normalizer: Optional[IntakeTextNormalizer] = None
    ):
        """
        Initialize extraction service.
        
        Args:
            lab_extractor: Optional lab report extractor implementation
            intake_normalizer: Optional intake text normalizer implementation
        """
        self.lab_extractor = lab_extractor
        self.intake_normalizer = intake_normalizer
    
    def extract_lab_report(self, lab_report: Any) -> Dict[str, Any]:
        """
        Extract structured data from lab report.
        
        Args:
            lab_report: Lab report (image, PDF, or text)
            
        Returns:
            Structured lab data
            
        Note:
            Delegates to lab extractor. No medical interpretation.
        """
        if not self.lab_extractor:
            raise NotImplementedError("Lab extractor not configured")
        return self.lab_extractor.extract_lab_values(lab_report)
    
    def normalize_intake(self, free_text: str) -> Dict[str, Any]:
        """
        Normalize free-text intake.
        
        Args:
            free_text: Free-text intake description
            
        Returns:
            Structured intake data
            
        Note:
            Delegates to intake normalizer. No nutrition calculations.
        """
        if not self.intake_normalizer:
            raise NotImplementedError("Intake normalizer not configured")
        return self.intake_normalizer.normalize_intake_text(free_text)

