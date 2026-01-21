"""
Standardized Knowledge Base Access.

Provides consistent interface for engines to access KB data.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import logging

logger = logging.getLogger(__name__)


class KBLoader:
    """Standardized KB loader for engines."""
    
    KB_BASE_PATH = Path(__file__).parent.parent / "knowledge_base"
    
    @classmethod
    def load_kb_file(cls, kb_path: str) -> Dict[str, Any]:
        """
        Load KB JSON file.
        
        Args:
            kb_path: Relative path from knowledge_base directory
                    (e.g., "medical/medical_conditions_kb_complete.json")
            
        Returns:
            KB data as dictionary or list
            
        Raises:
            FileNotFoundError: If KB file doesn't exist
            ValueError: If JSON is invalid
        """
        full_path = cls.KB_BASE_PATH / kb_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"KB file not found: {full_path}")
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.debug(f"Loaded KB file: {kb_path}")
            return data
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in KB file {kb_path}: {e}")
    
    @classmethod
    def get_kb_item_by_id(cls, kb_path: str, item_id: str, id_field: str = "id") -> Optional[Dict[str, Any]]:
        """
        Get specific item from KB by ID.
        
        Args:
            kb_path: Relative path from knowledge_base directory
            item_id: ID to search for
            id_field: Field name containing the ID (default: "id")
            
        Returns:
            KB item or None if not found
        """
        kb_data = cls.load_kb_file(kb_path)
        
        # Handle both list and dict structures
        if isinstance(kb_data, list):
            for item in kb_data:
                if isinstance(item, dict) and item.get(id_field) == item_id:
                    return item
        elif isinstance(kb_data, dict):
            if kb_data.get(id_field) == item_id:
                return kb_data
        
        logger.warning(f"Item with {id_field}={item_id} not found in {kb_path}")
        return None
    
    @classmethod
    def get_kb_items_by_field(cls, kb_path: str, field_name: str, field_value: Any) -> List[Dict[str, Any]]:
        """
        Get items from KB matching field value.
        
        Args:
            kb_path: Relative path from knowledge_base directory
            field_name: Field name to search
            field_value: Value to match
            
        Returns:
            List of matching items
        """
        kb_data = cls.load_kb_file(kb_path)
        
        results = []
        
        if isinstance(kb_data, list):
            for item in kb_data:
                if isinstance(item, dict) and item.get(field_name) == field_value:
                    results.append(item)
        elif isinstance(kb_data, dict):
            if kb_data.get(field_name) == field_value:
                results.append(kb_data)
        
        return results
    
    @classmethod
    def get_kb_items_by_condition(cls, kb_path: str, condition_func) -> List[Dict[str, Any]]:
        """
        Get items from KB matching a condition function.
        
        Args:
            kb_path: Relative path from knowledge_base directory
            condition_func: Function that takes an item and returns True/False
            
        Returns:
            List of matching items
        """
        kb_data = cls.load_kb_file(kb_path)
        
        results = []
        
        if isinstance(kb_data, list):
            for item in kb_data:
                if isinstance(item, dict) and condition_func(item):
                    results.append(item)
        elif isinstance(kb_data, dict):
            if condition_func(kb_data):
                results.append(kb_data)
        
        return results
    
    @classmethod
    def get_all_kb_items(cls, kb_path: str) -> List[Dict[str, Any]]:
        """
        Get all items from KB file.
        
        Args:
            kb_path: Relative path from knowledge_base directory
            
        Returns:
            List of all items (normalized to list format)
        """
        kb_data = cls.load_kb_file(kb_path)
        
        if isinstance(kb_data, list):
            return kb_data
        elif isinstance(kb_data, dict):
            return [kb_data]
        else:
            return []






