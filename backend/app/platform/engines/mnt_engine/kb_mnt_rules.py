"""
Knowledge Base MNT Rules for MNT Engine.

Loads MNT rules from JSON knowledge base file.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional


# Cache for loaded MNT rules
_MNT_RULES_CACHE: Optional[Dict[str, Dict[str, Any]]] = None


def _load_mnt_rules() -> Dict[str, Dict[str, Any]]:
    """
    Load MNT rules from JSON knowledge base file.
    
    Returns:
        Dictionary of MNT rules keyed by rule_id
    """
    global _MNT_RULES_CACHE
    
    # Return cached rules if already loaded
    if _MNT_RULES_CACHE is not None:
        return _MNT_RULES_CACHE
    
    # Path to KB JSON file
    kb_path = Path(__file__).parent.parent.parent / "knowledge_base" / "mnt_rules" / "mnt_rules_kb_complete.json"
    
    try:
        with open(kb_path, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
        
        # Convert list to dictionary keyed by rule_id
        # Filter only active rules
        rules_dict = {}
        for rule in kb_data:
            if rule.get("status") == "active":
                rule_id = rule.get("rule_id")
                if rule_id:
                    rules_dict[rule_id] = rule
        
        # Cache the rules
        _MNT_RULES_CACHE = rules_dict
        
        return rules_dict
    except FileNotFoundError:
        raise FileNotFoundError(
            f"MNT rules KB file not found at: {kb_path}\n"
            "Please ensure the knowledge base file exists."
        )
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in MNT rules KB: {e}")


def get_mnt_rules() -> Dict[str, Dict[str, Any]]:
    """
    Get all MNT rules from knowledge base.
    
    Returns:
        Dictionary of all active MNT rules keyed by rule_id
    """
    return _load_mnt_rules()


def get_mnt_rule(rule_id: str) -> Optional[Dict[str, Any]]:
    """
    Get MNT rule by ID.
    
    Args:
        rule_id: MNT rule identifier
        
    Returns:
        Rule dictionary or None if not found
    """
    rules = _load_mnt_rules()
    return rules.get(rule_id)


def get_rules_for_diagnosis(diagnosis_id: str) -> List[str]:
    """
    Get MNT rule IDs that apply to a specific diagnosis.
    
    Args:
        diagnosis_id: Diagnosis identifier (medical condition or nutrition diagnosis)
        
    Returns:
        List of MNT rule IDs that apply to this diagnosis
    """
    applicable_rules = []
    rules = _load_mnt_rules()
    for rule_id, rule in rules.items():
        applies_to = rule.get("applies_to_diagnoses", [])
        if diagnosis_id in applies_to:
            applicable_rules.append(rule_id)
    return applicable_rules


def get_priority_level(priority: str) -> int:
    """
    Convert priority string to numeric level for comparison.
    
    Args:
        priority: Priority string (critical, high, medium, low)
        
    Returns:
        Numeric priority level (4=critical, 3=high, 2=medium, 1=low)
    """
    priority_map = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1
    }
    return priority_map.get(priority, 2)  # Default to medium


# Backward compatibility: Export MNT_RULES as a function that returns the rules
def MNT_RULES() -> Dict[str, Dict[str, Any]]:
    """
    Get all MNT rules (for backward compatibility).
    
    Returns:
        Dictionary of all active MNT rules keyed by rule_id
    """
    return _load_mnt_rules()

