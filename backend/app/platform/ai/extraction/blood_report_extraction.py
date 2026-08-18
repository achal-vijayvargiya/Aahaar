"""
Blood Report Extraction Service.

Extracts blood report values from uploaded documents using OCR and LLM.
"""
import io
import json
import base64
from pathlib import Path
from typing import Dict, Any, Optional, List
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
from openai import OpenAI
from app.config import settings


class BloodReportExtractor:
    """
    Extract blood report values from uploaded documents.
    
    Uses OCR (Tesseract) for text extraction and LLM (OpenAI) for structured data extraction.
    """
    
    def __init__(self):
        """Initialize the extractor with OpenAI client."""
        self.client = OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1"
        )
    
    def extract_text_from_pdf(self, file_content: bytes) -> str:
        """
        Extract text from PDF file using PyMuPDF.
        
        Args:
            file_content: PDF file content as bytes
            
        Returns:
            Extracted text from PDF
        """
        try:
            pdf_document = fitz.open(stream=file_content, filetype="pdf")
            text_parts = []
            
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                text_parts.append(page.get_text())
            
            pdf_document.close()
            return "\n".join(text_parts)
        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")
    
    def extract_text_from_image(self, file_content: bytes) -> str:
        """
        Extract text from image file using OCR (Tesseract).
        
        Args:
            file_content: Image file content as bytes
            
        Returns:
            Extracted text from image
        """
        try:
            image = Image.open(io.BytesIO(file_content))
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            raise ValueError(f"Failed to extract text from image: {str(e)}")
    
    def extract_text(self, file_content: bytes, file_extension: str) -> str:
        """
        Extract text from file based on file type.
        
        Args:
            file_content: File content as bytes
            file_extension: File extension (e.g., '.pdf', '.png', '.jpg')
            
        Returns:
            Extracted text
        """
        extension = file_extension.lower()
        
        if extension == '.pdf':
            return self.extract_text_from_pdf(file_content)
        elif extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            return self.extract_text_from_image(file_content)
        else:
            raise ValueError(f"Unsupported file type: {extension}")
    
    def extract_blood_report_values(self, extracted_text: str) -> Dict[str, Any]:
        """
        Extract structured blood report values using LLM.
        
        Args:
            extracted_text: Raw text extracted from document
            
        Returns:
            Dictionary with extracted blood report values
        """
        prompt = f"""Extract blood report values from the following text. Return ONLY a valid JSON object with the following structure. If a value is not found, use null.

Required JSON structure:
{{
  "report_date": "YYYY-MM-DD or null",
  "hb": number or null,
  "rbc": number or null,
  "wbc": number or null,
  "platelets": number or null,
  "fbs": number or null,
  "hba1c": number or null,
  "cholesterol": number or null,
  "triglycerides": number or null,
  "hdl": number or null,
  "ldl": number or null,
  "alt": number or null,
  "ast": number or null,
  "bilirubin": number or null,
  "albumin": number or null,
  "creatinine": number or null,
  "urea": number or null,
  "egfr": number or null,
  "vitamin_d": number or null,
  "vitamin_b12": number or null,
  "tsh": number or null,
  "ferritin": number or null
}}

Important:
- Extract numeric values only (no units in the number)
- Handle different unit formats (mg/dL, g/dL, etc.) but return just the number
- Look for common abbreviations and variations (e.g., HbA1c, HBA1C, Hb A1c)
- Report date should be in YYYY-MM-DD format
- Return null for missing values, not 0

Text to extract from:
{extracted_text}

Return ONLY the JSON object, no other text:"""

        try:
            response = self.client.chat.completions.create(
                model="anthropic/claude-3.5-sonnet",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medical data extraction assistant. Extract blood report values and return ONLY valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=2000
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Clean response - remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parse JSON
            extracted_data = json.loads(response_text)
            
            # Validate and clean the data
            return self._validate_and_clean_extracted_data(extracted_data)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to extract blood report values: {str(e)}")
    
    def _validate_and_clean_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean extracted data.
        
        Args:
            data: Raw extracted data
            
        Returns:
            Cleaned and validated data
        """
        # Expected fields
        expected_fields = [
            "report_date", "hb", "rbc", "wbc", "platelets",
            "fbs", "hba1c", "cholesterol", "triglycerides", "hdl", "ldl",
            "alt", "ast", "bilirubin", "albumin",
            "creatinine", "urea", "egfr",
            "vitamin_d", "vitamin_b12", "tsh", "ferritin"
        ]
        
        cleaned_data = {}
        
        for field in expected_fields:
            value = data.get(field)
            
            # Handle null, None, empty string
            if value is None or value == "":
                cleaned_data[field] = None
            # Handle numeric values
            elif isinstance(value, (int, float)):
                cleaned_data[field] = float(value) if value != 0 else None
            # Handle string numbers
            elif isinstance(value, str):
                try:
                    num_value = float(value)
                    cleaned_data[field] = num_value if num_value != 0 else None
                except ValueError:
                    cleaned_data[field] = None
            else:
                cleaned_data[field] = None
        
        return cleaned_data
    
    def process_file(self, file_content: bytes, file_extension: str) -> Dict[str, Any]:
        """
        Process uploaded file and extract blood report values.
        
        Args:
            file_content: File content as bytes
            file_extension: File extension (e.g., '.pdf', '.png')
            
        Returns:
            Dictionary with extracted blood report values
        """
        # Step 1: Extract text using OCR
        extracted_text = self.extract_text(file_content, file_extension)
        
        if not extracted_text or len(extracted_text.strip()) < 10:
            raise ValueError("No text could be extracted from the file. Please ensure the file contains readable text.")
        
        # Step 2: Extract structured values using LLM
        blood_report_values = self.extract_blood_report_values(extracted_text)
        
        return blood_report_values
