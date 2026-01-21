"""
Base Engine Class.

Provides common functionality for all engines including contract validation
and standardized KB access.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Type, Optional
import logging

from app.platform.core.contracts.validator import EngineContractValidator, ContractValidationError
from app.platform.core.kb_access import KBLoader

logger = logging.getLogger(__name__)


class BaseEngine(ABC):
    """Base class for all engines."""
    
    def __init__(self):
        """Initialize engine with KB loader."""
        self.kb_loader = KBLoader()
        self.engine_name = self.__class__.__name__
    
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input and produce output.
        
        Must be implemented by each engine.
        
        Args:
            input_data: Input data dictionary
            
        Returns:
            Output data dictionary
        """
        pass
    
    def validate_input(self, input_data: Dict[str, Any], contract_class: Type) -> bool:
        """
        Validate input against contract.
        
        Args:
            input_data: Input data dictionary
            contract_class: Contract dataclass class
            
        Returns:
            True if valid
            
        Raises:
            ContractValidationError: If validation fails
        """
        return EngineContractValidator.validate_input(contract_class, input_data, self.engine_name)
    
    def validate_output(self, output_data: Dict[str, Any], contract_class: Type) -> bool:
        """
        Validate output against contract.
        
        Args:
            output_data: Output data dictionary
            contract_class: Contract dataclass class
            
        Returns:
            True if valid
            
        Raises:
            ContractValidationError: If validation fails
        """
        return EngineContractValidator.validate_output(contract_class, output_data, self.engine_name)
    
    def load_kb(self, kb_path: str) -> Dict[str, Any]:
        """
        Load KB file using standardized loader.
        
        Args:
            kb_path: Relative path from knowledge_base directory
            
        Returns:
            KB data
        """
        return self.kb_loader.load_kb_file(kb_path)
    
    def get_kb_item(self, kb_path: str, item_id: str, id_field: str = "id") -> Optional[Dict[str, Any]]:
        """
        Get KB item by ID.
        
        Args:
            kb_path: Relative path from knowledge_base directory
            item_id: ID to search for
            id_field: Field name containing the ID
            
        Returns:
            KB item or None
        """
        return self.kb_loader.get_kb_item_by_id(kb_path, item_id, id_field)
    
    def get_kb_items_by_field(self, kb_path: str, field_name: str, field_value: Any) -> list:
        """
        Get KB items matching field value.
        
        Args:
            kb_path: Relative path from knowledge_base directory
            field_name: Field name to search
            field_value: Value to match
            
        Returns:
            List of matching items
        """
        return self.kb_loader.get_kb_items_by_field(kb_path, field_name, field_value)






