"""Base notification service interface."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ..utils.logger import get_logger


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationStatus(Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    THROTTLED = "throttled"


@dataclass
class NotificationContext:
    """Context information for a notification."""
    event_type: str  # motion, object_detected, system_alert, etc.
    timestamp: float
    priority: NotificationPriority
    subject: Optional[str] = None
    message: Optional[str] = None
    image_path: Optional[str] = None
    video_path: Optional[str] = None
    detected_objects: Optional[List[str]] = None
    motion_percentage: Optional[float] = None
    threat_level: Optional[str] = None
    zone_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def get_formatted_message(self) -> str:
        """Generate a formatted message from context."""
        if self.message:
            return self.message
        
        # Auto-generate message from context
        parts = []
        
        # Event type
        parts.append(f"Security Alert: {self.event_type.replace('_', ' ').title()}")
        
        # Timestamp
        dt = datetime.fromtimestamp(self.timestamp)
        parts.append(f"Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Zone
        if self.zone_name:
            parts.append(f"Zone: {self.zone_name}")
        
        # Objects detected
        if self.detected_objects and len(self.detected_objects) > 0:
            objects_str = ", ".join(self.detected_objects[:3])
            if len(self.detected_objects) > 3:
                objects_str += f" (+{len(self.detected_objects) - 3} more)"
            parts.append(f"Detected: {objects_str}")
        
        # Motion percentage
        if self.motion_percentage is not None:
            parts.append(f"Motion: {self.motion_percentage:.1f}%")
        
        # Threat level
        if self.threat_level:
            parts.append(f"Threat Level: {self.threat_level.upper()}")
        
        return "\n".join(parts)
    
    def get_formatted_subject(self) -> str:
        """Generate a formatted subject line from context."""
        if self.subject:
            return self.subject
        
        # Auto-generate subject from context
        parts = ["🚨" if self.priority in [NotificationPriority.HIGH, NotificationPriority.CRITICAL] else "⚠️"]
        parts.append("Security Alert")
        
        if self.detected_objects and len(self.detected_objects) > 0:
            parts.append(f"- {self.detected_objects[0]}")
        
        if self.zone_name:
            parts.append(f"in {self.zone_name}")
        
        return " ".join(parts)


@dataclass
class NotificationResult:
    """Result of a notification attempt."""
    success: bool
    status: NotificationStatus
    provider: str
    timestamp: float
    message: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseNotificationService(ABC):
    """
    Abstract base class for notification services.
    
    All notification providers (email, SMS, push, voice) should inherit from this.
    """
    
    def __init__(self, config: Any, service_name: str):
        """
        Initialize notification service.
        
        Args:
            config: System configuration object
            service_name: Name of the notification service
        """
        self.config = config
        self.service_name = service_name
        self.logger = get_logger(f'notification.{service_name}')
        self.enabled = False
        self.is_initialized = False
        
        # Statistics
        self.sent_count = 0
        self.failed_count = 0
        self.throttled_count = 0
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the notification service.
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def send_notification(self, context: NotificationContext) -> NotificationResult:
        """
        Send a notification.
        
        Args:
            context: Notification context with all relevant information
            
        Returns:
            NotificationResult with delivery status
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test the notification service connection.
        
        Returns:
            True if connection is working, False otherwise
        """
        pass
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get notification service statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'service': self.service_name,
            'enabled': self.enabled,
            'initialized': self.is_initialized,
            'sent_count': self.sent_count,
            'failed_count': self.failed_count,
            'throttled_count': self.throttled_count,
            'success_rate': self.sent_count / max(1, self.sent_count + self.failed_count)
        }
    
    def shutdown(self) -> None:
        """Shutdown the notification service."""
        self.logger.info(f'{self.service_name} notification service shutting down')
        self.is_initialized = False
    
    def _record_success(self) -> None:
        """Record a successful notification."""
        self.sent_count += 1
    
    def _record_failure(self) -> None:
        """Record a failed notification."""
        self.failed_count += 1
    
    def _record_throttled(self) -> None:
        """Record a throttled notification."""
        self.throttled_count += 1

