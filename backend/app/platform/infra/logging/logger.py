"""
Platform Logging Setup.
Decision-level logging and audit trail support.
"""
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
import logging


class DecisionLogger(ABC):
    """
    Decision Logger Interface.
    
    Responsibility:
    - Log decision-level events
    - Track rule IDs used in decisions
    - Support explainability queries
    - Maintain audit trails
    
    Rules:
    - Log rule IDs used
    - Log constraint sources
    - Support "Why this recommendation?" queries
    """
    
    @abstractmethod
    def log_decision(
        self,
        entity_type: str,
        entity_id: str,
        rule_ids_used: List[str],
        notes: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Log a decision with rule IDs.
        
        Args:
            entity_type: Entity type (diagnosis | mnt | plan)
            entity_id: Entity identifier
            rule_ids_used: List of rule IDs used in decision
            notes: Optional notes
            context: Optional context data
        """
        pass
    
    @abstractmethod
    def log_rule_application(
        self,
        rule_id: str,
        context: Dict[str, Any],
        result: Any
    ):
        """
        Log rule application.
        
        Args:
            rule_id: Rule ID from knowledge base
            context: Context in which rule was applied
            result: Rule application result
        """
        pass
    
    @abstractmethod
    def log_constraint_source(
        self,
        constraint_type: str,
        constraint_value: Any,
        source: str,
        rule_ids: List[str]
    ):
        """
        Log constraint source for explainability.
        
        Args:
            constraint_type: Type of constraint (macro | micro | exclusion)
            constraint_value: Constraint value
            source: Source of constraint
            rule_ids: Rule IDs that generated constraint
        """
        pass


class PlatformLogger:
    """
    Platform Logger.
    
    Provides logging functionality for the platform.
    Supports decision-level logging and audit trails.
    """
    
    def __init__(
        self,
        name: str = "platform",
        log_level: str = "INFO",
        decision_logger: Optional[DecisionLogger] = None
    ):
        """
        Initialize platform logger.
        
        Args:
            name: Logger name
            log_level: Logging level
            decision_logger: Optional decision logger implementation
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        self.decision_logger = decision_logger
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, **kwargs)
    
    def log_decision(
        self,
        entity_type: str,
        entity_id: str,
        rule_ids_used: List[str],
        notes: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Log decision with rule IDs.
        
        Args:
            entity_type: Entity type
            entity_id: Entity identifier
            rule_ids_used: List of rule IDs
            notes: Optional notes
            context: Optional context
        """
        if self.decision_logger:
            self.decision_logger.log_decision(
                entity_type, entity_id, rule_ids_used, notes, context
            )
        self.logger.info(
            f"Decision logged: {entity_type} {entity_id} - Rules: {rule_ids_used}",
            extra={"rule_ids": rule_ids_used, "context": context}
        )
    
    def log_rule_application(
        self,
        rule_id: str,
        context: Dict[str, Any],
        result: Any
    ):
        """
        Log rule application.
        
        Args:
            rule_id: Rule ID
            context: Context
            result: Result
        """
        if self.decision_logger:
            self.decision_logger.log_rule_application(rule_id, context, result)
        self.logger.debug(
            f"Rule applied: {rule_id} - Result: {result}",
            extra={"rule_id": rule_id, "context": context}
        )
    
    def log_constraint_source(
        self,
        constraint_type: str,
        constraint_value: Any,
        source: str,
        rule_ids: List[str]
    ):
        """
        Log constraint source.
        
        Args:
            constraint_type: Constraint type
            constraint_value: Constraint value
            source: Source
            rule_ids: Rule IDs
        """
        if self.decision_logger:
            self.decision_logger.log_constraint_source(
                constraint_type, constraint_value, source, rule_ids
            )
        self.logger.info(
            f"Constraint source: {constraint_type} = {constraint_value} from {source} - Rules: {rule_ids}",
            extra={"constraint_type": constraint_type, "rule_ids": rule_ids}
        )

