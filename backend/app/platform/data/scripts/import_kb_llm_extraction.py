"""
LLM-Powered Knowledge Base Data Extraction Script.

Uses LLM (GPT-4/Claude) to extract structured data from PDFs, web pages, or text.
This is for Phase 2+ of data import - scaling with AI.

Requirements:
    pip install openai anthropic pdfplumber pypdf2

Usage:
    python -m app.platform.data.scripts.import_kb_llm_extraction \
        --source pdf --file guidelines.pdf --kb medical_conditions \
        --llm openai --api-key YOUR_KEY
"""
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.database import SessionLocal
from app.platform.data.scripts.import_kb_manual import import_data
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMExtractor:
    """LLM-based data extractor."""
    
    def __init__(self, provider: str = "openai", api_key: Optional[str] = None):
        """
        Initialize LLM extractor.
        
        Args:
            provider: LLM provider ("openai" or "anthropic")
            api_key: API key (or use environment variable)
        """
        self.provider = provider
        self.api_key = api_key
        
        if provider == "openai":
            try:
                import openai
                self.client = openai.OpenAI(api_key=api_key or None)
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        elif provider == "anthropic":
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=api_key or None)
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def extract_from_pdf(self, pdf_path: str, kb_type: str, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract structured data from PDF.
        
        Args:
            pdf_path: Path to PDF file
            kb_type: KB type to extract
            schema: JSON schema for validation
            
        Returns:
            List of extracted data dictionaries
        """
        # Extract text from PDF
        text = self._extract_pdf_text(pdf_path)
        
        # Use LLM to extract structured data
        prompt = self._build_extraction_prompt(kb_type, schema, text)
        
        extracted_data = self._call_llm(prompt)
        
        # Parse and validate
        return self._parse_extracted_data(extracted_data, schema)
    
    def extract_from_text(self, text: str, kb_type: str, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract structured data from text."""
        prompt = self._build_extraction_prompt(kb_type, schema, text)
        extracted_data = self._call_llm(prompt)
        return self._parse_extracted_data(extracted_data, schema)
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF."""
        try:
            import pdfplumber
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
            return text
        except ImportError:
            raise ImportError("pdfplumber not installed. Run: pip install pdfplumber")
    
    def _build_extraction_prompt(self, kb_type: str, schema: Dict[str, Any], text: str) -> str:
        """Build LLM prompt for extraction."""
        return f"""Extract structured data for {kb_type} knowledge base from the following text.

Schema:
{json.dumps(schema, indent=2)}

Text:
{text[:10000]}  # Limit text length

Instructions:
1. Extract all relevant {kb_type} entries from the text
2. Structure data according to the schema
3. Return JSON array of objects
4. Include source references where available
5. Be precise with numeric values and thresholds

Return only valid JSON array, no additional text.
"""
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM API."""
        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a data extraction assistant. Extract structured data and return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content
        elif self.provider == "anthropic":
            response = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
    
    def _parse_extracted_data(self, extracted_data: str, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse and validate extracted data."""
        try:
            # Extract JSON from response (in case LLM adds markdown)
            if "```json" in extracted_data:
                extracted_data = extracted_data.split("```json")[1].split("```")[0]
            elif "```" in extracted_data:
                extracted_data = extracted_data.split("```")[1].split("```")[0]
            
            data = json.loads(extracted_data)
            if isinstance(data, dict):
                data = [data]
            
            # Basic validation
            validated = []
            for item in data:
                if self._validate_item(item, schema):
                    validated.append(item)
                else:
                    logger.warning(f"Skipping invalid item: {item}")
            
            return validated
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.error(f"Response: {extracted_data[:500]}")
            return []
    
    def _validate_item(self, item: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Basic validation of extracted item."""
        # Add schema validation logic here
        return True


def get_schema_for_kb(kb_type: str) -> Dict[str, Any]:
    """Get JSON schema for KB type."""
    schemas = {
        "medical_conditions": {
            "required": ["condition_id", "display_name", "category"],
            "properties": {
                "condition_id": {"type": "string"},
                "display_name": {"type": "string"},
                "category": {"type": "string"},
                "severity_thresholds": {"type": "object"}
            }
        },
        "nutrition_diagnoses": {
            "required": ["diagnosis_id", "problem_statement"],
            "properties": {
                "diagnosis_id": {"type": "string"},
                "problem_statement": {"type": "string"}
            }
        },
        "mnt_rules": {
            "required": ["rule_id", "applies_to_diagnoses"],
            "properties": {
                "rule_id": {"type": "string"},
                "applies_to_diagnoses": {"type": "array"}
            }
        }
    }
    return schemas.get(kb_type, {})


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='LLM-powered KB data extraction')
    parser.add_argument('--source', type=str, choices=['pdf', 'text', 'url'], required=True)
    parser.add_argument('--file', type=str, help='File path (for pdf/text)')
    parser.add_argument('--url', type=str, help='URL (for url source)')
    parser.add_argument('--kb', type=str, required=True, 
                       choices=['medical_conditions', 'nutrition_diagnoses', 'mnt_rules'])
    parser.add_argument('--llm', type=str, default='openai', choices=['openai', 'anthropic'])
    parser.add_argument('--api-key', type=str, help='LLM API key (or use env var)')
    parser.add_argument('--dry-run', action='store_true', help='Extract but do not import')
    parser.add_argument('--output', type=str, help='Save extracted data to JSON file')
    
    args = parser.parse_args()
    
    # Initialize extractor
    extractor = LLMExtractor(provider=args.llm, api_key=args.api_key)
    
    # Get schema
    schema = get_schema_for_kb(args.kb)
    
    # Extract data
    if args.source == "pdf":
        if not args.file:
            parser.error("--file required for pdf source")
        logger.info(f"Extracting from PDF: {args.file}")
        extracted = extractor.extract_from_pdf(args.file, args.kb, schema)
    elif args.source == "text":
        if not args.file:
            parser.error("--file required for text source")
        with open(args.file, 'r', encoding='utf-8') as f:
            text = f.read()
        logger.info(f"Extracting from text file: {args.file}")
        extracted = extractor.extract_from_text(text, args.kb, schema)
    elif args.source == "url":
        # TODO: Implement web scraping
        raise NotImplementedError("URL extraction not yet implemented")
    
    logger.info(f"Extracted {len(extracted)} items")
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(extracted, f, indent=2)
        logger.info(f"Saved extracted data to {args.output}")
    
    # Import to database if not dry-run
    if not args.dry_run:
        db = SessionLocal()
        try:
            result = import_data(db, args.kb, extracted, update_existing=False)
            logger.info(f"✓ Imported {result['imported']} items")
        except Exception as e:
            logger.error(f"Error importing: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()
    else:
        logger.info("Dry run - data not imported. Use --output to save extracted data.")


if __name__ == "__main__":
    main()

