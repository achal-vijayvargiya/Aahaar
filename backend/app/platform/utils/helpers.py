"""
Platform Helper Functions.
General utility functions for the platform.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


def generate_entity_id() -> str:
    """
    Generate a unique entity identifier.
    
    Returns:
        Unique identifier string
        
    Note:
        Placeholder implementation. Actual implementation may use UUID or other scheme.
    """
    return str(uuid.uuid4())


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """
    Format datetime as ISO 8601 string.
    
    Args:
        dt: Optional datetime (defaults to now)
        
    Returns:
        ISO 8601 formatted timestamp string
    """
    if dt is None:
        dt = datetime.utcnow()
    return dt.isoformat()


def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge multiple dictionaries.
    
    Args:
        *dicts: Dictionaries to merge
        
    Returns:
        Merged dictionary
        
    Note:
        Later dictionaries override earlier ones for duplicate keys.
    """
    result = {}
    for d in dicts:
        if d:
            result.update(d)
    return result


def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    Safely get value from dictionary.
    
    Args:
        data: Dictionary to get value from
        key: Key to retrieve
        default: Default value if key not found
        
    Returns:
        Value or default
    """
    return data.get(key, default)


def filter_none_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter out None values from dictionary.
    
    Args:
        data: Dictionary to filter
        
    Returns:
        Dictionary with None values removed
    """
    return {k: v for k, v in data.items() if v is not None}


def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split list into chunks of specified size.
    
    Args:
        items: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

