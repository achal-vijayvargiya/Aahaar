"""
Platform Configuration Loader.
Configuration management for the platform.
"""
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod


class ConfigLoader(ABC):
    """
    Configuration Loader Interface.
    
    Responsibility:
    - Load configuration settings for the platform
    - Provide access to configuration values
    - Support feature flags and config-driven thresholds
    
    Rules:
    - No environment-specific logic
    - No secrets (secrets handled separately)
    - Configuration values only
    """
    
    @abstractmethod
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        pass
    
    @abstractmethod
    def get_all_config(self) -> Dict[str, Any]:
        """
        Get all configuration values.
        
        Returns:
            Dictionary of all configuration values
        """
        pass


class PlatformConfig:
    """
    Platform Configuration.
    
    Manages configuration for the platform module.
    Provides access to feature flags and thresholds.
    """
    
    def __init__(self, config_loader: Optional[ConfigLoader] = None):
        """
        Initialize platform configuration.
        
        Args:
            config_loader: Optional configuration loader implementation
        """
        self.config_loader = config_loader
        self._config_cache: Dict[str, Any] = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        if self.config_loader:
            return self.config_loader.get_config(key, default)
        return self._config_cache.get(key, default)
    
    def set(self, key: str, value: Any):
        """
        Set configuration value (for testing/overrides).
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self._config_cache[key] = value
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """
        Check if a feature flag is enabled.
        
        Args:
            feature_name: Feature flag name
            
        Returns:
            True if feature is enabled, False otherwise
        """
        return self.get(f"feature.{feature_name}", False)
    
    def get_threshold(self, threshold_name: str, default: float = 0.0) -> float:
        """
        Get config-driven threshold value.
        
        Args:
            threshold_name: Threshold name
            default: Default threshold value
            
        Returns:
            Threshold value
        """
        return self.get(f"threshold.{threshold_name}", default)

