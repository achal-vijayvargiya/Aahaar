"""
Contract Validator.

Validates engine inputs/outputs against defined contracts.
"""
from typing import Dict, Any, Type, Optional, get_origin, get_args
from dataclasses import dataclass, fields, MISSING
import logging

logger = logging.getLogger(__name__)


class ContractValidationError(Exception):
    """Raised when contract validation fails."""
    pass


class EngineContractValidator:
    """Validates engine contracts."""
    
    @staticmethod
    def validate_input(contract_class: Type, data: Dict[str, Any], engine_name: str) -> bool:
        """
        Validate input data against contract.
        
        Args:
            contract_class: Contract dataclass class
            data: Input data dictionary
            engine_name: Name of engine for error messages
            
        Returns:
            True if valid
            
        Raises:
            ContractValidationError: If validation fails
        """
        missing_fields = []
        invalid_fields = []
        
        # Get required fields from contract
        contract_fields = {f.name: f for f in fields(contract_class)}
        
        for field_name, field_info in contract_fields.items():
            # Check if field is present
            if field_name not in data:
                if field_info.default == MISSING:
                    missing_fields.append(field_name)
            else:
                # Validate type if possible
                expected_type = field_info.type
                actual_value = data[field_name]
                
                # Basic type checking
                if not EngineContractValidator._check_type(actual_value, expected_type):
                    invalid_fields.append({
                        "field": field_name,
                        "expected": str(expected_type),
                        "actual": type(actual_value).__name__
                    })
        
        if missing_fields or invalid_fields:
            error_msg = f"Contract validation failed for {engine_name}:\n"
            if missing_fields:
                error_msg += f"  Missing required fields: {', '.join(missing_fields)}\n"
            if invalid_fields:
                error_msg += "  Invalid field types:\n"
                for inv in invalid_fields:
                    error_msg += f"    - {inv['field']}: expected {inv['expected']}, got {inv['actual']}\n"
            
            logger.error(error_msg)
            raise ContractValidationError(error_msg)
        
        return True
    
    @staticmethod
    def validate_output(contract_class: Type, data: Dict[str, Any], engine_name: str) -> bool:
        """
        Validate output data against contract.
        
        Args:
            contract_class: Contract dataclass class
            data: Output data dictionary
            engine_name: Name of engine for error messages
            
        Returns:
            True if valid
            
        Raises:
            ContractValidationError: If validation fails
        """
        return EngineContractValidator.validate_input(contract_class, data, engine_name)
    
    @staticmethod
    def _check_type(value: Any, expected_type: Type) -> bool:
        """
        Basic type checking.
        
        Args:
            value: Value to check
            expected_type: Expected type
            
        Returns:
            True if type matches
        """
        # Handle None values
        if value is None:
            # Check if type is Optional
            origin = get_origin(expected_type)
            if origin is not None:
                args = get_args(expected_type)
                if type(None) in args:
                    return True
            return False
        
        # Handle Optional types
        origin = get_origin(expected_type)
        if origin is not None:
            args = get_args(expected_type)
            # Check if it's Optional (Union with None)
            if type(None) in args:
                # Get the actual type from Union
                non_none_types = [t for t in args if t is not type(None)]
                if non_none_types:
                    return any(EngineContractValidator._check_type(value, t) for t in non_none_types)
            
            # Handle List types
            if origin is list:
                if not isinstance(value, list):
                    return False
                if value and args:
                    item_type = args[0]
                    return all(EngineContractValidator._check_type(item, item_type) for item in value)
                return True
            
            # Handle Dict types
            if origin is dict:
                if not isinstance(value, dict):
                    return False
                # For Dict[str, Any] or Dict[str, int], we just check it's a dict
                return True
        
        # Handle direct type check
        if expected_type == Any:
            return True
        
        # Check for UUID type
        if expected_type.__name__ == 'UUID':
            from uuid import UUID
            return isinstance(value, UUID)
        
        # Direct isinstance check
        try:
            return isinstance(value, expected_type)
        except TypeError:
            # If isinstance fails, try to match by name
            return type(value).__name__ == expected_type.__name__






