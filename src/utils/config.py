"""Configuration loader for system_config.yaml and environment variables."""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv


class Config:
    """Configuration manager for the security system."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration from YAML file and environment variables.
        
        Args:
            config_path: Path to system_config.yaml file
        """
        # Load environment variables from .env file
        load_dotenv()
        
        # Determine config file path
        if config_path is None:
            config_path = os.getenv('CONFIG_FILE', 'config/system_config.yaml')
        
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        
        # Load configuration
        self._load_config()
        
        # Override with environment variables
        self._load_env_overrides()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}"
            )
        
        with open(self.config_path, 'r') as f:
            self._config = yaml.safe_load(f)
    
    def _load_env_overrides(self) -> None:
        """Override configuration with environment variables."""
        # Camera settings
        if os.getenv('PI_CAMERA_INDEX'):
            self._config.setdefault('camera', {})['index'] = int(os.getenv('PI_CAMERA_INDEX'))
        
        # AI model settings
        if os.getenv('YOLO_MODEL_PATH'):
            self._config.setdefault('ai', {}).setdefault('yolo', {})['model_path'] = \
                os.getenv('YOLO_MODEL_PATH')
        
        if os.getenv('WHISPER_MODEL_SIZE'):
            self._config.setdefault('notifications', {}).setdefault('voice', {})['whisper_model'] = \
                os.getenv('WHISPER_MODEL_SIZE')
        
        # LLM settings
        if os.getenv('LLM_ENABLED'):
            enabled = os.getenv('LLM_ENABLED').lower() in ('true', '1', 'yes')
            self._config.setdefault('ai', {}).setdefault('llm', {})['enabled'] = enabled
        
        # Storage paths
        if os.getenv('STORAGE_PATH'):
            self._config.setdefault('storage', {})['base_path'] = os.getenv('STORAGE_PATH')
        
        # Email notification settings
        if os.getenv('SMTP_SERVER'):
            email_config = self._config.setdefault('notifications', {}).setdefault('email', {})
            email_config['smtp_server'] = os.getenv('SMTP_SERVER')
            if os.getenv('SMTP_PORT'):
                email_config['smtp_port'] = int(os.getenv('SMTP_PORT'))
            if os.getenv('SMTP_USERNAME'):
                email_config['smtp_username'] = os.getenv('SMTP_USERNAME')
            if os.getenv('SMTP_PASSWORD'):
                email_config['smtp_password'] = os.getenv('SMTP_PASSWORD')
        
        # Twilio SMS settings
        if os.getenv('TWILIO_ACCOUNT_SID'):
            sms_config = self._config.setdefault('notifications', {}).setdefault('sms', {})
            twilio_config = sms_config.setdefault('twilio', {})
            twilio_config['account_sid'] = os.getenv('TWILIO_ACCOUNT_SID')
            if os.getenv('TWILIO_AUTH_TOKEN'):
                twilio_config['auth_token'] = os.getenv('TWILIO_AUTH_TOKEN')
            if os.getenv('TWILIO_FROM_NUMBER'):
                twilio_config['from_number'] = os.getenv('TWILIO_FROM_NUMBER')
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key.
        
        Args:
            key: Configuration key in dot notation (e.g., 'camera.resolution.width')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
            
        Example:
            >>> config.get('camera.resolution.width', 1920)
            1920
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value by dot-notation key.
        
        Args:
            key: Configuration key in dot notation
            value: Value to set
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            config = config.setdefault(k, {})
        
        config[keys[-1]] = value
    
    def get_camera_config(self) -> Dict[str, Any]:
        """Get camera configuration."""
        return self.get('camera', {})
    
    def get_detection_config(self) -> Dict[str, Any]:
        """Get motion detection configuration."""
        return self.get('detection', {})
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI classification configuration."""
        return self.get('ai', {})
    
    def get_notification_config(self) -> Dict[str, Any]:
        """Get notification configuration."""
        return self.get('notifications', {})
    
    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration."""
        return self.get('storage', {})
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration."""
        return self.get('performance', {})
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration."""
        return self.get('security', {})
    
    def save(self, path: Optional[str] = None) -> None:
        """
        Save current configuration to YAML file.
        
        Args:
            path: Path to save configuration (defaults to original path)
        """
        save_path = Path(path) if path else self.config_path
        
        with open(save_path, 'w') as f:
            yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)
    
    def reload(self) -> None:
        """Reload configuration from file and environment."""
        self._load_config()
        self._load_env_overrides()
    
    @property
    def debug(self) -> bool:
        """Check if debug mode is enabled."""
        return os.getenv('DEBUG', 'false').lower() in ('true', '1', 'yes')
    
    @property
    def log_level(self) -> str:
        """Get log level."""
        return os.getenv('LOG_LEVEL', 'INFO').upper()


# Global configuration instance
_config: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get global configuration instance.
    
    Args:
        config_path: Path to configuration file (only used on first call)
        
    Returns:
        Global Config instance
    """
    global _config
    
    if _config is None:
        _config = Config(config_path)
    
    return _config


def reload_config() -> None:
    """Reload global configuration from file."""
    global _config
    
    if _config is not None:
        _config.reload()


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration and return as dictionary.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    config_instance = get_config(config_path)
    return config_instance._config

