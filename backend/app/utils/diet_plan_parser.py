"""
AI Diet Plan Response Parser

Parses the AI agent's text response and extracts structured meal data
that can be saved to the database.
"""
import re
from typing import Dict, List, Optional, Any
from app.utils.logger import logger


class DietPlanParser:
    """
    Parser for extracting structured meal data from AI-generated diet plans.
    
    The AI agent generates diet plans in a semi-structured text format.
    This parser extracts:
    - Day number
    - Meal time
    - Meal type
    - Food/dish name
    - Portion size
    - Healing purpose
    - Dosha notes
    - Nutritional values (calories, protein, carbs, fat)
    """
    
    # Meal type mappings
    MEAL_TYPES = [
        "Morning Cleanse",
        "Breakfast",
        "Mid Snack", 
        "Mid-Morning Snack",
        "Lunch",
        "Evening Snack",
        "Dinner",
        "Sleep Tonic",
        "Bedtime Tonic"
    ]
    
    # Standard meal times
    MEAL_TIME_DEFAULTS = {
        "Morning Cleanse": "6:30 AM",
        "Breakfast": "8:30 AM",
        "Mid Snack": "11:00 AM",
        "Mid-Morning Snack": "11:00 AM",
        "Lunch": "1:30 PM",
        "Evening Snack": "4:30 PM",
        "Dinner": "7:00 PM",
        "Sleep Tonic": "9:00 PM",
        "Bedtime Tonic": "9:00 PM"
    }
    
    def __init__(self):
        self.current_day = 1
        self.order_in_day = 0
    
    def parse_diet_plan(self, ai_response: str) -> Dict[str, Any]:
        """
        Parse the AI agent's response and extract meal data.
        
        Args:
            ai_response: The text response from the AI agent containing the meal plan
        
        Returns:
            Dict with plan metadata and list of parsed meals
        """
        logger.info("Parsing AI-generated diet plan response")
        logger.info(f"AI Response length: {len(ai_response)} characters")
        logger.info(f"AI Response preview (first 500 chars): {ai_response[:500]}")
        
        meals = []
        lines = ai_response.split('\n')
        
        # Try different parsing strategies
        meals = self._parse_structured_format(ai_response)
        logger.info(f"Structured format parsing found {len(meals)} meals")
        
        if not meals:
            meals = self._parse_day_sections(ai_response)
            logger.info(f"Day sections parsing found {len(meals)} meals")
        
        if not meals:
            meals = self._parse_meal_blocks(ai_response)
            logger.info(f"Meal blocks parsing found {len(meals)} meals")
        
        logger.info(f"Parsed {len(meals)} meals from AI response")
        
        # Extract nutritional summary if present
        nutritional_summary = self._extract_nutritional_summary(ai_response)
        
        return {
            "meals": meals,
            "nutritional_summary": nutritional_summary,
            "total_meals": len(meals)
        }
    
    def _parse_structured_format(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse structured format where each meal is clearly delineated.
        
        Expected format:
        Day 1:
        - Morning Cleanse (6:30 AM): Warm Lemon Water
          Portion: 1 glass
          Healing Purpose: Detoxifies, aids digestion
          Calories: 5, Protein: 0g, Carbs: 1g, Fat: 0g
        """
        meals = []
        current_day = None
        current_meal = {}
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for day marker
            day_match = re.match(r'^Day\s+(\d+)', line, re.IGNORECASE)
            if day_match:
                current_day = int(day_match.group(1))
                self.order_in_day = 0
                continue
            
            # Check for meal header
            meal_header_match = re.match(
                r'^[-•*]\s*(.+?)\s*\((.+?)\)\s*:\s*(.+)',
                line
            )
            
            if meal_header_match:
                # Save previous meal if exists
                if current_meal and current_day:
                    current_meal['day_number'] = current_day
                    current_meal['order_in_day'] = self.order_in_day
                    meals.append(current_meal)
                    self.order_in_day += 1
                
                # Start new meal
                meal_type = meal_header_match.group(1).strip()
                meal_time = meal_header_match.group(2).strip()
                food_dish = meal_header_match.group(3).strip()
                
                current_meal = {
                    'meal_type': meal_type,
                    'meal_time': meal_time,
                    'food_dish': food_dish,
                    'healing_purpose': None,
                    'portion': None,
                    'dosha_notes': None,
                    'notes': None,
                    'calories': None,
                    'protein_g': None,
                    'carbs_g': None,
                    'fat_g': None
                }
                continue
            
            # Parse meal details
            if current_meal:
                # Portion
                portion_match = re.search(r'Portion\s*:\s*(.+)', line, re.IGNORECASE)
                if portion_match:
                    current_meal['portion'] = portion_match.group(1).strip()
                    continue
                
                # Healing purpose
                healing_match = re.search(r'Healing\s*Purpose\s*:\s*(.+)', line, re.IGNORECASE)
                if healing_match:
                    current_meal['healing_purpose'] = healing_match.group(1).strip()
                    continue
                
                # Dosha notes
                dosha_match = re.search(r'Dosha\s*(?:Notes|Impact|Balance)?\s*:\s*(.+)', line, re.IGNORECASE)
                if dosha_match:
                    current_meal['dosha_notes'] = dosha_match.group(1).strip()
                    continue
                
                # Notes
                notes_match = re.search(r'Notes?\s*:\s*(.+)', line, re.IGNORECASE)
                if notes_match and not current_meal['notes']:
                    current_meal['notes'] = notes_match.group(1).strip()
                    continue
                
                # Nutritional values
                nutrition_match = re.search(
                    r'Calories?\s*:\s*(\d+\.?\d*).*?Protein\s*:\s*(\d+\.?\d*)\s*g.*?Carbs?\s*:\s*(\d+\.?\d*)\s*g.*?Fat\s*:\s*(\d+\.?\d*)\s*g',
                    line,
                    re.IGNORECASE
                )
                if nutrition_match:
                    current_meal['calories'] = float(nutrition_match.group(1))
                    current_meal['protein_g'] = float(nutrition_match.group(2))
                    current_meal['carbs_g'] = float(nutrition_match.group(3))
                    current_meal['fat_g'] = float(nutrition_match.group(4))
                    continue
        
        # Add last meal
        if current_meal and current_day:
            current_meal['day_number'] = current_day
            current_meal['order_in_day'] = self.order_in_day
            meals.append(current_meal)
        
        return meals
    
    def _parse_day_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse format where text is organized by day sections.
        """
        meals = []
        
        # Split by day markers
        day_pattern = r'Day\s+(\d+)'
        day_splits = re.split(day_pattern, text, flags=re.IGNORECASE)
        
        # First element is text before any day marker (skip it)
        for i in range(1, len(day_splits), 2):
            day_number = int(day_splits[i])
            day_content = day_splits[i + 1] if i + 1 < len(day_splits) else ""
            
            day_meals = self._extract_meals_from_text(day_content, day_number)
            meals.extend(day_meals)
        
        return meals
    
    def _parse_meal_blocks(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse format where each meal is a block of text with multiple lines.
        """
        meals = []
        current_day = 1
        order = 0
        
        # Look for meal type patterns
        for meal_type in self.MEAL_TYPES:
            pattern = rf'(?:^|\n)\s*(?:\*\*)?{re.escape(meal_type)}(?:\*\*)?\s*[:\-]?\s*(.+?)(?=\n\n|\n(?:\*\*)?(?:{"|".join([re.escape(mt) for mt in self.MEAL_TYPES])})|$)'
            
            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
            
            for match in matches:
                meal_content = match.group(1).strip()
                meal = self._parse_meal_content(meal_content, meal_type, current_day, order)
                if meal:
                    meals.append(meal)
                    order += 1
        
        return meals
    
    def _extract_meals_from_text(self, text: str, day_number: int) -> List[Dict[str, Any]]:
        """
        Extract individual meals from a day's text content.
        """
        meals = []
        order = 0
        
        for meal_type in self.MEAL_TYPES:
            # Look for this meal type in the text
            pattern = rf'{re.escape(meal_type)}\s*[:\-]?\s*(.+?)(?=(?:{"|".join([re.escape(mt) for mt in self.MEAL_TYPES])})|$)'
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            
            if match:
                meal_content = match.group(1).strip()
                meal = self._parse_meal_content(meal_content, meal_type, day_number, order)
                if meal:
                    meals.append(meal)
                    order += 1
        
        return meals
    
    def _parse_meal_content(self, content: str, meal_type: str, day_number: int, order: int) -> Optional[Dict[str, Any]]:
        """
        Parse individual meal content to extract details.
        """
        # Extract food dish (usually first line or after time)
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        if not lines:
            return None
        
        food_dish = lines[0]
        
        # Clean up food dish (remove time if present)
        food_dish = re.sub(r'\(?\d{1,2}:\d{2}\s*(?:AM|PM)?\)?', '', food_dish).strip()
        food_dish = re.sub(r'^[-•*:\s]+', '', food_dish).strip()
        
        if not food_dish:
            return None
        
        meal = {
            'day_number': day_number,
            'meal_type': meal_type,
            'meal_time': self.MEAL_TIME_DEFAULTS.get(meal_type, "12:00 PM"),
            'food_dish': food_dish,
            'order_in_day': order,
            'healing_purpose': None,
            'portion': None,
            'dosha_notes': None,
            'notes': None,
            'calories': None,
            'protein_g': None,
            'carbs_g': None,
            'fat_g': None
        }
        
        # Extract other details from remaining lines
        full_content = ' '.join(lines)
        
        # Portion
        portion_match = re.search(r'(?:Portion|Serving)\s*:\s*([^,\n]+)', full_content, re.IGNORECASE)
        if portion_match:
            meal['portion'] = portion_match.group(1).strip()
        
        # Healing purpose
        healing_match = re.search(r'(?:Healing Purpose|Benefits?|Why)\s*:\s*([^,\n]+)', full_content, re.IGNORECASE)
        if healing_match:
            meal['healing_purpose'] = healing_match.group(1).strip()
        
        # Dosha notes
        dosha_match = re.search(r'Dosha\s*(?:Notes?|Impact|Balance)?\s*:\s*([^,\n]+)', full_content, re.IGNORECASE)
        if dosha_match:
            meal['dosha_notes'] = dosha_match.group(1).strip()
        
        # Nutritional values
        cal_match = re.search(r'(\d+\.?\d*)\s*(?:kcal|calories?)', full_content, re.IGNORECASE)
        if cal_match:
            meal['calories'] = float(cal_match.group(1))
        
        protein_match = re.search(r'(\d+\.?\d*)\s*g?\s*protein', full_content, re.IGNORECASE)
        if protein_match:
            meal['protein_g'] = float(protein_match.group(1))
        
        carbs_match = re.search(r'(\d+\.?\d*)\s*g?\s*carbs?', full_content, re.IGNORECASE)
        if carbs_match:
            meal['carbs_g'] = float(carbs_match.group(1))
        
        fat_match = re.search(r'(\d+\.?\d*)\s*g?\s*fat', full_content, re.IGNORECASE)
        if fat_match:
            meal['fat_g'] = float(fat_match.group(1))
        
        return meal
    
    def _extract_nutritional_summary(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract nutritional summary from the response.
        """
        summary = {}
        
        # Look for daily targets
        target_match = re.search(
            r'(?:Daily\s+)?Target\s*:\s*(\d+\.?\d*)\s*(?:kcal|calories)',
            text,
            re.IGNORECASE
        )
        if target_match:
            summary['target_calories'] = float(target_match.group(1))
        
        # Look for protein target
        protein_target = re.search(r'Protein\s*Target\s*:\s*(\d+\.?\d*)\s*g', text, re.IGNORECASE)
        if protein_target:
            summary['target_protein_g'] = float(protein_target.group(1))
        
        # Look for carbs target
        carbs_target = re.search(r'Carbs?\s*Target\s*:\s*(\d+\.?\d*)\s*g', text, re.IGNORECASE)
        if carbs_target:
            summary['target_carbs_g'] = float(carbs_target.group(1))
        
        # Look for fat target
        fat_target = re.search(r'Fat\s*Target\s*:\s*(\d+\.?\d*)\s*g', text, re.IGNORECASE)
        if fat_target:
            summary['target_fat_g'] = float(fat_target.group(1))
        
        return summary if summary else None
    
    def validate_meals(self, meals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate parsed meals for completeness and consistency.
        
        Returns:
            Dict with validation results and any warnings/errors
        """
        errors = []
        warnings = []
        
        if not meals:
            errors.append("No meals were parsed from the response")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # Check required fields
        for i, meal in enumerate(meals):
            if not meal.get('food_dish'):
                errors.append(f"Meal {i+1}: Missing food/dish name")
            
            if not meal.get('meal_type'):
                warnings.append(f"Meal {i+1}: Missing meal type")
            
            if not meal.get('day_number'):
                warnings.append(f"Meal {i+1}: Missing day number")
        
        # Check day coverage
        days_present = set(m['day_number'] for m in meals if m.get('day_number'))
        if days_present:
            max_day = max(days_present)
            missing_days = set(range(1, max_day + 1)) - days_present
            if missing_days:
                warnings.append(f"Missing meals for days: {sorted(missing_days)}")
        
        # Check nutritional data
        meals_with_nutrition = sum(1 for m in meals if m.get('calories'))
        if meals_with_nutrition < len(meals) * 0.8:
            warnings.append(f"Only {meals_with_nutrition}/{len(meals)} meals have nutritional data")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "total_meals": len(meals),
            "days_covered": len(days_present) if days_present else 0
        }

