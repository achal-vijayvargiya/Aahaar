"""
Validation utilities for MealStructureEngine.
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import re


def validate_time_format(time_str: str) -> bool:
    """
    Validate time format is HH:MM (24-hour format).
    
    Args:
        time_str: Time string to validate
        
    Returns:
        True if valid, False otherwise
    """
    return bool(re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', time_str))


def parse_time(time_str: str) -> datetime:
    """
    Parse time string (HH:MM) to datetime object (using today's date).
    
    Args:
        time_str: Time string in HH:MM format
        
    Returns:
        datetime object with today's date and parsed time
        
    Raises:
        ValueError: If time format is invalid
    """
    if not validate_time_format(time_str):
        raise ValueError(f'Invalid time format: {time_str}. Expected HH:MM (24-hour)')
    
    hour, minute = map(int, time_str.split(':'))
    today = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    return today


def add_minutes(time_obj: datetime, minutes: int) -> datetime:
    """
    Add minutes to a datetime object.
    
    Args:
        time_obj: datetime object
        minutes: Number of minutes to add (can be negative)
        
    Returns:
        New datetime object
    """
    return time_obj + timedelta(minutes=minutes)


def add_hours(time_obj: datetime, hours: int) -> datetime:
    """
    Add hours to a datetime object.
    
    Args:
        time_obj: datetime object
        hours: Number of hours to add (can be negative)
        
    Returns:
        New datetime object
    """
    return time_obj + timedelta(hours=hours)


def validate_calorie_totals(
    calorie_split: Dict[str, float],
    target_calories: float,
    tolerance_pct: float = 5.0
) -> Tuple[bool, float]:
    """
    Validate that calorie split totals are within tolerance of target.
    
    Args:
        calorie_split: Dictionary of meal names to calorie values
        target_calories: Target total calories
        tolerance_pct: Maximum allowed difference percentage (default 5%)
        
    Returns:
        Tuple of (is_valid, difference_percentage)
    """
    total = sum(calorie_split.values())
    diff_pct = abs(total - target_calories) / target_calories * 100
    is_valid = diff_pct <= tolerance_pct
    return is_valid, diff_pct


def validate_protein_sufficiency(
    protein_split: Dict[str, float],
    target_protein_g: float,
    min_sufficiency_pct: float = 95.0
) -> Tuple[bool, float]:
    """
    Validate that protein split meets minimum sufficiency threshold.
    
    Args:
        protein_split: Dictionary of meal names to protein values (grams)
        target_protein_g: Target total protein in grams
        min_sufficiency_pct: Minimum percentage of target that must be met (default 95%)
        
    Returns:
        Tuple of (is_sufficient, actual_percentage)
    """
    total = sum(protein_split.values())
    actual_pct = (total / target_protein_g * 100) if target_protein_g > 0 else 0
    is_sufficient = actual_pct >= min_sufficiency_pct
    return is_sufficient, actual_pct


def detect_timing_overlaps(timing_windows: Dict[str, List[str]]) -> List[Tuple[str, str]]:
    """
    Detect overlapping timing windows between meals.
    
    Args:
        timing_windows: Dictionary of meal names to [start_time, end_time] lists
        
    Returns:
        List of tuples (meal1, meal2) indicating overlapping meals
    """
    overlaps = []
    meals = list(timing_windows.keys())
    
    for i, meal1 in enumerate(meals):
        if meal1 not in timing_windows or len(timing_windows[meal1]) != 2:
            continue
        
        start1 = parse_time(timing_windows[meal1][0])
        end1 = parse_time(timing_windows[meal1][1])
        
        # Handle case where end time is next day (e.g., sleep time)
        if end1 < start1:
            end1 = end1 + timedelta(days=1)
        
        for meal2 in meals[i+1:]:
            if meal2 not in timing_windows or len(timing_windows[meal2]) != 2:
                continue
            
            start2 = parse_time(timing_windows[meal2][0])
            end2 = parse_time(timing_windows[meal2][1])
            
            # Handle case where end time is next day
            if end2 < start2:
                end2 = end2 + timedelta(days=1)
            
            # Check for overlap
            if not (end1 <= start2 or end2 <= start1):
                overlaps.append((meal1, meal2))
    
    return overlaps


def validate_dinner_before_sleep(
    dinner_end_time: str,
    sleep_time: str,
    min_hours_before_sleep: float = 3.0
) -> Tuple[bool, float]:
    """
    Validate that dinner ends at least N hours before sleep time.
    
    Args:
        dinner_end_time: Dinner end time in HH:MM format
        sleep_time: Sleep time in HH:MM format
        min_hours_before_sleep: Minimum hours before sleep (default 3.0)
        
    Returns:
        Tuple of (is_valid, actual_hours_before_sleep)
    """
    dinner_end = parse_time(dinner_end_time)
    sleep = parse_time(sleep_time)
    
    # Handle case where sleep time is next day
    if sleep < dinner_end:
        sleep = sleep + timedelta(days=1)
    
    hours_before = (sleep - dinner_end).total_seconds() / 3600.0
    is_valid = hours_before >= min_hours_before_sleep
    
    return is_valid, hours_before


def rebalance_calories(
    calorie_split: Dict[str, float],
    target_calories: float
) -> Dict[str, float]:
    """
    Rebalance calorie split to match target exactly.
    
    Args:
        calorie_split: Dictionary of meal names to calorie values
        target_calories: Target total calories
        
    Returns:
        Rebalanced calorie split dictionary
    """
    current_total = sum(calorie_split.values())
    if current_total == 0:
        return calorie_split
    
    factor = target_calories / current_total
    return {meal: calories * factor for meal, calories in calorie_split.items()}

