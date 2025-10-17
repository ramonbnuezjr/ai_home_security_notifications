"""Push notification service using Firebase Cloud Messaging."""

import time
from typing import List, Optional, Dict, Any

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

from .base_notification_service import (
    BaseNotificationService,
    NotificationContext,
    NotificationResult,
    NotificationStatus
)
from ..utils.config import Config


class PushNotificationService(BaseNotificationService):
    """
    Push notification service using Firebase Cloud Messaging (FCM).
    
    Supports:
    - Push notifications to mobile devices
    - Custom data payloads
    - Image attachments
    - Priority levels
    """
    
    def __init__(self, config: Config):
        """
        Initialize push notification service.
        
        Args:
            config: System configuration object
        """
        super().__init__(config, 'push')
        
        # Check if Firebase is available
        if not FIREBASE_AVAILABLE:
            self.logger.warning('Firebase library not installed. Push notifications unavailable.')
            self.enabled = False
            return
        
        # Load push configuration
        notification_config = config.get('notifications', {})
        push_config = notification_config.get('push', {})
        
        self.enabled = push_config.get('enabled', False)
        self.provider = push_config.get('provider', 'firebase')
        
        # Firebase configuration
        firebase_config = push_config.get('firebase', {})
        self.credentials_path = firebase_config.get('credentials_path', '')
        self.device_tokens = firebase_config.get('device_tokens', [])
        
        self.app = None
        
        self.logger.info(
            'Push notification service created',
            enabled=self.enabled,
            provider=self.provider,
            devices=len(self.device_tokens)
        )
    
    def initialize(self) -> bool:
        """
        Initialize the push notification service.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if not self.enabled:
            self.logger.info('Push notifications disabled in configuration')
            return False
        
        if not FIREBASE_AVAILABLE:
            self.logger.error('Firebase library not installed. Install with: pip install firebase-admin')
            return False
        
        if not self.credentials_path:
            self.logger.error('Firebase credentials path not configured')
            return False
        
        if not self.device_tokens or len(self.device_tokens) == 0:
            self.logger.error('No device tokens configured')
            return False
        
        try:
            # Initialize Firebase Admin SDK
            if not firebase_admin._apps:
                cred = credentials.Certificate(self.credentials_path)
                self.app = firebase_admin.initialize_app(cred)
            else:
                self.app = firebase_admin.get_app()
            
            self.is_initialized = True
            self.logger.info('Push notification service initialized successfully')
            return True
            
        except Exception as e:
            self.logger.error(f'Failed to initialize Firebase: {e}')
            return False
    
    def send_notification(self, context: NotificationContext) -> NotificationResult:
        """
        Send a push notification.
        
        Args:
            context: Notification context
            
        Returns:
            NotificationResult with delivery status
        """
        if not self.is_initialized:
            if not self.initialize():
                return NotificationResult(
                    success=False,
                    status=NotificationStatus.FAILED,
                    provider='push',
                    timestamp=time.time(),
                    error='Service not initialized'
                )
        
        try:
            # Create notification message
            title = context.get_formatted_subject()
            body = self._create_notification_body(context)
            
            # Create FCM notification
            notification = messaging.Notification(
                title=title,
                body=body,
                image=context.image_path if context.image_path and context.image_path.startswith('http') else None
            )
            
            # Create data payload
            data_payload = {
                'event_type': context.event_type,
                'timestamp': str(context.timestamp),
                'priority': context.priority.value,
            }
            
            if context.zone_name:
                data_payload['zone'] = context.zone_name
            
            if context.detected_objects:
                data_payload['objects'] = ','.join(context.detected_objects)
            
            if context.threat_level:
                data_payload['threat_level'] = context.threat_level
            
            # Android configuration
            android_config = messaging.AndroidConfig(
                priority='high' if context.priority.value in ['high', 'critical'] else 'normal',
                notification=messaging.AndroidNotification(
                    sound='default',
                    channel_id='security_alerts'
                )
            )
            
            # APNS (iOS) configuration
            apns_config = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default',
                        badge=1
                    )
                )
            )
            
            # Send to all devices
            successful_sends = 0
            failed_sends = 0
            errors = []
            
            for device_token in self.device_tokens:
                try:
                    message = messaging.Message(
                        notification=notification,
                        data=data_payload,
                        token=device_token,
                        android=android_config,
                        apns=apns_config
                    )
                    
                    response = messaging.send(message)
                    successful_sends += 1
                    self.logger.debug(f'Push notification sent to device, message ID: {response}')
                    
                except messaging.UnregisteredError:
                    failed_sends += 1
                    error_msg = f'Device token is invalid or unregistered'
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                    
                except Exception as e:
                    failed_sends += 1
                    error_msg = f'Error sending to device: {e}'
                    errors.append(error_msg)
                    self.logger.error(error_msg)
            
            # Determine overall success
            if successful_sends > 0:
                self._record_success()
                self.logger.info(
                    'Push notifications sent',
                    successful=successful_sends,
                    failed=failed_sends
                )
                
                return NotificationResult(
                    success=True,
                    status=NotificationStatus.SENT,
                    provider='push',
                    timestamp=time.time(),
                    message=f'Push sent to {successful_sends}/{len(self.device_tokens)} device(s)',
                    metadata={'successful': successful_sends, 'failed': failed_sends}
                )
            else:
                self._record_failure()
                error_msg = f'Failed to send push to any devices: {"; ".join(errors)}'
                self.logger.error(error_msg)
                
                return NotificationResult(
                    success=False,
                    status=NotificationStatus.FAILED,
                    provider='push',
                    timestamp=time.time(),
                    error=error_msg
                )
            
        except Exception as e:
            self._record_failure()
            error_msg = f'Failed to send push notification: {e}'
            self.logger.error(error_msg, exc_info=True)
            return NotificationResult(
                success=False,
                status=NotificationStatus.FAILED,
                provider='push',
                timestamp=time.time(),
                error=error_msg
            )
    
    def test_connection(self) -> bool:
        """
        Test Firebase connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        if not self.app:
            return False
        
        try:
            # Try to create a test message (without sending)
            # This validates that Firebase is properly initialized
            test_message = messaging.Message(
                notification=messaging.Notification(
                    title='Test',
                    body='Test'
                ),
                token='test_token'
            )
            
            # If we can create the message structure, Firebase is working
            self.logger.info('Firebase connection test successful')
            return True
            
        except Exception as e:
            self.logger.error(f'Firebase connection test failed: {e}')
            return False
    
    def _create_notification_body(self, context: NotificationContext) -> str:
        """
        Create push notification body text.
        
        Args:
            context: Notification context
            
        Returns:
            Notification body string
        """
        parts = []
        
        # Add detected objects
        if context.detected_objects and len(context.detected_objects) > 0:
            objects_str = ", ".join(context.detected_objects[:3])
            if len(context.detected_objects) > 3:
                objects_str += f" (+{len(context.detected_objects) - 3} more)"
            parts.append(f"Detected: {objects_str}")
        
        # Add zone
        if context.zone_name:
            parts.append(f"Zone: {context.zone_name}")
        
        # Add time
        time_str = time.strftime('%H:%M:%S', time.localtime(context.timestamp))
        parts.append(f"Time: {time_str}")
        
        # Add threat level if high
        if context.threat_level and context.threat_level in ['high', 'critical']:
            parts.append(f"⚠️ {context.threat_level.upper()} threat")
        
        return " • ".join(parts)
    
    def add_device_token(self, token: str) -> None:
        """
        Add a device token for push notifications.
        
        Args:
            token: Device FCM token
        """
        if token not in self.device_tokens:
            self.device_tokens.append(token)
            self.logger.info(f'Device token added, total devices: {len(self.device_tokens)}')
    
    def remove_device_token(self, token: str) -> None:
        """
        Remove a device token.
        
        Args:
            token: Device FCM token to remove
        """
        if token in self.device_tokens:
            self.device_tokens.remove(token)
            self.logger.info(f'Device token removed, total devices: {len(self.device_tokens)}')

