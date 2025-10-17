"""Service modules for the security system."""

from .camera_service import CameraService
from .motion_detection_service import MotionDetectionService, MotionEvent
from .object_detection_service import ObjectDetectionService, DetectedObject, DetectionResult
from .notification_manager import NotificationManager
from .base_notification_service import (
    NotificationContext,
    NotificationPriority,
    NotificationStatus,
    NotificationResult,
    BaseNotificationService
)
from .email_notification_service import EmailNotificationService
from .sms_notification_service import SMSNotificationService
from .push_notification_service import PushNotificationService
from .voice_notification_service import VoiceNotificationService

__all__ = [
    # Core services
    'CameraService',
    'MotionDetectionService',
    'ObjectDetectionService',
    'NotificationManager',
    
    # Notification services
    'EmailNotificationService',
    'SMSNotificationService',
    'PushNotificationService',
    'VoiceNotificationService',
    
    # Data classes
    'MotionEvent',
    'DetectedObject',
    'DetectionResult',
    'NotificationContext',
    'NotificationResult',
    
    # Enums
    'NotificationPriority',
    'NotificationStatus',
    
    # Base classes
    'BaseNotificationService',
]

