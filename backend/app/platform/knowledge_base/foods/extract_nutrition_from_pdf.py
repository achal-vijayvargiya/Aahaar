"""
LLM-based extraction of nutrition data (vitamins & minerals) from IFCT PDFs.

Extracts structured nutrition data from table2.pdf (vitamins) and table3.pdf (minerals)
using LLM with structured output for accurate parsing of complex table layouts.

Requirements:
    pip install openai pdfplumber pypdf

Usage:
    # Extract from table2.pdf (vitamins)
    python -m app.platform.knowledge_base.foods.extract_nutrition_from_pdf \
        --pdf table2.pdf --type vitamins --output vitamins_extracted.json
    
    # Extract from table3.pdf (minerals)
    python -m app.platform.knowledge_base.foods.extract_nutrition_from_pdf \
        --pdf table3.pdf --type minerals --output minerals_extracted.json
    
    # Extract from both
    python -m app.platform.knowledge_base.foods.extract_nutrition_from_pdf \
        --pdf table2.pdf --type vitamins --output vitamins.json && \
    python -m app.platform.knowledge_base.foods.extract_nutrition_from_pdf \
        --pdf table3.pdf --type minerals --output minerals.json
"""

import sys
import json
import argparse
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from decimal import Decimal, InvalidOperation

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.utils.logger import logger


# Pydantic models for structured output
try:
    from pydantic import BaseModel, Field
    from typing import List as TypingList
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    logger.warning("Pydantic not available - will use JSON schema instead")


# Nutrition data schemas
if PYDANTIC_AVAILABLE:
    class MineralData(BaseModel):
        """Minerals and trace elements data."""
        food_code: str = Field(description="Food code (e.g., A001, O001)")
        food_name: str = Field(description="Food name")
        calcium_mg: Optional[float] = Field(None, description="Calcium in mg per 100g")
        iron_mg: Optional[float] = Field(None, description="Iron in mg per 100g")
        magnesium_mg: Optional[float] = Field(None, description="Magnesium in mg per 100g")
        phosphorus_mg: Optional[float] = Field(None, description="Phosphorus in mg per 100g")
        potassium_mg: Optional[float] = Field(None, description="Potassium in mg per 100g")
        sodium_mg: Optional[float] = Field(None, description="Sodium in mg per 100g")
        zinc_mg: Optional[float] = Field(None, description="Zinc in mg per 100g")
        selenium_mcg: Optional[float] = Field(None, description="Selenium in mcg per 100g")
        copper_mg: Optional[float] = Field(None, description="Copper in mg per 100g (optional)")
        manganese_mg: Optional[float] = Field(None, description="Manganese in mg per 100g (optional)")
    
    class VitaminData(BaseModel):
        """Vitamins data."""
        food_code: str = Field(description="Food code (e.g., A001, O001)")
        food_name: str = Field(description="Food name")
        vitamin_c_mg: Optional[float] = Field(None, description="Vitamin C (Ascorbic Acid) in mg per 100g")
        folate_mcg: Optional[float] = Field(None, description="Folate (B9) in mcg per 100g")
        thiamine_b1_mg: Optional[float] = Field(None, description="Thiamine (B1) in mg per 100g (optional)")
        riboflavin_b2_mg: Optional[float] = Field(None, description="Riboflavin (B2) in mg per 100g (optional)")
        niacin_b3_mg: Optional[float] = Field(None, description="Niacin (B3) in mg per 100g (optional)")
        pantothenic_acid_b5_mg: Optional[float] = Field(None, description="Pantothenic Acid (B5) in mg per 100g (optional)")
        pyridoxine_b6_mg: Optional[float] = Field(None, description="Pyridoxine (B6) in mg per 100g (optional)")
        biotin_b7_mcg: Optional[float] = Field(None, description="Biotin (B7) in mcg per 100g (optional)")


class PDFNutritionExtractor:
    """LLM-based nutrition data extractor from PDF tables."""
    
    # Alternative models to try if primary model fails (ordered by preference)
    FALLBACK_MODELS = [
        "meta-llama/llama-3.3-70b-instruct:free",  # Free model, good for avoiding rate limits
        "anthropic/claude-3.5-sonnet",  # Very reliable, good for structured output
        "meta-llama/llama-3.1-70b-instruct",  # Good alternative
        "google/gemini-pro-1.5",  # Google's model
        "qwen/qwen-2.5-7b-instruct",  # Smaller Qwen, might have better rate limits
    ]
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, 
                 fallback_models: Optional[List[str]] = None):
        """
        Initialize extractor.
        
        Args:
            api_key: OpenRouter API key (defaults to settings)
            model: Model to use (defaults to FOOD_ENRICHMENT_MODEL)
            fallback_models: List of fallback models to try on rate limit errors
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")
        
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model or settings.FOOD_ENRICHMENT_MODEL
        self.fallback_models = fallback_models or self.FALLBACK_MODELS
        self.current_model = self.model
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://drassistent.com",
                "X-Title": "DrAssistent Nutrition Extraction"
            }
        )
        
        logger.info(f"Initialized extractor with model: {self.current_model}")
        logger.info(f"Fallback models available: {', '.join(self.fallback_models)}")
    
    def extract_from_pdf(self, pdf_path: str, data_type: str, 
                        pages_per_batch: int = 5, start_page: int = 1, 
                        end_page: Optional[int] = None,
                        debug: bool = False, debug_file: str = None,
                        progress_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract nutrition data from PDF.
        
        Args:
            pdf_path: Path to PDF file
            data_type: "vitamins" or "minerals"
            pages_per_batch: Number of pages to process per LLM call
            start_page: Starting page number (1-indexed)
            end_page: Ending page number (None = all pages)
        
        Returns:
            List of extracted nutrition data dictionaries
        """
        # Extract text from PDF pages
        pdf_text = self._extract_pdf_text_pages(pdf_path, start_page, end_page)
        
        if not pdf_text:
            logger.error(f"No text extracted from {pdf_path}")
            return []
        
        total_pages = len(pdf_text)
        logger.info(f"Extracting {data_type} from {total_pages} pages...")
        
        # Load existing progress if progress file exists
        all_extracted = []
        processed_pages = set()
        if progress_file and Path(progress_file).exists():
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)
                    all_extracted = progress_data.get('extracted', [])
                    processed_pages = set(progress_data.get('processed_pages', []))
                    logger.info(f"Loaded {len(all_extracted)} existing records from progress file")
                    logger.info(f"Resuming from page {max(processed_pages) + 1 if processed_pages else start_page}")
            except Exception as e:
                logger.warning(f"Could not load progress file: {e}. Starting fresh.")
                all_extracted = []
                processed_pages = set()
        
        # Process in batches
        for batch_start in range(0, total_pages, pages_per_batch):
            batch_end = min(batch_start + pages_per_batch, total_pages)
            current_page_start = start_page + batch_start
            current_page_end = start_page + batch_end - 1
            
            # Skip this batch if all pages were already processed
            batch_page_numbers = set(range(current_page_start, current_page_end + 1))
            if processed_pages and batch_page_numbers.issubset(processed_pages):
                logger.info(f"Skipping pages {current_page_start} to {current_page_end} (already processed)")
                continue
            
            batch_pages = pdf_text[batch_start:batch_end]
            
            logger.info(f"Processing pages {current_page_start} to {current_page_end}...")
            
            # Combine batch text
            batch_text = "\n\n---PAGE BREAK---\n\n".join([
                f"=== PAGE {current_page_start + i} ===\n{p}"
                for i, p in enumerate(batch_pages)
            ])
            
            # Debug: Save extracted text
            if debug and debug_file:
                with open(debug_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n{'='*80}\n")
                    f.write(f"BATCH: Pages {start_page + batch_start} to {start_page + batch_end - 1}\n")
                    f.write(f"{'='*80}\n")
                    f.write(batch_text[:5000])  # First 5000 chars
                    f.write("\n... (truncated)\n")
            
            # Extract using LLM with retry logic and exponential backoff
            max_retries = 3
            extracted = []
            for attempt in range(max_retries):
                try:
                    extracted = self._extract_with_llm(batch_text, data_type)
                    if extracted:
                        break
                    elif attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        logger.warning(f"  No data extracted, retrying in {wait_time}s (attempt {attempt + 2}/{max_retries})...")
                        time.sleep(wait_time)
                except Exception as e:
                    error_str = str(e)
                    # Check if rate limit error
                    if "429" in error_str or "rate" in error_str.lower():
                        # Exponential backoff for rate limits
                        wait_time = min(60, 5 * (2 ** attempt))  # 5s, 10s, 20s, max 60s
                        logger.warning(f"  Rate limit error, waiting {wait_time}s before retry (attempt {attempt + 1}/{max_retries})...")
                        if attempt < max_retries - 1:
                            time.sleep(wait_time)
                            continue  # Retry with backoff
                        else:
                            logger.error(f"  Rate limit persists after {max_retries} attempts. Consider:")
                            logger.error(f"    1. Wait a few minutes and resume with --start-page {start_page + batch_start}")
                            logger.error(f"    2. Use a different model with --model option")
                            raise
                    else:
                        logger.error(f"  Error in extraction attempt {attempt + 1}: {e}")
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt
                            time.sleep(wait_time)
                        else:
                            extracted = []
                            break
            
            if extracted:
                all_extracted.extend(extracted)
                records_with_values = sum(1 for r in extracted if any(v is not None for k, v in r.items() if k not in ['food_code', 'food_name']))
                logger.info(f"  Extracted {len(extracted)} records ({records_with_values} with values) from this batch")
                
                # Save progress after each successful batch
                if progress_file:
                    current_pages = list(range(current_page_start, current_page_end + 1))
                    processed_pages.update(current_pages)
                    try:
                        progress_data = {
                            'extracted': all_extracted,
                            'processed_pages': sorted(list(processed_pages)),
                            'last_page': start_page + batch_end - 1,
                            'total_extracted': len(all_extracted)
                        }
                        progress_path = Path(progress_file)
                        progress_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(progress_path, 'w', encoding='utf-8') as f:
                            json.dump(progress_data, f, indent=2, ensure_ascii=False)
                        logger.debug(f"  Progress saved: {len(all_extracted)} records, pages up to {current_page_end}")
                    except Exception as e:
                        logger.warning(f"  Could not save progress: {e}")
            else:
                logger.warning(f"  No records extracted from pages {current_page_start} to {current_page_end}")
            
            # Rate limiting
            if batch_end < total_pages:
                time.sleep(1.5)  # Slightly longer delay between batches
        
        logger.info(f"Total extracted: {len(all_extracted)} records")
        return all_extracted
    
    def _extract_pdf_text_pages(self, pdf_path: str, start_page: int = 1, 
                                end_page: Optional[int] = None) -> List[str]:
        """Extract text from each PDF page with better table handling."""
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("pdfplumber not installed. Run: pip install pdfplumber")
        
        pages_text = []
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            actual_end = end_page if end_page else total_pages
            
            logger.info(f"Reading pages {start_page} to {actual_end} from {pdf_path}")
            
            for page_num in range(start_page - 1, min(actual_end, total_pages)):
                page = pdf.pages[page_num]
                
                # Try multiple extraction strategies
                best_text = None
                
                # Strategy 1: Extract tables with better settings
                try:
                    tables = page.extract_tables(
                        table_settings={
                            "vertical_strategy": "lines_strict",
                            "horizontal_strategy": "lines_strict",
                            "snap_tolerance": 5,
                            "join_tolerance": 3,
                            "edge_tolerance": 3,
                            "min_words_vertical": 1,
                            "min_words_horizontal": 1,
                        }
                    )
                    if tables and any(len(t) > 1 for t in tables):
                        table_text = self._tables_to_text(tables)
                        if len(table_text) > 100:  # Ensure we got meaningful data
                            best_text = table_text
                except Exception as e:
                    logger.debug(f"Table extraction failed for page {page_num + 1}: {e}")
                
                # Strategy 2: If table extraction failed, use plain text
                if not best_text:
                    text = page.extract_text()
                    if text and len(text) > 50:
                        best_text = text
                
                if best_text:
                    pages_text.append(best_text)
                    logger.debug(f"Page {page_num + 1}: Extracted {len(best_text)} characters")
                else:
                    logger.warning(f"Page {page_num + 1}: No text extracted")
        
        logger.info(f"Extracted text from {len(pages_text)} pages")
        return pages_text
    
    def _tables_to_text(self, tables: List) -> str:
        """Convert extracted tables to structured text format."""
        text_parts = []
        for table_idx, table in enumerate(tables):
            if not table or len(table) < 2:  # Need at least header + 1 data row
                continue
            
            # Convert table to readable text with clear column separation
            for row_idx, row in enumerate(table):
                if row:
                    # Clean and format row
                    cleaned_row = []
                    for cell in row:
                        if cell is None:
                            cleaned_row.append("")
                        else:
                            cell_str = str(cell).strip()
                            # Remove excessive whitespace
                            cell_str = " ".join(cell_str.split())
                            cleaned_row.append(cell_str)
                    
                    # Join with tabs for column alignment
                    row_text = "\t".join(cleaned_row)
                    if row_text.strip():  # Skip completely empty rows
                        text_parts.append(row_text)
            
            # Add separator between tables
            if table_idx < len(tables) - 1:
                text_parts.append("")  # Empty line between tables
        
        return "\n".join(text_parts)
    
    def _extract_with_llm(self, text: str, data_type: str) -> List[Dict[str, Any]]:
        """Extract structured data using LLM."""
        
        # Build prompt
        if data_type == "minerals":
            schema_description = """
Extract minerals and trace elements data. Each record should have:
- food_code: Food code (e.g., A001, O001, E001)
- food_name: Food name
- calcium_mg: Calcium in mg per 100g (or null if not available)
- iron_mg: Iron in mg per 100g (or null)
- magnesium_mg: Magnesium in mg per 100g (or null)
- phosphorus_mg: Phosphorus in mg per 100g (or null)
- potassium_mg: Potassium in mg per 100g (or null)
- sodium_mg: Sodium in mg per 100g (or null)
- zinc_mg: Zinc in mg per 100g (or null)
- selenium_mcg: Selenium in mcg per 100g (or null)
- copper_mg: Copper in mg per 100g (optional, or null)
- manganese_mg: Manganese in mg per 100g (optional, or null)

Handle values with ± symbols by extracting the main value (first number).
Blank cells or "below detectable limit" should be null.
"""
            example = {
                "food_code": "A001",
                "food_name": "Amaranth seed, black",
                "calcium_mg": 181.0,
                "iron_mg": 9.33,
                "magnesium_mg": None,
                "phosphorus_mg": None,
                "potassium_mg": None,
                "sodium_mg": None,
                "zinc_mg": None,
                "selenium_mcg": None,
                "copper_mg": 0.81,
                "manganese_mg": None
            }
        
        else:  # vitamins
            schema_description = """
Extract vitamins data. Each record should have:
- food_code: Food code (e.g., A001, O001, E001)
- food_name: Food name
- vitamin_c_mg: Vitamin C (Ascorbic Acid) in mg per 100g (or null)
- folate_mcg: Folate (B9) in mcg per 100g (or null)
- thiamine_b1_mg: Thiamine (B1) in mg per 100g (optional, or null)
- riboflavin_b2_mg: Riboflavin (B2) in mg per 100g (optional, or null)
- niacin_b3_mg: Niacin (B3) in mg per 100g (optional, or null)
- pantothenic_acid_b5_mg: Pantothenic Acid (B5) in mg per 100g (optional, or null)
- pyridoxine_b6_mg: Pyridoxine (B6) in mg per 100g (optional, or null)
- biotin_b7_mcg: Biotin (B7) in mcg per 100g (optional, or null)

Handle values with ± symbols by extracting the main value (first number).
Blank cells should be null.
"""
            example = {
                "food_code": "A001",
                "food_name": "Amaranth seed, black",
                "vitamin_c_mg": None,
                "folate_mcg": None,
                "thiamine_b1_mg": 0.05,
                "riboflavin_b2_mg": 0.12,
                "niacin_b3_mg": 1.2,
                "pantothenic_acid_b5_mg": None,
                "pyridoxine_b6_mg": None,
                "biotin_b7_mcg": None
            }
        
        prompt = f"""You are a nutrition data extraction expert. Extract structured {data_type} data from the following IFCT (Indian Food Composition Table) PDF text.

{schema_description}

IMPORTANT: The table below contains actual nutrition values. Extract them as NUMBERS, not nulls!

Example format (SHOWING REAL VALUES - note the numbers!):
{json.dumps(example, indent=2)}

CRITICAL EXTRACTION RULES:
1. Extract ALL food entries visible in the table below (should be many entries, not just a few)
2. For EACH food entry, you MUST extract the food_code AND the {data_type} VALUES from the table
3. VALUES ARE IN THE TABLE - look for numeric columns after the food_code and food_name
4. DO NOT return all nulls - if you see numbers in the table columns, extract them as numbers (float/integer)
5. Handle ± symbols: "20.33±0.50" → extract 20.33 (first number before ±)
6. Handle ranges: "5-10" → extract 7.5 (midpoint) or first number
7. Only use null if: cell is empty, blank, "-", "N/A", or "below detectable limit"
8. Food codes format: letter + 3 digits (A001, B005, O001, E023, S010, etc.)
9. Extract at least 10-20 entries per page if available

The table structure typically has:
- Column 1: Food code (A001, B002, etc.)
- Column 2: Food name
- Columns 3+: {data_type} values in the specified units

PDF Text (Table Data - LOOK FOR THE VALUES IN THESE COLUMNS):
{text[:25000]}

EXTRACT ALL visible food entries with their {data_type} values. Return ONLY a valid JSON array:
- Array must start with [ and end with ]
- Each object has food_code, food_name, and {data_type} fields
- Extract NUMBERS for values that exist in the table
- Include as many entries as you can see in the table

Return ONLY the JSON array, nothing else.
"""
        
        # Try with current model, fallback to alternatives on rate limit
        models_to_try = [self.current_model] + self.fallback_models
        last_error = None
        response = None
        
        for model_attempt in models_to_try:
            try:
                # Use lower temperature for more consistent extraction
                # Increase max_tokens to handle more records per batch
                response = self.client.chat.completions.create(
                    model=model_attempt,
                    messages=[
                        {
                            "role": "system",
                            "content": """You are a precise data extraction assistant specializing in nutrition tables. 
Your task is to extract ALL food entries with their vitamin/mineral values from IFCT table data.
CRITICAL: Extract actual numeric values from the table - do NOT return all nulls.
Return only valid JSON arrays with complete data."""
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0,  # Zero temperature for maximum consistency
                    max_tokens=12000  # Increased for more records
                )
                
                # Success - update current model if we switched
                if model_attempt != self.current_model:
                    logger.info(f"Successfully using fallback model: {model_attempt}")
                    self.current_model = model_attempt
                
                break  # Success, exit loop
                
            except Exception as e:
                error_str = str(e)
                last_error = e
                
                # Check if it's a rate limit error
                if "429" in error_str or "rate" in error_str.lower() or "rate limit" in error_str.lower():
                    logger.warning(f"Rate limit error with {model_attempt}")
                    if model_attempt != models_to_try[-1]:  # Not the last model
                        next_model_idx = models_to_try.index(model_attempt) + 1
                        logger.info(f"Trying fallback model: {models_to_try[next_model_idx]}")
                        time.sleep(2)  # Brief pause before trying next model
                        continue  # Try next model
                    else:
                        # All models rate limited - raise with retry info
                        raise Exception(f"All models rate limited. Last error: {error_str}")
                else:
                    # Non-rate-limit error - raise immediately
                    raise
        
        if not response:
            if last_error:
                raise last_error
            else:
                raise Exception("Failed to get response from any model")
        
        content = response.choices[0].message.content
        
        # Parse JSON - handle various formats
        try:
            # Remove markdown code blocks if present
            content_clean = content.strip()
            if content_clean.startswith("```"):
                # Extract content between code blocks
                lines = content_clean.split("\n")
                content_clean = "\n".join(lines[1:-1]) if len(lines) > 2 else content_clean
                if content_clean.startswith("json"):
                    content_clean = "\n".join(lines[2:-1]) if len(lines) > 3 else content_clean
            
            # Try to extract JSON array
            data = None
            
            # Case 1: Direct JSON array
            if content_clean.strip().startswith("["):
                data = json.loads(content_clean)
            
            # Case 2: JSON array somewhere in text
            elif "[" in content_clean and "]" in content_clean:
                start = content_clean.find("[")
                end = content_clean.rfind("]") + 1
                try:
                    data = json.loads(content_clean[start:end])
                except:
                    pass
            
            # Case 3: JSON object with array
            if data is None:
                parsed = json.loads(content_clean)
                if isinstance(parsed, list):
                    data = parsed
                elif isinstance(parsed, dict):
                    # Try common keys
                    for key in ["data", "items", "records", "results", "extracted"]:
                        if key in parsed and isinstance(parsed[key], list):
                            data = parsed[key]
                            break
                    
                    # If no array found, check if keys are food codes
                    if data is None:
                        keys = list(parsed.keys())
                        if keys and all(isinstance(k, str) and len(k) >= 3 and k[0].isalpha() and k[1:].isdigit() for k in keys[:5]):
                            # Keys look like food codes, treat as dict of records
                            data = list(parsed.values())
                        else:
                            # Single record
                            data = [parsed]
            
            if data is None:
                logger.warning("Could not parse JSON from LLM response")
                logger.debug(f"Response: {content_clean[:500]}")
                return []
            
            # Validate and clean
            validated = []
            for item in data:
                if isinstance(item, dict):
                    cleaned = self._clean_extracted_item(item, data_type)
                    if cleaned:
                        # Skip records that have no actual values (all nulls except food_code/name)
                        has_values = any(
                            v is not None 
                            for k, v in cleaned.items() 
                            if k not in ['food_code', 'food_name']
                        )
                        if has_values or len(validated) < 10:  # Keep first 10 even if null for debugging
                            validated.append(cleaned)
                        else:
                            logger.debug(f"Skipping record with all nulls: {cleaned.get('food_code')}")
            
            logger.info(f"Validated {len(validated)} records from batch (skipped {len(data) - len(validated)} with all nulls)")
            return validated
                
        except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {e}")
                logger.debug(f"Response content (first 1000 chars): {content[:1000]}")
                
                # Try to fix common JSON issues and retry parsing
                try:
                    # Try to fix unquoted keys or trailing commas
                    content_fixed = content.strip()
                    # Remove trailing commas before closing brackets
                    import re
                    content_fixed = re.sub(r',\s*}', '}', content_fixed)
                    content_fixed = re.sub(r',\s*]', ']', content_fixed)
                    # Try parsing again
                    if content_fixed.strip().startswith("["):
                        data = json.loads(content_fixed)
                        validated = []
                        for item in data:
                            if isinstance(item, dict):
                                cleaned = self._clean_extracted_item(item, data_type)
                                if cleaned:
                                    has_values = any(v is not None for k, v in cleaned.items() if k not in ['food_code', 'food_name'])
                                    if has_values:
                                        validated.append(cleaned)
                        logger.info(f"Fixed JSON and extracted {len(validated)} records")
                        return validated
                except:
                    pass
                
                # Last resort: try to extract partial JSON
                logger.warning("Could not parse JSON even after fixing attempts")
                return []
        
        except Exception as e:
            logger.error(f"Error extracting with LLM: {e}", exc_info=True)
            return []
    
    def _clean_extracted_item(self, item: Dict[str, Any], data_type: str) -> Optional[Dict[str, Any]]:
        """Clean and validate extracted item."""
        if not isinstance(item, dict):
            return None
        
        # Validate food_code
        food_code = item.get("food_code") or item.get("foodCode") or item.get("code")
        if not food_code:
            return None
        
        food_code = str(food_code).strip().upper()
        
        # Validate food_code format (should be like A001, O001, etc.)
        if not (len(food_code) >= 3 and food_code[0].isalpha() and food_code[1:].isdigit()):
            logger.debug(f"Invalid food_code format: {food_code}")
            return None
        
        # Build cleaned item
        cleaned = {
            "food_code": food_code,
            "food_name": str(item.get("food_name") or item.get("foodName") or item.get("name") or "").strip()
        }
        
        # Clean numeric values
        if data_type == "minerals":
            numeric_fields = [
                "calcium_mg", "iron_mg", "magnesium_mg", "phosphorus_mg",
                "potassium_mg", "sodium_mg", "zinc_mg", "selenium_mcg",
                "copper_mg", "manganese_mg"
            ]
        else:  # vitamins
            numeric_fields = [
                "vitamin_c_mg", "folate_mcg", "thiamine_b1_mg", "riboflavin_b2_mg",
                "niacin_b3_mg", "pantothenic_acid_b5_mg", "pyridoxine_b6_mg", "biotin_b7_mcg"
            ]
        
        for field in numeric_fields:
            # Try different field name variations
            value = (item.get(field) or 
                    item.get(field.replace("_", "")) or
                    item.get(field.title().replace("_", "")))
            
            if value is None or value == "" or str(value).lower() in ["null", "none", "na", "n/a", "-"]:
                cleaned[field] = None
            else:
                try:
                    # Handle strings with ± or other symbols
                    if isinstance(value, str):
                        # Extract first number before ± or other non-numeric chars
                        import re
                        match = re.match(r'^([\d.]+)', str(value).strip())
                        if match:
                            value = float(match.group(1))
                        else:
                            cleaned[field] = None
                            continue
                    
                    # Convert to float
                    float_value = float(value)
                    cleaned[field] = float_value if float_value >= 0 else None
                except (ValueError, TypeError):
                    cleaned[field] = None
        
        return cleaned


def merge_extracted_data(extracted_list: List[Dict[str, Any]], 
                        output_file: str, deduplicate: bool = True):
    """
    Merge and save extracted data.
    
    Args:
        extracted_list: List of extracted records
        output_file: Output JSON file path
        deduplicate: Whether to deduplicate by food_code
    """
    if deduplicate:
        # Deduplicate by food_code (keep last occurrence)
        seen_codes = {}
        for item in extracted_list:
            code = item.get("food_code")
            if code:
                seen_codes[code] = item
        
        merged = list(seen_codes.values())
        logger.info(f"Deduplicated: {len(extracted_list)} -> {len(merged)} records")
    else:
        merged = extracted_list
    
    # Sort by food_code
    merged.sort(key=lambda x: (x.get("food_code", "")))
    
    # Save to file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(merged)} records to {output_file}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Extract nutrition data (vitamins/minerals) from IFCT PDFs using LLM'
    )
    parser.add_argument(
        '--pdf',
        type=str,
        required=True,
        help='Path to PDF file (table2.pdf or table3.pdf)'
    )
    parser.add_argument(
        '--type',
        type=str,
        choices=['vitamins', 'minerals'],
        required=True,
        help='Type of data to extract'
    )
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Output JSON file path'
    )
    parser.add_argument(
        '--pages-per-batch',
        type=int,
        default=5,
        help='Number of pages to process per LLM call (default: 5)'
    )
    parser.add_argument(
        '--start-page',
        type=int,
        default=1,
        help='Starting page number (1-indexed, default: 1)'
    )
    parser.add_argument(
        '--end-page',
        type=int,
        help='Ending page number (default: all pages)'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        help='OpenRouter API key (defaults to settings)'
    )
    parser.add_argument(
        '--model',
        type=str,
        help='Model to use (defaults to FOOD_ENRICHMENT_MODEL)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Save extracted text to file for debugging'
    )
    parser.add_argument(
        '--debug-text-file',
        type=str,
        default='extracted_text_debug.txt',
        help='File to save debug text (default: extracted_text_debug.txt)'
    )
    parser.add_argument(
        '--resume-from',
        type=int,
        help='Manually resume extraction from this page number (auto-resume from progress file is enabled by default)'
    )
    parser.add_argument(
        '--fallback-models',
        nargs='+',
        help='Fallback models to try on rate limit errors (default: claude-3.5-sonnet, llama-3.1-70b, etc.)'
    )
    
    args = parser.parse_args()
    
    # Validate PDF file
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        logger.error(f"PDF file not found: {pdf_path}")
        return 1
    
    logger.info("=" * 70)
    logger.info(f"EXTRACTING {args.type.upper()} FROM PDF")
    logger.info("=" * 70)
    logger.info(f"PDF: {pdf_path}")
    logger.info(f"Type: {args.type}")
    logger.info(f"Output: {args.output}")
    logger.info(f"Pages per batch: {args.pages_per_batch}")
    
    # Set up progress file (auto-save/auto-resume)
    progress_file = str(Path(args.output).with_suffix('.progress.json'))
    logger.info(f"Progress file: {progress_file}")
    
    # Auto-resume: Check if output or progress file exists
    output_path = Path(args.output)
    progress_path = Path(progress_file)
    if output_path.exists() or progress_path.exists():
        logger.info("Found existing progress/output file. Will auto-resume/merge.")
    
    logger.info("=" * 70)
    
    # Initialize extractor
    extractor = PDFNutritionExtractor(api_key=args.api_key, model=args.model)
    if args.fallback_models:
        extractor.fallback_models = args.fallback_models
    
    # Clear debug file if exists
    if args.debug and args.debug_text_file:
        debug_path = Path(args.debug_text_file)
        if debug_path.exists():
            debug_path.unlink()
        logger.info(f"Debug mode: extracted text will be saved to {args.debug_text_file}")
    
    # Handle resume from specific page if requested
    start_page = args.start_page
    if args.resume_from:
        start_page = args.resume_from
        logger.info(f"Resuming from page {start_page} (requested)")
    
    # Load existing output if it exists for merging
    existing_data = []
    if output_path.exists():
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            logger.info(f"Found existing output with {len(existing_data)} records. Will merge with new extraction.")
        except Exception as e:
            logger.warning(f"Could not load existing output: {e}")
    
    # Extract data
    extracted = extractor.extract_from_pdf(
        str(pdf_path),
        args.type,
        pages_per_batch=args.pages_per_batch,
        start_page=start_page,
        end_page=args.end_page,
        debug=args.debug,
        debug_file=args.debug_text_file if args.debug else None,
        progress_file=progress_file
    )
    
    # Merge with existing data if we had any
    if existing_data:
        # Create lookup by food_code
        existing_by_code = {item.get('food_code'): item for item in existing_data}
        # Update with new data (new takes precedence)
        for item in extracted:
            code = item.get('food_code')
            if code:
                existing_by_code[code] = item
        # Combine all
        all_data = list(existing_by_code.values())
        logger.info(f"Merged: {len(existing_data)} existing + {len(extracted)} new = {len(all_data)} total")
        extracted = all_data
    
    if not extracted:
        logger.warning("No data extracted!")
        return 1
    
    # Merge and save
    merge_extracted_data(extracted, args.output)
    
    # Clean up progress file after successful completion
    if progress_path.exists():
        try:
            progress_path.unlink()
            logger.info("Progress file cleaned up (extraction complete)")
        except Exception as e:
            logger.warning(f"Could not delete progress file: {e}")
    
    logger.info("=" * 70)
    logger.info("EXTRACTION COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Saved {len(extracted)} records to {args.output}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

