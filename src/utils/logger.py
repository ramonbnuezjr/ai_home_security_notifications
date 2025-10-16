"""Structured logging system for the security application."""

import logging
import sys
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log string
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data
        
        return json.dumps(log_data)


class SecurityLogger:
    """Enhanced logger for security system with structured logging."""
    
    def __init__(
        self,
        name: str,
        log_level: str = 'INFO',
        log_dir: Optional[str] = None,
        enable_json: bool = False
    ):
        """
        Initialize security logger.
        
        Args:
            name: Logger name
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files
            enable_json: Enable JSON-formatted logging
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Remove existing handlers
        self.logger.handlers = []
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        
        if enable_json:
            console_handler.setFormatter(JSONFormatter())
        else:
            console_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_format)
        
        self.logger.addHandler(console_handler)
        
        # File handler (if log_dir specified)
        if log_dir:
            log_path = Path(log_dir)
            log_path.mkdir(parents=True, exist_ok=True)
            
            # General log file
            file_handler = RotatingFileHandler(
                log_path / f'{name}.log',
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(getattr(logging, log_level.upper()))
            
            if enable_json:
                file_handler.setFormatter(JSONFormatter())
            else:
                file_format = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                file_handler.setFormatter(file_format)
            
            self.logger.addHandler(file_handler)
            
            # Error log file (only ERROR and CRITICAL)
            error_handler = RotatingFileHandler(
                log_path / f'{name}_error.log',
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            error_handler.setLevel(logging.ERROR)
            
            if enable_json:
                error_handler.setFormatter(JSONFormatter())
            else:
                error_handler.setFormatter(file_format)
            
            self.logger.addHandler(error_handler)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with optional extra data."""
        extra = {'extra_data': kwargs} if kwargs else {}
        self.logger.debug(message, extra=extra)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message with optional extra data."""
        extra = {'extra_data': kwargs} if kwargs else {}
        self.logger.info(message, extra=extra)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with optional extra data."""
        extra = {'extra_data': kwargs} if kwargs else {}
        self.logger.warning(message, extra=extra)
    
    def error(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """Log error message with optional extra data and exception info."""
        extra = {'extra_data': kwargs} if kwargs else {}
        self.logger.error(message, exc_info=exc_info, extra=extra)
    
    def critical(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """Log critical message with optional extra data and exception info."""
        extra = {'extra_data': kwargs} if kwargs else {}
        self.logger.critical(message, exc_info=exc_info, extra=extra)
    
    def exception(self, message: str, **kwargs) -> None:
        """Log exception with traceback."""
        extra = {'extra_data': kwargs} if kwargs else {}
        self.logger.exception(message, extra=extra)


# Global logger instances
_loggers = {}


def get_logger(
    name: str,
    log_level: Optional[str] = None,
    log_dir: Optional[str] = None,
    enable_json: bool = False
) -> SecurityLogger:
    """
    Get or create a logger instance.
    
    Args:
        name: Logger name
        log_level: Logging level (uses LOG_LEVEL env var if not specified)
        log_dir: Directory for log files
        enable_json: Enable JSON-formatted logging
        
    Returns:
        SecurityLogger instance
    """
    if name not in _loggers:
        import os
        
        if log_level is None:
            log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        if log_dir is None:
            from .config import get_config
            config = get_config()
            log_dir = config.get('storage.log_path', 'logs')
        
        _loggers[name] = SecurityLogger(name, log_level, log_dir, enable_json)
    
    return _loggers[name]


def setup_logging(log_level: str = 'INFO', log_dir: str = 'logs', enable_json: bool = False) -> None:
    """
    Set up logging for the entire application.
    
    Args:
        log_level: Logging level for all loggers
        log_dir: Directory for log files
        enable_json: Enable JSON-formatted logging
    """
    # Create log directory
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Suppress verbose third-party loggers
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

